#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""검토 결과 기록기 — 발송 여부가 아니라 사용자 동의(approved) + 5점 평가로 성공을 판단한다.

MVP 성공 기준(CLAUDE.md, 2026. 7. 15. 개정): W1·W2 각 5건에 대해 사용자가 검토 후
동의(approved) + 5점 만점 평가를 남기면 해당 건은 "성공"으로 집계된다. 실제 온나라 발송
여부와는 무관 — 발송은 항상 사람이 하고 에이전트는 관여하지 않는다(CLAUDE.md 금지 규칙 2).

사용 예:
  python scripts/log_review.py --file output/2026_농어촌유학_수리과학체험_기안문.hwpx \
      --type W1 --approved yes --score 4 --note "붙임 표기만 수정"
  python scripts/log_review.py --summary
"""
import argparse
import datetime
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG = ROOT / "logs" / "review_log.jsonl"


def append_entry(args):
    entry = {
        "ts": datetime.datetime.now().isoformat(timespec="seconds"),
        "file": args.file,
        "type": args.type,
        "approved": args.approved == "yes",
        "score": args.score,
        "note": args.note or "",
    }
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(f"[기록] {entry['type']} {entry['file']} — 동의={entry['approved']}, 점수={entry['score']}/5")


def summarize():
    if not LOG.exists():
        print("[요약] 아직 기록된 검토 없음 (logs/review_log.jsonl 없음)")
        return
    # 파일별 최신 기록만 유효 (재검토 시 이전 평가는 덮어씀)
    latest = {}
    with LOG.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            e = json.loads(line)
            latest[e["file"]] = e

    by_type = {}
    for e in latest.values():
        by_type.setdefault(e["type"], []).append(e)

    print(f"[데이터] {LOG} — 문서 {len(latest)}건 (최신 평가 기준)\n")
    for t in sorted(by_type):
        entries = by_type[t]
        approved = [e for e in entries if e["approved"]]
        avg = sum(e["score"] for e in approved) / len(approved) if approved else 0
        print(f"■ {t}: 동의 {len(approved)}/5건 목표 (총 평가 {len(entries)}건), 평균 {avg:.1f}/5점")
        for e in sorted(entries, key=lambda x: x["ts"]):
            mark = "OK" if e["approved"] else "반려"
            print(f"   [{mark}] {e['score']}/5  {e['file']}  {e['note']}")
        if len(approved) >= 5:
            print(f"   → MVP 기준 충족 ({t} 5건 동의)")
        print()


def main():
    ap = argparse.ArgumentParser(description="검토 결과 기록기 (동의+점수 기준, 발송 여부 무관)")
    sub = ap.add_mutually_exclusive_group(required=True)
    sub.add_argument("--file", help="검토 대상 파일 경로")
    sub.add_argument("--summary", action="store_true", help="누적 현황 요약")
    ap.add_argument("--type", choices=["W1", "W2"], help="--file 사용 시 필수")
    ap.add_argument("--approved", choices=["yes", "no"], help="--file 사용 시 필수 — 사용자 동의 여부")
    ap.add_argument("--score", type=float, help="--file 사용 시 필수 — 5점 만점 (0.5 단위 가능, 예: 4.5)")
    ap.add_argument("--note", default="", help="검토 코멘트 (선택)")
    args = ap.parse_args()

    if args.summary:
        summarize()
        return
    if not (args.type and args.approved and args.score):
        ap.error("--file 사용 시 --type, --approved, --score 모두 필요")
    if not (0 < args.score <= 5):
        ap.error("--score는 0 초과 5 이하여야 함")
    append_entry(args)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
