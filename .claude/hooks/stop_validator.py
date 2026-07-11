#!/usr/bin/env python3
"""Stop 훅: Claude가 턴을 끝내기 전에 Validator 파이프라인을 실행한다.
- 검증 실패 → 차단(block)하여 Claude가 스스로 고치게 함 (Self-Correction 루프)
- 같은 세션에서 2회 차단했으면 → 더 이상 막지 않고 사용자 보고로 전환 (CLAUDE.md 원칙)
- scripts/validate_pipeline.py 가 아직 없으면 조용히 통과 (Phase 1 안전장치)

validate_pipeline.py 계약: output/ 최신 HWPX를 검사하고
  exit 0 = 통과 / exit 1 = 실패(사유를 stdout에 출력)
"""
import json
import os
import subprocess
import sys

MAX_BLOCKS = 2

def main():
    data = json.load(sys.stdin)

    # 무한 루프 방지 1차: 이미 Stop 훅 때문에 계속된 턴이면 재차 강하게 막지 않는다
    stop_hook_active = data.get("stop_hook_active", False)

    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", data.get("cwd", "."))
    validator = os.path.join(project_dir, "scripts", "validate_pipeline.py")
    counter_file = os.path.join(project_dir, "logs", ".stop_attempts")

    # Phase 1: 검증 스크립트가 없으면 훅은 투명하게 통과
    if not os.path.exists(validator):
        sys.exit(0)

    # 시도 횟수 확인 (세션별)
    session = data.get("session_id", "default")
    attempts = {}
    if os.path.exists(counter_file):
        try:
            with open(counter_file, encoding="utf-8") as f:
                attempts = json.load(f)
        except Exception:
            attempts = {}
    count = attempts.get(session, 0)

    # 검증 실행
    result = subprocess.run(
        [sys.executable, validator],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=90, cwd=project_dir,
    )

    if result.returncode == 0:
        # 통과 → 카운터 초기화 후 정상 종료 허용
        attempts[session] = 0
        _save(counter_file, attempts)
        sys.exit(0)

    reason = (result.stdout or result.stderr or "검증 실패").strip()[:1500]

    if count >= MAX_BLOCKS or (stop_hook_active and count >= MAX_BLOCKS):
        # 2회 초과 → 차단하지 않고 종료 허용, 사용자에게 상황만 알림
        attempts[session] = 0
        _save(counter_file, attempts)
        print(json.dumps({
            "systemMessage": f"[검증 실패 {count}회 초과 — 자동 교정 중단, 사람 확인 필요]\n{reason}"
        }))
        sys.exit(0)

    # 차단 → Claude가 사유를 보고 스스로 수정
    attempts[session] = count + 1
    _save(counter_file, attempts)
    print(json.dumps({
        "decision": "block",
        "reason": (
            f"Validator 실패 (자동 교정 {count + 1}/{MAX_BLOCKS}회차):\n{reason}\n"
            "위 사유를 수정하고 다시 검증을 통과시키세요. "
            "페이지 초과라면 문맥을 유지하며 약 10% 압축 재작성하세요."
        ),
    }))
    sys.exit(0)

def _save(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f)

if __name__ == "__main__":
    main()
