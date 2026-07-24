---
name: w1
description: Use when 사용자가 새 공문 작성을 요청할 때 — 기안문·가정통신문·계획서·회의록 등 신규 문서 생성 ("공문/기안/가통/계획서 만들어줘"). 받은 공문에 대한 회신·제출 처리는 w2 사용.
---

# W1 — 신규 공문 작성

표준 절차의 고정 순서 체크리스트. **규칙의 권위는 프로젝트 CLAUDE.md** — 이 문서와 충돌하면 CLAUDE.md를 따른다. 아래 각 단계를 todo로 만들어 순서대로 수행한다.

## 절차

1. **탐색**: `knowledge/examples/index.md`에서 유형·키워드 검색. 슬롯 템플릿 4종(`templates/가정통신문` · `가정통신문-고사안내` · `성립전예산요구` · `회의록-교과협의회`)에 해당하면 폴더 README의 슬롯 매핑을 읽고 `edit_hwpx.py --slot-json` 경로로 확정 — 마크다운 스켈레톤보다 우선.
2. **값 수집 — 기계화 도구만, LLM 추정 금지**:

   | 문서에 포함되면 | 필수 실행 |
   |---|---|
   | 수업 대체·융합교과 시수 | `scripts/fusion_timetable.py 날짜… --periods …` 출력값만 사용 |
   | 예산 표 | `scripts/budget_name_check.py --check 항목명…` — 표의 **전 항목**, FAIL이면 교체 또는 질문 |
   | `1. 관련:` 인용 | `scripts/related_lookup.py --doc/--search` — exit 1이면 임의 기입 금지·질문, 인용 날짜는 **시행일** |

   사용자 미제공 값은 질문 또는 플레이스홀더로 남긴다(정상 처리).
3. **초안(마크다운) 작성 → 사용자 확인** 후에만 생성 진행. 본문 요약↔첨부 상세의 공유필드는 한 값 소스로 정의.
4. **생성**: 슬롯 템플릿이면 `--slot-json` 단일 소스 주입, 아니면 hwpx 스킬로 신규 생성. 기안문 본문은 전체 굴림·12pt, 첨부(계획서·가통)는 양식 서체. 교직원 실명 대신 직책+인원수.
5. **Validator 1~9** — CLAUDE.md 파이프라인 순서 그대로: validate(실패 시 F4 경로) → fix_namespaces → `finalize_hwpx --strip-linesegarray` → validate --layout → page_guard → `--hancom` 실열림(변환·재패키징 베이스면 `render_check.py` 추가) → gonmun_lint(**hwpx 스킬 사본**)·content_guard(재사용 베이스면 forbid에 직전 문서 고유 명칭·옛 날짜)·붙임 수=첨부 수·관련번호 대조 → 원본 있으면 신구대조 → 9단계 안내 문구.
6. **저장**: `output/` + OneDrive `작업 보고용` **동시 복사**.
7. **보고**: 파일 경로 + Validator 통과 내역 + 사람이 확인할 지점(플레이스홀더·판단 지점은 표/diff) + **"발송 전 한글로 열어 확인해주세요"**.
8. **기록**: 사용자가 검토 결과를 주면 즉시 `scripts/log_review.py --file <경로> --type W1 --approved yes/no --score 1-5`. 사람이 고친 최종본은 `knowledge/examples/`에 MD 병행 환류.
