#!/usr/bin/env python3
"""PostToolUse 훅: 파일 생성/수정을 logs/audit.jsonl 에 자동 기록.
LLM에게 기록을 맡기지 않고 훅이 결정적으로 남긴다.
"""
import json
import os
import sys
from datetime import datetime

def main():
    data = json.load(sys.stdin)
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", data.get("cwd", "."))
    log_dir = os.path.join(project_dir, "logs")
    os.makedirs(log_dir, exist_ok=True)

    entry = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "agent": "hook",
        "action": data.get("tool_name", ""),
        "target": (data.get("tool_input") or {}).get("file_path", ""),
        "result": "ok",
    }
    with open(os.path.join(log_dir, "audit.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    sys.exit(0)

if __name__ == "__main__":
    main()
