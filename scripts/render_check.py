#!/usr/bin/env python3
"""render_check.py — HWPX 렌더링 검증 (LLM 미개입 기계 검사)

변환본(.hwp→hwpx)·재패키징(unpack/pack) 베이스를 편집한 산출물이 한글에서
"올바르게 보이는지"를 검사한다. 텍스트 계층 검증(validate·page_guard·content_guard)은
렌더링 붕괴를 잡지 못한다 — 근거: 2026. 7. 17. 교육경비 정산서식 사례
(pyhwp 변환본의 캡션 역순·표 순서 붕괴가 검증 7겹을 통과하고 사용자 육안으로 발견됨).

검사 항목:
  1. 쪽수 대조     — 한글 COM으로 결과물·레퍼런스를 각각 열어 PageCount 비교
  2. 순서 정합     — COM으로 PDF 내보내기 → PDF 추출 텍스트에서 논리 텍스트 앵커들의
                     출현 순서가 유지되는지 (최장증가부분수열 비율로 판정)
  3. 역순 문자열   — PDF에 없는 앵커의 뒤집힌 문자열이 PDF에 있으면 역순 렌더링으로 판정
  4. 개체 잔재     — 논리 텍스트에 없는 원문자(①㉮◯류)가 PDF에 보이면 compose 등
                     비텍스트 개체 잔재로 판정

사용법:
    python scripts/render_check.py 결과.hwpx --reference 베이스.hwpx [--json] [--keep-pdf 경로]

종료 코드: 0=PASS, 1=FAIL, 3=검사 불가(COM/PDF 추출 실패 — 결과 보고에 명시할 것)
의존성: pywin32(한글 설치 필요), pypdf
"""
import argparse
import json
import re
import sys
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree

# 순서 정합 판정 기준
ANCHOR_MIN_CHARS = 6          # 공백 제거 후 이 길이 이상인 고유 문단만 앵커로 사용
ANCHOR_MAX = 80               # 앵커 최대 개수 (문서 전체에 고르게 분포하도록 샘플링)
FOUND_RATIO_MIN = 0.80        # 앵커 발견율 하한
ORDER_LIS_RATIO_MIN = 0.90    # 발견 앵커 중 순서 유지(LIS) 비율 하한
PDF_TEXT_MIN_CHARS = 100      # PDF 추출 텍스트가 이보다 짧으면 추출 실패로 간주

# 개체 잔재 의심 문자 (원문자·괄호문자 계열)
SUSPICIOUS_CHARS = set(
    "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳"
    "㉮㉯㉰㉱㉲㉳㉴㉵㉶㉷㉸㉹㉺㉻"
    "◯〇⊙"
)


def norm(s: str) -> str:
    """공백·제어문자 제거 (줄바꿈·페이지 넘김에 걸친 문자열도 이어서 비교하기 위함)."""
    return re.sub(r"\s+", "", s)


def extract_logical_lines(hwpx_path: Path) -> list[str]:
    """HWPX 논리 텍스트를 문서 순서대로 추출 (hp:t 요소, 네임스페이스 무관)."""
    lines: list[str] = []
    with zipfile.ZipFile(hwpx_path) as zf:
        sections = sorted(n for n in zf.namelist()
                          if re.fullmatch(r"Contents/section\d+\.xml", n))
        for name in sections:
            root = ElementTree.fromstring(zf.read(name))
            for el in root.iter():
                if el.tag.rsplit("}", 1)[-1] == "t":
                    text = "".join(el.itertext())
                    if text and text.strip():
                        lines.append(text.strip())
    return lines


def pick_anchors(lines: list[str]) -> list[str]:
    """고유하고 충분히 긴 문단만 앵커로 선정, 문서 전체에 고르게 분포시킨다."""
    from collections import Counter
    counts = Counter(norm(x) for x in lines)
    anchors: list[str] = []
    seen: set[str] = set()
    for line in lines:
        n = norm(line)
        if len(n) >= ANCHOR_MIN_CHARS and counts[n] == 1 and n not in seen:
            anchors.append(n)
            seen.add(n)
    if len(anchors) > ANCHOR_MAX:
        step = len(anchors) / ANCHOR_MAX
        anchors = [anchors[int(i * step)] for i in range(ANCHOR_MAX)]
    return anchors


def hancom_pages_and_pdf(src: Path, pdf_out: Path) -> int:
    """한글 COM으로 파일을 열어 쪽수를 얻고 PDF로 내보낸다."""
    import win32com.client as win32
    fmt = "HWP" if src.suffix.lower() == ".hwp" else "HWPX"
    hwp = win32.Dispatch("HWPFrame.HwpObject")
    try:
        hwp.RegisterModule("FilePathCheckDLL", "FilePathCheckerModule")
    except Exception:
        pass
    try:
        if not hwp.Open(str(src), fmt, "forceopen:true"):
            raise RuntimeError(f"한글이 파일을 열지 못함: {src}")
        pages = int(hwp.PageCount)
        if pdf_out is not None:
            if not hwp.SaveAs(str(pdf_out), "PDF", ""):
                raise RuntimeError(f"PDF 내보내기 실패: {src}")
        return pages
    finally:
        hwp.Quit()


