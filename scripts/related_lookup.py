#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""관련번호 인용 조회기 — knowledge/examples/md/*.md의 frontmatter를 파싱해
문서번호·제목·결재일(또는 시행일)·관련 인용을 그래프로 만들고 조회한다.

목적: "1. 관련: 기관-번호(YYYY. M. D.)"를 LLM이 암기·추정으로 채우지 않도록,
실존 문서에서 확인된 값만 기계적으로 뽑아 보여준다 (CLAUDE.md Validator §7 관련번호 대조 규칙).

사용 예:
  python scripts/related_lookup.py --doc 5458                 # 이 문서가 인용한 관련 공문 + 이 문서를 인용한 후속 공문
  python scripts/related_lookup.py --search 농어촌유학          # 제목 키워드로 검색
  python scripts/related_lookup.py --chain 3268                # 전체 인용 체인(상류+하류) 출력
  python scripts/related_lookup.py --list                      # 전체 문서 목록

종료 코드: 0 정상 / 1 조회 결과 없음
"""
import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MD_DIR = ROOT / "knowledge" / "examples" / "md"

FIELD_RE = {
    "문서번호": re.compile(r"^문서번호:\s*(.+)$", re.M),
    "제목": re.compile(r"^제목:\s*(.+)$", re.M),
    "결재일": re.compile(r"^결재일:\s*(.+)$", re.M),
    "시행일": re.compile(r"^시행일:\s*(.+)$", re.M),
}
REL_RE = re.compile(r"^관련:\s*\[(.*?)\]", re.M)
REL_ITEM_RE = re.compile(r"([^,\[\]]+?\([^)]*\))")


def load_docs():
    docs = {}
    for f in sorted(MD_DIR.glob("*.md")):
        if f.name.startswith("_"):
            continue
        text = f.read_text(encoding="utf-8")
        fm = text.split("---")[1] if text.startswith("---") else ""
        num = FIELD_RE["문서번호"].search(fm)
        num = num.group(1).strip().replace("화동중학교-", "") if num else f.stem
        title = FIELD_RE["제목"].search(fm)
        date = FIELD_RE["결재일"].search(fm) or FIELD_RE["시행일"].search(fm)
        rel_m = REL_RE.search(fm)
        rel_raw = rel_m.group(1).strip() if rel_m else ""
        rel = [r.strip() for r in REL_ITEM_RE.findall(rel_raw)] if rel_raw else []
        docs[num] = {
            "번호": num,
            "제목": title.group(1).strip() if title else f.stem,
            "날짜": date.group(1).strip() if date else "(미기재)",
            "관련": rel,
            "파일": f.name,
        }
    return docs


def find_citers(docs, num):
    """이 문서번호를 인용한 다른 문서들"""
    out = []
    for d in docs.values():
        for r in d["관련"]:
            if f"화동중학교-{num}" in r or re.search(rf"(?<!\d){num}(?!\d)", r):
                out.append(d)
                break
    return out


def print_doc(d, indent=""):
    print(f"{indent}[{d['번호']}] {d['제목']}  (날짜: {d['날짜']})")


def main():
    ap = argparse.ArgumentParser(description="관련번호 인용 조회기 (기계 파싱, LLM 암기 금지)")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--doc", help="문서번호로 조회 (예: 5458)")
    g.add_argument("--search", help="제목 키워드로 검색")
    g.add_argument("--chain", help="전체 인용 체인(상류 관련 + 하류 인용) 출력")
    g.add_argument("--list", action="store_true", help="전체 문서 목록")
    args = ap.parse_args()

    docs = load_docs()
    if not docs:
        print(f"[오류] {MD_DIR} 에서 md 파일을 찾지 못함", file=sys.stderr)
        sys.exit(1)

    if args.list:
        for num in sorted(docs, key=lambda n: (len(n), n)):
            print_doc(docs[num])
        return

    if args.search:
        hits = [d for d in docs.values() if args.search in d["제목"]]
        if not hits:
            print(f"[검색] '{args.search}' 일치 문서 없음")
            sys.exit(1)
        print(f"[검색] '{args.search}' — {len(hits)}건")
        for d in hits:
            print_doc(d)
        return

    if args.doc:
        num = args.doc.replace("화동중학교-", "")
        if num not in docs:
            print(f"[오류] 문서번호 '{num}' 을 examples/md에서 찾지 못함 — 임의 관련번호 기입 금지, 원본 확인 필요", file=sys.stderr)
            sys.exit(1)
        d = docs[num]
        print_doc(d)
        print("\n▲ 이 문서가 인용한 관련 공문 (상류):")
        if d["관련"]:
            for r in d["관련"]:
                print(f"   - {r}")
        else:
            print("   (없음)")
        citers = find_citers(docs, num)
        print("\n▼ 이 문서를 인용한 후속 공문 (하류):")
        if citers:
            for c in citers:
                print_doc(c, indent="   ")
        else:
            print("   (없음)")
        return

    if args.chain:
        num = args.chain.replace("화동중학교-", "")
        if num not in docs:
            print(f"[오류] 문서번호 '{num}' 을 찾지 못함", file=sys.stderr)
            sys.exit(1)
        seen = set()

        def walk_up(n, depth):
            if n in seen or n not in docs:
                return
            seen.add(n)
            print_doc(docs[n], indent="  " * depth)
            for r in docs[n]["관련"]:
                m = re.search(r"화동중학교-(\d+)", r)
                if m:
                    walk_up(m.group(1), depth + 1)

        def walk_down(n, depth):
            for c in find_citers(docs, n):
                if c["번호"] in seen:
                    continue
                seen.add(c["번호"])
                print_doc(c, indent="  " * depth)
                walk_down(c["번호"], depth + 1)

        print(f"[체인: {num}] 상류(관련 인용) ← 자기 → 하류(피인용)\n")
        walk_up(num, 0)
        seen.discard(num)
        print()
        walk_down(num, 1)
        return


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    main()
