#!/usr/bin/env python3
"""PreToolUse 훅: CLAUDE.md 금지 규칙을 강제한다.
- knowledge/, docs/ 폴더의 기존 파일 덮어쓰기 차단 (원본 보존)
- 신규 파일 생성은 허용 (파생물: md 변환본·index·템플릿 — 2026. 7. 8. 사용자 승인)
- 파생물 화이트리스트(.md 한정)는 기존 파일이라도 갱신 허용 (2026. 7. 24. 사용자 승인)
- 위험한 셸 명령 차단
exit 0 = 허용, exit 2 = 차단 (stderr 메시지가 Claude에게 전달됨)
"""
import json
import os
import re
import sys

PROTECTED_DIRS = ("knowledge/", "knowledge\\", "docs/", "docs\\")
# 에이전트가 만들고 유지보수하는 파생물 — 원본(발송본 hwpx·pdf) 보호는 그대로 두고
# 갱신을 허용한다. .md 확장자에 한정해 원본이 이 경로에 놓여도 보호가 유지된다.
DERIVED_WHITELIST = ("knowledge/examples/index.md", "knowledge/examples/md/")
DANGEROUS_PATTERNS = [
    r"\brm\s+-rf\b",
    r"\bdel\s+/[sq]\b",
    r"\brmdir\s+/s\b",
    r"\bformat\s+[a-z]:",
    r"\btaskkill\b",
]

def main():
    # 한국어 Windows 콘솔(cp949)에서 차단 메시지 한글 깨짐 방지
    sys.stderr.reconfigure(encoding="utf-8")
    data = json.load(sys.stdin)
    tool = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})

    if tool in ("Write", "Edit"):
        raw_path = tool_input.get("file_path") or ""
        path = raw_path.replace("\\", "/")
        derived = path.endswith(".md") and any(w in path for w in DERIVED_WHITELIST)
        for d in PROTECTED_DIRS:
            d_norm = d.replace("\\", "/")
            if f"/{d_norm}" in f"/{path}" and "/output" not in path and not derived:
                # 신규 파일 생성은 허용, 기존 파일(원본 포함) 수정·덮어쓰기만 차단
                if not os.path.exists(raw_path):
                    break
                print(
                    f"차단: '{path}' 는 보호 폴더의 기존 파일입니다. "
                    "원본은 수정 금지 — 수정본은 output/ 에 새 파일로 저장하세요.",
                    file=sys.stderr,
                )
                sys.exit(2)

    if tool == "Bash":
        cmd = tool_input.get("command", "")
        for pat in DANGEROUS_PATTERNS:
            if re.search(pat, cmd, re.IGNORECASE):
                print(f"차단: 위험한 명령 패턴 감지 ({pat}). 사용자 확인이 필요합니다.", file=sys.stderr)
                sys.exit(2)

    sys.exit(0)

if __name__ == "__main__":
    main()