def extract_pdf_text(pdf_path: Path) -> str:
    from pypdf import PdfReader
    reader = PdfReader(str(pdf_path))
    return "".join(page.extract_text() or "" for page in reader.pages)


def longest_increasing_len(seq: list[int]) -> int:
    import bisect
    tails: list[int] = []
    for x in seq:
        i = bisect.bisect_left(tails, x)
        if i == len(tails):
            tails.append(x)
        else:
            tails[i] = x
    return len(tails)


def main() -> int:
    ap = argparse.ArgumentParser(description="HWPX 렌더링 검증 (쪽수·순서·역순·개체 잔재)")
    ap.add_argument("output", help="검사할 결과물 .hwpx")
    ap.add_argument("--reference", help="쪽수 대조 기준 파일 (.hwpx 또는 .hwp)")
    ap.add_argument("--json", action="store_true", help="JSON으로 출력")
    ap.add_argument("--keep-pdf", help="내보낸 검증 PDF를 이 경로에 보존")
    args = ap.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    out_path = Path(args.output)
    if not out_path.exists():
        print(f"오류: 파일 없음 — {out_path}")
        return 3

    report: dict = {"output": str(out_path), "checks": {}, "fails": [], "warnings": []}

    # 1) COM: 쪽수 + PDF 내보내기
    tmpdir = tempfile.mkdtemp(prefix="render_check_")
    pdf_path = Path(args.keep_pdf) if args.keep_pdf else Path(tmpdir) / "render_check.pdf"
    try:
        out_pages = hancom_pages_and_pdf(out_path, pdf_path)
        report["checks"]["pages_output"] = out_pages
        if args.reference:
            ref_pages = hancom_pages_and_pdf(Path(args.reference), None)
            report["checks"]["pages_reference"] = ref_pages
            if out_pages != ref_pages:
                report["fails"].append(f"쪽수 불일치: 결과 {out_pages}쪽 ≠ 레퍼런스 {ref_pages}쪽")
    except Exception as exc:
        print(f"검사 불가(COM): {exc}")
        return 3

    # 2) 텍스트 확보
    try:
        pdf_text = extract_pdf_text(pdf_path)
    except Exception as exc:
        print(f"검사 불가(PDF 추출): {exc}")
        return 3
    pdf_norm = norm(pdf_text)
    if len(pdf_norm) < PDF_TEXT_MIN_CHARS:
        print(f"검사 불가: PDF 추출 텍스트가 너무 짧음 ({len(pdf_norm)}자) — 추출 실패로 간주")
        return 3

    logical_lines = extract_logical_lines(out_path)
    anchors = pick_anchors(logical_lines)
    if not anchors:
        print("검사 불가: 논리 텍스트에서 앵커를 찾지 못함")
        return 3

    # 3) 앵커 발견율·순서 정합(LIS)·역순 검출
    positions: list[int] = []
    missing: list[str] = []
    reversed_hits: list[str] = []
    for a in anchors:
        idx = pdf_norm.find(a)
        if idx >= 0:
            positions.append(idx)
        else:
            missing.append(a)
            if len(a) >= ANCHOR_MIN_CHARS and pdf_norm.find(a[::-1]) >= 0:
                reversed_hits.append(a)

    found_ratio = (len(anchors) - len(missing)) / len(anchors)
    report["checks"]["anchors_total"] = len(anchors)
    report["checks"]["anchors_found_ratio"] = round(found_ratio, 3)
    if found_ratio < FOUND_RATIO_MIN:
        report["fails"].append(
            f"앵커 발견율 미달: {found_ratio:.0%} < {FOUND_RATIO_MIN:.0%} (누락 예: "
            + " / ".join(m[:20] for m in missing[:3]) + ")")

    if reversed_hits:
        report["fails"].append(
            "역순 렌더링 검출: " + " / ".join(h[:20] for h in reversed_hits[:3]))

    if positions:
        lis_ratio = longest_increasing_len(positions) / len(positions)
        report["checks"]["order_lis_ratio"] = round(lis_ratio, 3)
        if lis_ratio < ORDER_LIS_RATIO_MIN:
            report["fails"].append(
                f"순서 정합 미달: 발견 앵커 중 순서 유지 비율 {lis_ratio:.0%} < {ORDER_LIS_RATIO_MIN:.0%}")

    # 4) 개체 잔재 (원문자류가 PDF에만 존재)
    logical_all = norm("".join(logical_lines))
    leftover = sorted(set(pdf_norm) & SUSPICIOUS_CHARS - set(logical_all))
    if leftover:
        report["fails"].append(
            "개체 잔재 의심(논리 텍스트에 없는 원문자가 렌더링됨): " + " ".join(leftover))

    ok = not report["fails"]
    report["result"] = "PASS" if ok else "FAIL"

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=1))
    else:
        print(f"{report['result']}: render-check {out_path.name}")
        for k, v in report["checks"].items():
            print(f"  {k}: {v}")
        for f in report["fails"]:
            print(f"  [FAIL] {f}")
        for w in report["warnings"]:
            print(f"  [warn] {w}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
