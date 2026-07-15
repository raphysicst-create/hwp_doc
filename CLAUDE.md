# CLAUDE.md — 공문 자동 작성 에이전트

## 프로젝트 목적
공문 초안 작성 → HWPX 생성 → 검증까지 자동화한다. 전자결재(온나라) 등록은 사람이 한다.
상세 설계는 `docs/설계도-v4.md` 참조. 이 파일은 매 세션 지켜야 할 실행 규칙이다.
**운영 원칙: 실패 주도 성장** — 규칙·데이터·자동화는 실제 발생한 실패에서만 추가한다.

## 확정된 환경
- Windows + 한글 설치됨 (검토 시 한글 열람 가능)
- **최종 제출 포맷: HWPX**
- **MVP 성공 기준 (2026. 7. 15. 개정)**: W1(신규)·W2(회신) 각 5건에 대해 사용자가 검토 후 **동의(approved) + 5점 만점 평가**를 남길 것. 발송 여부는 무관 — 발송은 항상 사람이 하며 에이전트가 확인할 방법도 없다. `scripts/log_review.py --file <경로> --type W1|W2 --approved yes/no --score 1-5`로 기록, `--summary`로 누적 현황 확인

## 도구 (역할 → 어댑터)
| 역할 | 도구 | 용도 |
|------|------|------|
| Reader | kordoc (MCP) | HWP3~5·HWPX·PDF·XLS·DOCX → Markdown, 구조 분석, diff |
| Editor 주력 | Canine89/hwpxskill | 신규 생성, 양식 보존 교체, 템플릿, page_guard |
| Editor 보조 | kordoc patch_document / fill_form | 특정 셀·문단만 패치 |
| 폴백 | jkf87/hwpx-skill | validate 실패 시 재생성 용도로만 (F4) |
| 보류 | hwp-mcp | 사용하지 않음. 표 구조 변경이 월 수 회 이상 실제 발생하면 사용자와 도입 논의 |

## 라우팅 규칙
- 새 문서 / 양식 유지 + 내용 교체 → Canine89
- 특정 셀·문단만 수정 → kordoc patch_document / fill_form
- 표 구조 변경(행·열·병합) → MD 추출 → 수정 → Canine89 재생성 (우회가 기본)
- `.hwp` 입력: 읽기는 kordoc 우선, kordoc 실패 시에만 hwpx-fallback의 `convert_hwp.py`로 변환(이 경우만 폴백 스킬 사용 허용). 변환본을 편집 베이스로 쓸 때는 사용자에게 고지. `.hwp`로 결과물을 만드는 것은 항상 거부.
- **확신이 없으면 임의 진행하지 말고 사용자에게 질문한다.**

## 기계화 도구 (LLM 미개입 조회·검증, `scripts/`) — 2026. 7. 15.
- `refresh_reference.py` — `knowledge/reference/` 원본(기초시간표 xlsx·사업관리카드 xls)에서 JSON·MD 파생 파일 재생성. 원본이 갱신되면 파일 교체 후 이것만 재실행. **파생 md/json은 손으로 수정 금지** (전역 훅도 차단함)
- `fusion_timetable.py 날짜… --periods 1-4 [--grades 1,2] [--json]` — 활동일 요일 계산 + 대체 과목·융합교과 시수 집계. **융합교과 계획은 반드시 이 출력값으로 작성** — LLM이 시간표를 읽어 추정하지 않는다. 주말이면 exit 2, 비교과 시간(동아리 등) 포함 시 경고. 특별시간표(단축·고사·행사) 미반영이 한계 → 의심되면 사용자 확인
- `budget_name_check.py --check 이름… / --search 키워드 / --list` — 계획서 예산 항목명이 사업관리카드에 실존하는지 대조 (이름만 검증, 금액 무관 — 2026. 7. 15. 확인). **계획서 생성 후 예산 표의 모든 항목명에 대해 실행**, FAIL이면 실제 이름으로 교체하거나 사용자에게 질문
- `related_lookup.py --doc 번호 / --chain 번호 / --search 키워드` — 관련번호 인용 체인을 `examples/md/` frontmatter에서 기계 파싱. Validator §7 관련번호 인용 대조에 사용, exit 1(못 찾음)이면 임의 기입 금지
- `log_review.py --file 경로 --type W1|W2 --approved yes/no --score 1-5 [--note] / --summary` — 검토 동의+5점 평가 기록. MVP 성공 기준(위 참조) 판단은 이 로그의 `--summary` 결과로 한다

