#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""예산과목 이름 검증기 — 계획서에 쓴 예산 항목명이 사업관리카드에 실존하는지 기계 대조.

이름만 검증한다(금액은 검증 대상 아님 — 2026. 7. 15. 사용자 확인).
데이터: knowledge/reference/예산과목-*.json (refresh_reference.py 산출물).

사용 예:
  python scripts/budget_name_check.py --check "수학탐구 활동운영 학생식비"
  python scripts/budget_name_check.py --check 이름1 --check 이름2
  python scripts/budget_name_check.py --search 천체
  python scripts/budget_name_check.py --list

종료 코드: 0 전부 실존 / 1 미실존 항목 있음
"""
import argparse
import difflib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATA = ROOT / "knowledge" / "reference" / "예산과목-2026.json"


def norm(s):
    return re.sub(r"\s+", "", s)


def load_catalog(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    entries = []  # (표시경로, 이름, 층위)
    for prog in data["사업"]:
        entries.append((prog["세부사업"], prog["세부사업"], "세부사업"))
        for item in prog["세부항목"]:
            entries.append((f"{prog['세부사업']} > {item['명']}", item["명"], "세부항목"))
            for line in item["산출내역"]:
                path_str = f"{prog['세부사업']} > {item['명']} > [{line['비목']}] {line['명']}"
                entries.append((path_str, line["명"], "산출내역"))
    return data, entries


def main():
    ap = argparse.ArgumentParser(description="예산과목 이름 검증기 (기계 대조, LLM 미개입)")
    ap.add_argument("--check", action="append", default=[], help="실존 여부를 검증할 이름 (반복 가능)")
    ap.add_argument("--search", help="키워드로 예산과목 검색")
    ap.add_argument("--list", action="store_true", help="전체 산출내역 목록 출력")
    ap.add_argument("--data", default=str(DEFAULT_DATA), help="예산과목 JSON 경로")
    args = ap.parse_args()

    data, entries = load_catalog(args.data)
    print(f"[데이터] {data['source']} (스냅샷 {data['snapshot']})\n")

    if args.list:
        for path_str, _, level in entries:
            if level == "산출내역":
                print(f"  {path_str}")
        return

    if args.search:
        key = norm(args.search)
        hits = [e for e in entries if key in norm(e[1]) or key in norm(e[0])]
        if not hits:
            print(f"[검색] '{args.search}' 일치 항목 없음")
            sys.exit(1)
        print(f"[검색] '{args.search}' — {len(hits)}건:")
        for path_str, _, level in hits:
            print(f"  ({level}) {path_str}")
        return

    if not args.check:
        ap.error("--check / --search / --list 중 하나는 필요")

    by_norm = {}
    for path_str, name, level in entries:
        by_norm.setdefault(norm(name), []).append((path_str, level))
    failed = False
    for q in args.check:
        hit = by_norm.get(norm(q))
        if hit:
            for path_str, level in hit:
                print(f"[OK]   '{q}' 실존 ({level}): {path_str}")
        else:
            failed = True
            print(f"[FAIL] '{q}' — 사업관리카드에 없는 이름")
            sugg = difflib.get_close_matches(norm(q), list(by_norm), n=3, cutoff=0.5)
            for s in sugg:
                for path_str, level in by_norm[s]:
                    print(f"       ≈ 유사: ({level}) {path_str}")
    if failed:
        print("\n[결과] 미실존 이름 있음 — 임의 명칭 금지 규칙에 따라 카드의 실제 이름으로 교체하거나 사용자에게 질문할 것")
        sys.exit(1)
    print("\n[결과] 전부 실존 — 통과")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
