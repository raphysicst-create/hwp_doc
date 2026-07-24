#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stop 훅용 산출물 검증기 — stop_validator.py가 턴 종료 전에 실행한다.

계약(.claude/hooks/stop_validator.py): exit 0 = 통과 / exit 1 = 실패(사유 stdout).
subprocess timeout 90초 안에 끝나야 하므로 빠른 검사만 수행한다:
  1. validate.py        — HWPX 구조(스키마) 검증
  2. gonmun_lint.py     — 공문 작성법 검수 (error 심각도만 실패, DATE_WEEKDAY 포함 사본)
COM 실열림·render_check 등 느린 검사는 여기서 하지 않는다 (대화 중 파이프라인 담당).

동작 원칙:
- 최초 실행: 기존 output/*.hwpx는 이미 사람 검토를 거쳤으므로 검사 없이 기준선만 기록.
- 이후 실행: 기준선 이후 새로 생기거나 변경된 파일만 검사한다.
- 이번 실행에서 검사한 파일의 실패만 exit 1로 보고한다. 이미 보고된 실패 파일이
  변경 없이 남아 있으면 다시 막지 않는다 (매 턴 재차단 방지 — 2회 초과 시
  stop_validator가 사용자 보고로 전환하는 설계와 맞물림).
- 시간 예산(70초) 초과 시 남은 파일은 기록하지 않고 다음 Stop에서 재검사.
- 검증기 자체 오류(스캔 실패 등)는 턴을 막지 않는다 — 경고 출력 후 exit 0.

테스트용 env: HWPDOC_OUTPUT_DIR(기본 output/), HWPDOC_STATE_FILE(기본 logs/.validate_state.json)
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = Path(os.environ.get("HWPDOC_OUTPUT_DIR", ROOT / "output"))
STATE_FILE = Path(os.environ.get("HWPDOC_STATE_FILE", ROOT / "logs" / ".validate_state.json"))
SCRIPTS = ROOT / ".claude" / "skills" / "hwpx" / "scripts"
TIME_BUDGET = 70.0
PER_CHECK_TIMEOUT = 25

CHECKS = [
    ("validate", [str(SCRIPTS / "validate.py"), "{file}"]),
    ("gonmun_lint", [str(SCRIPTS / "gonmun_lint.py"), "--hwpx", "{file}", "--format", "text"]),
]


def file_sig(p: Path) -> dict:
    st = p.stat()
    return {"mtime": st.st_mtime, "size": st.st_size}


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")


def run_checks(p: Path) -> tuple[bool, str]:
    """파일 하나에 전 검사 실행. (통과 여부, 실패 사유) 반환. 타임아웃은 예외로 전파."""
    for name, argv_tpl in CHECKS:
        argv = [sys.executable] + [a.replace("{file}", str(p)) for a in argv_tpl]
        r = subprocess.run(
            argv, capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=PER_CHECK_TIMEOUT, cwd=ROOT,
        )
        if r.returncode != 0:
            out = (r.stdout or "").strip() or (r.stderr or "").strip()
            return False, f"[{name}] {out[:600]}"
    return True, ""


def main() -> int:
    if not OUTPUT_DIR.is_dir():
        return 0
    try:
        files = sorted(
            f for f in OUTPUT_DIR.rglob("*.hwpx")
            if not f.name.startswith("~$") and f.stat().st_size > 0
        )
    except OSError as e:
        print(f"[경고] output 스캔 실패, 검증 건너뜀: {e}")
        return 0

    state = load_state()
    first_run = not STATE_FILE.exists()

    if first_run:
        for f in files:
            state[str(f.relative_to(OUTPUT_DIR))] = {**file_sig(f), "ok": True, "baseline": True}
        save_state(state)
        print(f"[기준선] 기존 산출물 {len(files)}건 기록 (기검토분, 검사 생략) — 이후 변경분부터 검사")
        return 0

    started = time.monotonic()
    failures = []
    checked = 0
    skipped_budget = 0
    for f in files:
        rel = str(f.relative_to(OUTPUT_DIR))
        sig = file_sig(f)
        prev = state.get(rel)
        if prev and prev.get("mtime") == sig["mtime"] and prev.get("size") == sig["size"]:
            continue  # 변경 없음 (이전 실패 포함 — 재보고하지 않음)
        if time.monotonic() - started > TIME_BUDGET:
            skipped_budget += 1
            continue  # 기록하지 않음 → 다음 Stop에서 재검사
        try:
            ok, reason = run_checks(f)
        except subprocess.TimeoutExpired:
            print(f"[경고] 검사 시간 초과, 다음 턴에 재시도: {rel}")
            continue
        checked += 1
        state[rel] = {**sig, "ok": ok}
        if not ok:
            failures.append((rel, reason))

    save_state(state)

    if failures:
        print(f"[검증 실패] {len(failures)}건 / 검사 {checked}건")
        for rel, reason in failures:
            print(f"- output/{rel}\n  {reason}")
        return 1
    if skipped_budget:
        print(f"[통과] 검사 {checked}건 (시간 예산으로 {skipped_budget}건 이월)")
    elif checked:
        print(f"[통과] 변경 산출물 {checked}건 검사 통과")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