## 절대 금지 규칙
1. **마크다운 표만 보고 "n번째 행/열"로 위치를 추정해 기입하지 않는다.** 반드시 ① 플레이스홀더(`[[필드명]]`) 치환 또는 ② Reader가 산출한 블록 인덱스 + (row, col) 셀 주소만 사용.
2. Human Approval 생략 금지. 어떤 문서도 "발송 완료"로 처리하지 않는다 — 산출물은 항상 `output/` + 검토 요청으로 끝난다.
   **동시 산출(2026. 7. 13. 원칙)**: 최종 산출물(hwpx 등 검토 대상 파일)은 `output/` 저장과 **동시에** OneDrive `C:\Users\22\OneDrive - 화동중학교\작업 보고용\`에도 복사한다 (외부/모바일 확인용. budget·structure 프로파일 등 작업 부산물은 제외).
3. 암호화·DRM·배포용 문서는 우회 시도 없이 즉시 보고.
4. 원본 파일을 직접 덮어쓰지 않는다. 수정본은 항상 새 파일로 저장.
5. 개인정보(주민번호 등)가 보이면 사용자에게 알리고 처리 방침을 확인받는다.

## 공문서 작성 규정 (2025 개정 기준)
- **기안문(본문 HWPX) 서체: 전체 굴림, 본문 12pt(height 1200)** — 2026. 7. 13. 사용자 지정 원칙. 기관명 등 제목부는 크기 유지하되 서체는 굴림. 첨부 계획서·가정통신문은 양식(레퍼런스) 서체를 따른다
- 항목부호 8단계 순서: `1.` → `가.` → `1)` → `가)` → `(1)` → `(가)` → `①` → `㉮`
- 날짜: `2026. 7. 7.` 형식 (연월일 뒤 온점, 월·일 앞자리 0 없음)
- 시간: `14:30` / 금액: `금123,456원(금일십이만삼천사백오십육원)`
- 본문 끝: 마지막 글자에서 한 글자 띄우고 `끝.` / 붙임이 있으면 붙임 표시 후 `끝.`
- 초안 작성 전 `knowledge/examples/`에서 유사 공문을 검색해 형식을 따른다 (있는 경우)

## 표준 워크플로
### W1 신규 공문
1. `knowledge/examples/index.md`에서 유형·문서번호로 검색 → `knowledge/templates/`에 해당 유형 본문 스켈레톤이 있으면 그것을 골격으로 사용 (매핑 표는 index.md 상단, 없으면 규정만으로 진행)
   - **슬롯 템플릿 4종 (2026. 7. 15. 승격, index.md 매핑 표는 훅 보호로 미갱신 — 여기가 최신)**: `templates/가정통신문/`(일반 가통) · `templates/가정통신문-고사안내/`(고사 안내 가통, 표 구조 다르면 재생성 경로) · `templates/성립전예산요구/`(기안문 본문) · `templates/회의록-교과협의회/`(고사 출제 협의). 각 폴더 README의 슬롯 매핑·주의사항을 따라 `edit_hwpx.py --slot-json`으로 채운다 — 마크다운 스켈레톤보다 우선
2. 초안 작성 (마크다운) → 사용자 확인
3. Canine89로 HWPX 생성 — 본문 요약(일시·장소·대상 등)과 첨부 상세는 **한 값 소스에서 양쪽에 주입**하고 생성 후 값 일치를 확인한다 (공유필드 정합, 세트 md의 `공유필드:` 참조)
4. Validator 파이프라인 통과
5. `output/`에 저장 + OneDrive `작업 보고용` 동시 복사 + 검토 요청
6. 사용자가 검토 결과(동의 여부·5점 평가)를 알려주면 `scripts/log_review.py`로 즉시 기록

### W2 회신 공문
1. 수신 공문을 kordoc으로 파싱 → 요지·요청사항·회신기한·**제출 방법** 추출
2. 제출 방법에 따라 분기: 공문 회신 지정 → 회신 시행문(변형 A) / 시스템·메일 제출 → 내부결재(변형 B). 골격은 `knowledge/templates/본문-제출회신.md`
3. 이후 W1의 2~6과 동일. 본문에 원 공문의 문서번호·시행일자를 인용

### 검토 환류 (모든 워크플로 공통)
사람이 검토에서 고친 최종본은 `knowledge/examples/`에 저장한다 (MD 변환본 병행).
같은 유형의 지적이 2회 나오면 → 해당 검증 규칙을 Validator에 추가하자고 사용자에게 제안한다.

## Validator 파이프라인 (생성 후 필수, 순서는 hwpx SKILL.md 기준)
1. validate (스키마 검증) — 실패 시 F4: validate 재실행 1회 → 여전히 실패 시 hwpx-fallback의 **워크플로우 F(양식 있음) 또는 A(양식 없음)**로 재생성 → 재생성물에 `fill_hwpx.py check --strict` 통과 후, **주력 hwpx 스킬의 page_guard·content_guard·gonmun_lint를 다시 적용**(스크립트는 `.claude/skills/hwpx/scripts/` 경로로 직접 실행)해야 완료
2. fix_namespaces 실행
3. finalize_hwpx --strip-linesegarray (줄 배치 캐시 제거 + 레이아웃 위험 경고)
4. validate --layout
5. page_guard — 페이지 초과 시 "문맥 유지, 약 10% 압축 재작성" 자기 교정 **최대 2회**, 실패 시 사용자 보고
   - **의도된 구조 변경 경로**: 사용자가 표 행·열 추가 등 구조 변경을 명시 승인한 작업은 기본 fingerprint 검사가 FAIL하는 것이 정상. 이때는 ① FAIL 사유가 승인된 변경 그 자체뿐인지 확인해 보고에 명시하고, ② 결과물 크기를 원본 자리(폭·높이)에 맞춰 쪽수를 보존하며, ③ 승인된 결과물로 `--write-budget/--write-structure` 프로파일을 재생성해 이후 수정의 새 기준으로 삼는다 (2026. 7. 7. 취약시기 문화체험 v2 사례)
6. (가능 시) `finalize_hwpx.py 결과.hwpx --hancom`으로 한컴 실열림 검사 — pywin32 부재 등으로 불가하면 그 사실을 보고에 명시
7. 규칙 검증(gonmun_lint·content_guard) 최소셋: 날짜 형식·항목부호 순서(자동 수정) / **날짜-요일 정합은 gonmun_lint(DATE_WEEKDAY)가 기계 검증** — LLM의 요일 계산은 신뢰하지 않는다 / 붙임 언급 수 = 실제 첨부 수(불일치 보고) / **기존 문서를 재활용한 작업이면 content_guard forbid에 직전 문서의 고유 명칭(행사명·강사명·기관명)을 반드시 넣어 복사 잔재 검사** (사례: 사람책 도서관 잔재가 예산·기대효과에 남음, 2026. 7. 7.)
   - gonmun_lint는 항상 `.claude/skills/hwpx/scripts/gonmun_lint.py` 사본을 실행한다 (폴백 사본에는 DATE_WEEKDAY 검증이 없음)
   - **관련번호 인용 대조**: `1. 관련:`의 `기관-번호(YYYY. M. D.)`는 실존 문서에서 확인된 값만 쓴다 — W2는 받은 공문 원문에서, 가통 배부·후속 공문은 선행 자교 공문에서(`scripts/related_lookup.py --doc <번호>`로 상류·하류 인용 기계 조회, `--chain`으로 전체 체인, `--search`로 키워드 검색), 규정 근거는 상급기관 번호 병기 가능. 인용 날짜는 그 문서의 **시행일**(결재일과 다를 수 있음, 6487 사례). 스크립트가 찾지 못하면(exit 1) 임의 기입하지 말고 사용자에게 질문 — received/·sent/도 비어 있으면 원본 요청
8. 원본이 있는 작업이면 kordoc compare_documents로 신구대조 생성
9. 검토 요청 시 반드시 안내: **"발송 전 한글로 열어 확인해주세요"** (스키마 통과 ≠ 한글에서 열림 보장, 이것이 최종 방어선)

## 실패 처리
- 동일 단계 **2회 실패 시 자동 시도 중단**, 시도 이력과 함께 사용자에게 보고.
- kordoc 파싱 실패 → 포맷 변환 후 재시도 → jkf87 변환기 경유
- kordoc MCP 도구가 목록에 없거나 호출이 연결 오류로 실패하면: ① HWPX 읽기는 `.claude/skills/hwpx/scripts/text_extract.py --format markdown`으로 대체, ② PDF는 Read 도구로 직접 판독, ③ 셀 패치는 hwpx 스킬 `edit_hwpx.py --cell/--slot-json`으로 대체, ④ diff는 두 파일의 text_extract 결과 비교로 대체하고 보고에 'kordoc 미사용' 명시
- 스캔 PDF → OCR → 실패 시 이미지로 직접 판독
- kordoc skipped[] 발생 → 해당 항목만 Canine89 재시도 → 전체 재생성

## 폴더 구조 (최소 시작, 필요 시 확장)
```
knowledge/
├── examples/     # 잘 쓴 공문 + 검토 통과본 환류 (MD 변환본 병행)
├── templates/    # 반복 양식 (슬롯 태깅 완료: 가정통신문·성립전예산요구·가정통신문-고사안내·회의록)
├── reference/    # 기초 시간표·예산 사업관리카드 등 기계 조회 원본+파생 데이터
├── sent/  received/  phrases.md   # 쌓이는 대로
output/           # 산출물 (검토 대기)
logs/audit.jsonl     # 감사 로그
logs/review_log.jsonl  # 검토 동의·점수 기록 (scripts/log_review.py)
docs/             # 설계도 v4
scripts/          # 기계화 도구 (LLM 미개입 조회·검증)
```

## Audit Log
주요 액션(파싱·초안·생성·검증·자기교정)마다 `logs/audit.jsonl`에 한 줄:
`{"ts","agent","action","target","result","detail"}` — 실패도 반드시 기록.

## 훅 (규칙의 강제 계층)
프로즈 규칙은 조언이고, 어기면 대가가 큰 규칙은 훅으로 강제한다. 설정: `.claude/settings.json`
- **PreToolUse** `protect_files.py`: knowledge/·docs/ **기존 파일 덮어쓰기** 차단(신규 파일 생성은 허용 — 환류 저장용, 금지 규칙 4), 위험 셸 명령 차단
- **PostToolUse** `audit_log.py`: 파일 생성·수정을 audit.jsonl에 자동 기록
- **Stop** `stop_validator.py`: `scripts/validate_pipeline.py`가 존재하면 턴 종료 전 실행. 실패 시 차단 → Self-Correction 루프, **2회 초과 시 차단 해제 + 사용자 보고**. 스크립트가 없으면 투명하게 통과 (현재 상태)
- 활성화 순서: 세션 1(관통 테스트)은 훅 없이도 가능 → `python scripts/log_review.py --summary`로 W1·W2 각 5건 동의 확인되면(MVP 달성) validate_pipeline.py 작성으로 Stop 루프 활성화 → W1·W2를 `.claude/skills/` 커맨드로 승격
- **전역 훅(2026. 7. 11.)**: `C:\Users\22\.claude\hooks\hwp_doc_guard.py`가 user settings.json에 등록됨 — 프로젝트 밖 세션(텔레그램 경유 홈 세션 등)에서도 보호 폴더 차단(pre)과 audit.jsonl 자동 기록(post)을 경로 감지로 강제. 프로젝트 안 세션에서는 이중 기록을 피하려고 post가 스스로 건너뜀
- Stop 훅 수정 시 무한 루프 방지 로직(stop_hook_active, 시도 카운터)을 제거하지 않는다

## 응답 스타일
- 산출물 완성 시: 파일 경로 + Validator 통과 내역 + 사람이 확인할 지점을 요약 보고, "한글로 열어 확인" 안내 포함
- 판단이 필요한 지점(플레이스홀더 매핑, 압축으로 삭제된 문장 등)은 diff나 표로 보여주고 확인받는다
