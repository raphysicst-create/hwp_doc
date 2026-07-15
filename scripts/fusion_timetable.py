#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""융합교과 산출기 — 활동 날짜·교시에서 대체되는 과목을 기계적으로 계산한다.

요일은 Python datetime으로 계산(LLM 암산 금지 원칙과 동일 취지, DATE_WEEKDAY와 짝).
시간표 데이터는 knowledge/reference/기초시간표-*.json (refresh_reference.py 산출물).

사용 예:
  python scripts/fusion_timetable.py 2026-09-16 --periods 1-4
  python scripts/fusion_timetable.py "2026. 9. 16." "2026. 9. 17." --periods 5,6 --grades 1
  python scripts/fusion_timetable.py 2026-09-16 --periods 1-4 --json

종료 코드: 0 정상 / 2 입력 오류(주말·형식 등)
"""
import argparse
import datetime
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATA = ROOT / "knowledge" / "reference" / "기초시간표-2026-2학기.json"
WEEKDAYS = ["월", "화", "수", "목", "금", "토", "일"]


def parse_date(s):
    nums = re.findall(r"\d+", s)
    if len(nums) != 3:
        raise ValueError(f"날짜 형식을 해석할 수 없음: {s!r}")
    return datetime.date(int(nums[0]), int(nums[1]), int(nums[2]))


def parse_periods(s):
    out = []
    for part in s.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-", 1)
            out.extend(range(int(a), int(b) + 1))
        else:
            out.append(int(part))
    bad = [p for p in out if not 1 <= p <= 8]
    if bad:
        raise ValueError(f"교시는 1~8 범위여야 함: {bad}")
    return sorted(set(out))


def fmt_korean(d):
    return f"{d.year}. {d.month}. {d.day}."


def main():
    ap = argparse.ArgumentParser(description="융합교과 산출기 (기계 계산, LLM 미개입)")
    ap.add_argument("dates", nargs="+", help="활동 날짜 (2026-09-16 / 2026. 9. 16. 등)")
    ap.add_argument("--periods", required=True, help="교시: 1-4 또는 1,3,5")
    ap.add_argument("--grades", default="1,2", help="학년: 1,2 (기본 전체)")
    ap.add_argument("--data", default=str(DEFAULT_DATA), help="시간표 JSON 경로")
    ap.add_argument("--json", action="store_true", help="구조화 JSON으로 출력")
    args = ap.parse_args()

    data = json.loads(Path(args.data).read_text(encoding="utf-8"))
    table, full, non_subject = data["시간표"], data["subject_full"], set(data["non_subject"])

    errors = []
    try:
        periods = parse_periods(args.periods)
    except ValueError as e:
        sys.exit(f"[오류] {e}")
    grades = [g.strip() for g in args.grades.split(",")]
    for g in grades:
        if g not in data["grades"]:
            sys.exit(f"[오류] 학년 '{g}' 은 시간표에 없음 (가능: {list(data['grades'])})")

    days_out = []
    counts = {g: Counter() for g in grades}
    non_subject_hits = []
    for ds in args.dates:
        try:
            d = parse_date(ds)
        except ValueError as e:
            errors.append(str(e))
            continue
        wd = WEEKDAYS[d.weekday()]
        if wd in ("토", "일"):
            errors.append(f"{fmt_korean(d)} 은 {wd}요일(주말) — 기초 시간표에 없음")
            continue
        rows = []
        for p in periods:
            row = {"교시": p}
            for g in grades:
                v = table[wd][g][p - 1]
                label = full.get(v, v)
                row[g] = label
                if v in non_subject:
                    non_subject_hits.append(f"{fmt_korean(d)}({wd}) {p}교시 {g}학년: {label}")
                elif v:
                    counts[g][label] += 1
            rows.append(row)
        days_out.append({"날짜": fmt_korean(d), "요일": wd, "교시별": rows})

    if errors:
        for e in errors:
            print(f"[오류] {e}", file=sys.stderr)
        sys.exit(2)

    total = Counter()
    for g in grades:
        total.update(counts[g])
    result = {
        "요일검증": "Python datetime 기계 계산",
        "교시": periods,
        "학년": grades,
        "일자별": days_out,
        "시수집계": {g: dict(counts[g]) for g in grades},
        "시수집계_합계": dict(total),
        "비교과_경고": non_subject_hits,
        "주의": "기초 시간표 기준 — 단축수업·고사·행사 등 특별시간표 미반영",
    }
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    for day in days_out:
        print(f"■ {day['날짜']}({day['요일']})  — 요일 기계 검증됨")
        header = "  교시 | " + " | ".join(f"{g}학년" for g in grades)
        print(header)
        for row in day["교시별"]:
            print(f"  {row['교시']:>4} | " + " | ".join(f"{row[g]}" for g in grades))
        print()
    print("■ 융합교과 시수 집계 (전 날짜 합산)")
    subjects = sorted(total, key=lambda s: -total[s])
    print("  과목 | " + " | ".join(f"{g}학년" for g in grades) + " | 계")
    for s in subjects:
        print(f"  {s} | " + " | ".join(str(counts[g].get(s, 0)) for g in grades) + f" | {total[s]}")
    if non_subject_hits:
        print("\n[경고] 비교과 시간이 포함됨 (융합교과 표에 넣을지 사용자 판단 필요):")
        for h in non_subject_hits:
            print(f"  - {h}")
    print("\n[주의] 기초 시간표 기준 — 단축수업·고사기간·학사행사 등 특별시간표는 미반영")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    main()
