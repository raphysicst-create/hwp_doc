---
name: hwpx
description: "한글 HWPX 문서 생성/읽기/편집 스킬. .hwpx 파일, Hancom, OWPML 관련 요청 시 사용. .hwp 바이너리 파일 작성/생성/직접 편집 요청은 거부한다."
---

# HWPX 문서 스킬 — 레퍼런스 복원 우선(XML-first) 워크플로우

한글(Hancom Office)의 HWPX 파일을 **XML 직접 작성** 중심으로 생성, 편집, 읽기할 수 있는 스킬.
HWPX는 ZIP 기반 XML 컨테이너(OWPML 표준)이다. 서식 보존이 중요한 편집에서는 OWPML XML을 직접 다뤄 charPr, paraPr, 표 구조를 세밀하게 제어한다.

## HWP 바이너리 요청 거부 규칙 (필수)

이 스킬은 **HWPX 전용**이다. 사용자가 `.hwp` 바이너리 파일의 작성, 생성, 저장, 편집, 채우기, 변환 결과물 생성을 요청하면 해당 작업은 수행하지 않는다.

- `.hwp`로 결과 파일을 만들어 달라는 요청은 거부한다.
- `.hwp` 원본을 직접 수정하거나 채워 달라는 요청은 거부한다.
- `.hwp`를 읽어 참고하는 수준은 가능하지만(읽기·변환은 이 스킬이 아니라 kordoc/폴백 담당), 결과물은 사용자가 명시적으로 HWPX를 허용한 경우에만 `.hwpx`로 만든다.
- 사용자가 `.hwp` 작성을 요청했는데 HWPX 대체 산출물을 명시적으로 허용하지 않았다면, 임의로 `.hwpx` 파일을 만들어 대신 완료 처리하지 않는다.
- 안내 문구는 간단히 쓴다: "이 스킬은 HWPX만 지원해서 .hwp 작성은 할 수 없습니다. 한글에서 HWPX로 저장한 파일을 주거나, 결과물을 .hwpx로 받는 방식이면 처리할 수 있습니다."

## 기본 동작 모드 (필수): 첨부 HWPX 분석 → 고유 XML 복원(99% 근접) → 요청 반영 재작성

사용자가 `.hwpx`를 첨부한 경우, 이 스킬은 아래 순서를 **기본값**으로 따른다.

1. **레퍼런스 확보**: 첨부된 HWPX를 기준 문서로 사용
2. **슬롯 추출**: `hwpx_slots.py`로 편집 가능한 문단/셀 슬롯 목록을 JSON으로 만든다
3. **사용자 값 매핑**: 슬롯 키(`p:12`, `cell:0:2:1`)에 새 값을 매핑한다
4. **구조 보존 편집**: `edit_hwpx.py --slot-json`으로 원본 패키지를 복제하고 슬롯 텍스트만 수정
5. **빌드/검증**: `edit_hwpx.py` 결과 또는 `build_hwpx.py` 결과를 `validate.py`로 무결성 확인. **11개 최소 패키지 완비를 여기서 검사한다**(2026. 8. 20. 확장) — `Preview/` 2종과 `META-INF/container.rdf`가 빠져도 한글은 그냥 열리므로 9단계 COM 실열림으로는 절대 안 잡힌다. 누락이 뜨면 **한컴에서 열어 「다른 이름으로 저장」**하는 것이 가장 확실한 복구다
6. **최종화/레이아웃 경고**: `fix_namespaces.py`, `finalize_hwpx.py --strip-linesegarray --layout`, `validate.py --layout`로 네임스페이스와 렌더링 위험을 점검한다
7. **글자 예산/쪽수 가드(필수)**: `page_guard.py`로 문단/셀별 글자 예산과 레퍼런스 대비 페이지 드리프트 위험 검사
8. **내용 완성도 가드(필수)**: `content_guard.py`로 원문 잔재, placeholder, 필수 키워드 누락을 검사한다
9. **한컴 실열림(필수)**: `finalize_hwpx.py --hancom`으로 한글이 실제로 파일을 여는지 COM으로 확인한다 (pywin32 + 보안모듈 등록 완료, 2026. 7. 18.)
10. **셀 폭 초과 육안 검증(조건부 필수)**: 셀 예산을 넘긴 텍스트를 넣었으면 PDF로 내보내 이미지로 렌더한 뒤 **직접 본다**. 1~9단계는 전부 통과하면서도 셀 안 줄바꿈·글자 밀림은 못 잡는다 (2026. 8. 20. 실패, 아래 「실패 이력」 참조). 발동 조건과 정책은 프로젝트 CLAUDE.md Validator 6단계가 정본

### 99% 근접 복원 기준 (실무 체크리스트)

- `charPrIDRef`, `paraPrIDRef`, `borderFillIDRef` 참조 체계 동일
- 표의 `rowCnt`, `colCnt`, `colSpan`, `rowSpan`, `cellSz`, `cellMargin` 동일
- 문단 순서, 문단 수, 주요 빈 줄/구획 위치 동일
- 페이지/여백/섹션(secPr) 동일
- 변경은 사용자 요청 범위(본문 텍스트, 값, 항목명 등)로 제한
- 내용 변경 요청이 문서 전체의 관점 전환(예: 한국 기관 → 미국 기관, 특정 회사 → 다른 회사)이라면 이전 기관명/담당자/전화번호/정책명 잔재가 남으면 실패

### 쪽수 동일(100%) 필수 기준

- 사용자가 레퍼런스를 제공한 경우 **결과 문서의 최종 쪽수는 레퍼런스와 동일해야 한다**
- 쪽수가 늘어날 가능성이 보이면 먼저 텍스트를 압축/요약해서 기존 레이아웃에 맞춘다
- 사용자 명시 요청 없이 `hp:p`, `hp:tbl`, `rowCnt`, `colCnt`, `pageBreak`, `secPr`를 변경하지 않는다
- `validate.py` 통과만으로 완료 처리하지 않는다. 반드시 `page_guard.py`와 `content_guard.py`도 통과해야 한다
- `page_guard.py` 또는 `content_guard.py` 실패 시 결과를 완료로 제출하지 않고, 원인(길이 과다/구조 변경/원문 잔재/필수 키워드 누락)을 수정 후 재빌드한다
- 가능하면 한글(또는 사용자의 확인) 기준 최종 쪽수 값을 확인하고 레퍼런스와 일치 여부를 재확인한다

### 기본 실행 명령 (첨부 레퍼런스가 있을 때)

```bash
# 1) 레퍼런스 분석 + XML 추출
"$PY" "$SKILL_DIR/scripts/analyze_template.py" reference.hwpx \
  --extract-header /tmp/ref_header.xml \
  --extract-section /tmp/ref_section.xml

# 2) 편집 가능한 슬롯 추출
"$PY" "$SKILL_DIR/scripts/hwpx_slots.py" reference.hwpx \
  --output /tmp/reference.slots.json

# 3) 원본 양식의 문단/셀별 글자 예산 저장
"$PY" "$SKILL_DIR/scripts/page_guard.py" \
  --reference reference.hwpx \
  --write-budget /tmp/reference.budget.json \
  --write-structure /tmp/reference.structure.json

# 3-1) 내용 완성도 규칙 작성
# 예: 한국 고용노동부 보도자료를 미국노동부 문서로 바꾸는 경우
cat > /tmp/content.rules.json <<'JSON'
{
  "require": ["미국노동부"],
  "forbid": ["고용노동부", "김영훈", "044-"],
  "forbid_regex": ["○○+", "\\.\\s*\\.\\s*\\."]
}
JSON

# 4) 양식 보존 편집
"$PY" "$SKILL_DIR/scripts/edit_hwpx.py" reference.hwpx \
  --output result.hwpx \
  --slot-json values.json

# 5) 검증 + 최종화
"$PY" "$SKILL_DIR/scripts/validate.py" result.hwpx
"$PY" "$SKILL_DIR/scripts/fix_namespaces.py" result.hwpx
"$PY" "$SKILL_DIR/scripts/finalize_hwpx.py" result.hwpx --strip-linesegarray --layout
"$PY" "$SKILL_DIR/scripts/validate.py" result.hwpx --layout

# 6) 글자 예산 + 쪽수 드리프트 가드 (필수)
"$PY" "$SKILL_DIR/scripts/page_guard.py" \
  --reference reference.hwpx \
  --output result.hwpx \
  --budget-profile /tmp/reference.budget.json \
  --structure-profile /tmp/reference.structure.json \
  --no-strict-paragraph-budget \
  --skip-text-drift \
  --allow-empty-fill

# 7) 내용 완성도 가드 (필수)
"$PY" "$SKILL_DIR/scripts/content_guard.py" result.hwpx \
  --rules /tmp/content.rules.json

# 문서 전체 관점 전환/전면 재작성인 경우 원본 긴 문장 잔존율도 제한
"$PY" "$SKILL_DIR/scripts/content_guard.py" result.hwpx \
  --reference reference.hwpx \
  --rules /tmp/content.rules.json \
  --max-unchanged-ratio 0.35

# 공문서라면 날짜/시간/금액/붙임 표기도 점검
"$PY" "$SKILL_DIR/scripts/gonmun_lint.py" --hwpx result.hwpx --format text

# 8) 한컴 실열림 (필수, Windows + 한글 설치 환경)
"$PY" "$SKILL_DIR/scripts/finalize_hwpx.py" result.hwpx --hancom

# 9) PDF 렌더 육안 확인 (필수) — 기계 검사가 못 보는 것을 사람/에이전트의 눈으로 본다
#    render_check.py는 이 스킬이 아니라 프로젝트 scripts/에 있다
"$PY" scripts/render_check.py result.hwpx --reference reference.hwpx --keep-pdf /tmp/result.pdf
"$PY" -c "
import fitz, sys
d = fitz.open(sys.argv[1])
for i, page in enumerate(d):
    page.get_pixmap(dpi=140).save(sys.argv[2] + f'/page{i}.png')
print('rendered', len(d), 'pages')
" /tmp/result.pdf /tmp
#    → 생성된 png를 Read 도구로 열어 실제로 눈으로 확인한다 (셀 안 줄바꿈·글자 밀림은 여기서만 보인다)
```

`hwpx_slots.py`는 표/그림/텍스트상자를 품은 컨테이너 문단을 제외하고, 실제 편집 가능한 문단과 표 셀을 슬롯으로 노출한다. 사용자는 슬롯 키에 값만 넣으면 된다.

`edit_hwpx.py`는 `mimetype`, `content.hpf`, `header.xml`, `settings.xml`, `Preview/*`, `BinData/*`를 원본에서 그대로 복제한다. 수정 대상은 기본적으로 `Contents/section0.xml` 내부의 슬롯 텍스트뿐이다. 따라서 사용자가 기존 양식을 제공했고 텍스트/셀 채우기만 필요하다면 `build_hwpx.py`보다 `edit_hwpx.py --slot-json`을 우선한다.

패키징은 일반 ZIP 재압축을 금지한다. 원본 ZIP의 로컬 헤더와 압축 데이터를 그대로 복사하고, 변경 대상 엔트리만 교체한다. 변경하지 않은 엔트리는 CRC, compressed size, file size, flag bits, 압축 방식, 날짜, 생성 시스템, 외부/내부 속성이 원본과 같아야 한다.

### `edit_hwpx.py` 사용 규칙

```bash
# 전체 텍스트 치환
"$PY" "$SKILL_DIR/scripts/edit_hwpx.py" form.hwpx \
  -o out.hwpx \
  --replace "기존문구=새문구"

# JSON 매핑 치환
"$PY" "$SKILL_DIR/scripts/edit_hwpx.py" form.hwpx \
  -o out.hwpx \
  --replace-json values.json

# 표 셀 채우기: row,col은 0부터 시작, table 생략 시 첫 번째 표
"$PY" "$SKILL_DIR/scripts/edit_hwpx.py" form.hwpx \
  -o out.hwpx \
  --cell "0,2,1=테스트 법인"

# 본문 문단 재작성: 문장 품질을 우선하고 원본 문단 예산 이하로만 제한
"$PY" "$SKILL_DIR/scripts/edit_hwpx.py" form.hwpx \
  -o out.hwpx \
  --paragraph-json paragraphs.json

# 권장: 슬롯 키 기반 채우기
"$PY" "$SKILL_DIR/scripts/hwpx_slots.py" form.hwpx -o slots.json
"$PY" "$SKILL_DIR/scripts/edit_hwpx.py" form.hwpx \
  -o out.hwpx \
  --slot-json values.json
```

- `--replace`는 먼저 개별 `hp:t` 안에서 치환해 런 서식을 최대한 유지한다.
- 치환 대상이 여러 런에 나뉘어 있으면 문단 단위로 합치되, 첫 번째 런을 무조건 쓰지 않는다. `header.xml`의 `charPr`를 확인해 볼드/색상/밑줄 같은 강조가 적고, 해당 문단 안에서 비강조 텍스트가 가장 많이 쓰는 글자 높이에 가까운 주 런을 선택한다.
- `--cell`은 해당 `hp:tc` 안의 첫 번째 런 서식을 유지하고 텍스트만 넣는다.
- `--paragraph`/`--paragraph-json`은 실무 본문 재작성용이다. 기존 문장을 여러 런에 기계적으로 쪼개지 않고 문단의 주 텍스트 런 하나에 자연문으로 넣는다. 주 런은 글자 수만 보지 않고 `charPrIDRef`의 볼드/색상/밑줄과 문단 내 지배적 본문 높이로 고른다.
- `hh:strikeout shape="3D"` 같은 값은 일부 HWPX에서 일반 본문 charPr에도 붙어 있다. 실제 취소선 렌더링이 명확하지 않으면 단독으로 강조/배제 기준으로 쓰지 않는다.
- `--slot`/`--slot-json`은 기본 인터페이스다. 슬롯 키는 `hwpx_slots.py`가 생성한 것만 사용한다.
- `--paragraph` 대상은 직접 `hp:run/hp:t`를 가진 실제 텍스트 문단이어야 한다. 표/그림/텍스트상자를 품은 컨테이너 문단은 직접 수정하지 않는다. 컨테이너를 수정하면 내부 텍스트와 새 텍스트가 겹쳐 렌더링된다.
- 빈 입력 셀처럼 `hp:run`은 있으나 `hp:t`가 없는 경우에는 기존 런 안에 `hp:t`만 추가한다.
- `hp:t` 내부의 `hp:fwSpace`, `hp:lineBreak`, 기타 자식 컨트롤은 절대 삭제하지 않는다. 텍스트를 비울 때도 자식 태그는 유지하고 `text/tail`만 비운다.
- 텍스트를 바꾼 문단의 `hp:linesegarray`는 제거한다. 이 태그는 문단 줄 배치 캐시라서 본문 수정 뒤 보존하면 한컴에서 손상/변조 경고를 낼 수 있다.
- `hp:tbl`, `hp:tr`, `hp:tc`, `cellAddr`, `cellSpan`, `cellSz`, `cellMargin`, `borderFillIDRef`는 변경하지 않는다.

### 실무 입력 품질 규칙

본문 문단은 맞춤법과 띄어쓰기가 우선이다. 양식을 보존하려고 `정부는현장점검과공개보고...`처럼 공백을 제거하거나 문장을 중간에서 자르지 않는다.

- 본문 재작성은 `--paragraph-json`을 사용한다.
- 문단 인덱스를 고를 때 `analyze_template.py` 또는 텍스트 추출 결과에서 컨테이너 문단이 아니라 내부 실제 텍스트 문단을 고른다. 예를 들어 상단 표 전체 문단이 아니라 표 셀 안의 기관명/제목 문단을 수정한다.
- 본문은 원본 문단의 공백 제외 글자 수 이하로 짧게 다시 쓴다. 원본과 정확히 같은 글자 수로 억지 보강하지 않는다.
- 이름, 날짜, 전화번호, 직책, 금액, 짧은 표 셀 같은 필드만 정확 길이/셀 예산을 엄격 적용한다.
- 과도하게 긴 무공백 한글 문자열은 `edit_hwpx.py`의 기본 품질 가드에서 실패한다. 정상 문장이 아니라면 결과를 제출하지 않는다.
- 원본 런의 볼드/강조가 본문 새 문장 중간에 묻어 들어가면 실패다. 본문은 `--paragraph` 계열로 단일 주 런에 넣고, 제목/소제목처럼 의도된 강조만 원본 스타일을 유지한다.
- 원본보다 글자 크기가 달라 보이면 `header.xml`이 바뀐 것인지, 새 텍스트가 다른 `charPrIDRef`에 들어간 것인지 먼저 비교한다. `header.xml`이 같아도 14pt 본문 대신 12pt 괄호/각주 run을 선택하면 표시 서체가 달라진다.

### 글자 예산 가드 규칙

`page_guard.py --write-budget`는 원본 양식에서 다음 예산을 계산한다.

- 일반 문단: 직접 `hp:run/hp:t` 텍스트의 공백 제외 글자 수
- 표 셀: 셀 내부 전체 `hp:t` 텍스트의 공백 제외 글자 수와 셀 폭/글자 크기 기반 추정 수용량 중 큰 값
- 빈 입력 셀: 기존 셀 폭과 첫 런의 `charPrIDRef` 글자 크기를 이용해 보수적 수용량 산정

결과 검증 시 `--budget-profile`을 반드시 사용한다. 실무 본문 재작성 결과는 `--no-strict-paragraph-budget --skip-text-drift`를 함께 사용해 원본 글자 수 “일치”가 아니라 예산 이하와 구조 보존 여부를 본다. 표 셀과 짧은 입력 필드는 예산을 초과하면 실패한다. 셀 내부 문단은 셀 예산으로 검사하므로 빈 칸 입력이 가능하다.

### 전체 구조 fingerprint 가드 규칙

`page_guard.py --write-structure`는 원본 양식에서 다음을 저장한다.

- ZIP 패키지 파일 목록과 순서
- 각 엔트리의 압축 방식, 날짜, 생성 시스템, 버전, flag bits, 외부/내부 속성
- 바이너리/부속 파일의 SHA-256 해시
- 모든 XML 파일의 태그명, 속성, 계층, 자식 순서
- `hp:t`의 직접 텍스트와 `hp:t` 하위 컨트롤의 tail 텍스트는 입력값으로 보고 제외
- `hp:t` 내부의 `hp:fwSpace`, `hp:lineBreak` 같은 자식 컨트롤 태그/순서는 구조 fingerprint에 포함
- `hp:linesegarray`는 줄 배치 캐시로 보고 구조 fingerprint에서 제외

결과 검증 시 `--structure-profile`을 반드시 사용한다. `hp:t` 텍스트 입력과 `hp:linesegarray` 캐시 제거를 제외한 태그/속성/파일/이미지/메타 구조가 바뀌면 실패한다. 특히 `hp:t` 내부 컨트롤이 삭제되면 손상 가능성이 높으므로 실패해야 한다.

ZIP 엔트리의 `flag_bits`도 원본과 같아야 한다. Python `zipfile.writestr()`로 전체 엔트리를 다시 쓰면 `flag_bits`와 압축 바이트가 바뀔 수 있으므로 사용하지 않는다. 반드시 원시 ZIP 복사 방식으로 변경 대상 엔트리만 교체한다.

`edit_hwpx.py`는 기본적으로 입력 전 글자수 예산과 기본 문장 품질을 검사한다. `--paragraph` 값은 원본 문단 예산 이하여야 하고, `--cell` 값은 원본 셀 예산을 넘으면 안 된다. `--replace`의 새 값이 기존 자리보다 길면 쓰기 전에 실패한다.

#### `--allow-over-budget`과 셀 폭 (2026. 8. 20. 승격)

**기본은 텍스트를 줄여 예산 안에 넣는 것이다. `--allow-over-budget`은 셀 폭을 실제로 확인했을 때만 쓴다** — 이 플래그는 예산 *검사*를 끄는 것이지 셀 폭이 늘어나는 게 아니다.

셀 예산은 셀 폭과 글자 크기에서 나온 값이라, 초과분은 한글에서 **셀 안 줄바꿈**으로 나타난다. 그런데 그 줄바꿈은 스키마 검증에도, `page_guard`(쪽수·구조)에도, `render_check`(쪽수·순서)에도, 한컴 실열림에도 **전혀 걸리지 않는다** — 쪽수가 그대로면 전부 PASS다. 즉 예산 경고가 이 실패를 잡을 수 있는 **유일한 기계 신호**이고, 그것을 끄면 남는 방어선은 사람 눈뿐이다.

- 셀·짧은 필드(날짜·이름·전화번호·금액)는 예산 초과 시 **축약을 먼저 시도**한다. 예: `센터 이동 및 로봇 스포츠 챌린지` → `이동·로봇 체험`, `학교 복귀 및 귀가 지도` → `복귀·귀가 지도`
- 축약이 의미를 훼손해서 불가능하면, 넘기지 말고 **사용자에게 판단을 요청**한다 (셀 폭을 넓힐지, 문구를 바꿀지).
- 그래도 초과분을 쓰기로 했다면 반드시 ① 그 결정을 보고에 명시하고 ② PDF 렌더 이미지로 해당 셀을 눈으로 확인한 뒤 제출한다.
- 괄호쌍·단위처럼 **쪼개지면 안 되는 짧은 토큰**(`참가 (   )`의 닫는 괄호 등)은 예산이 아슬아슬하면 여유를 더 둔다.

### 내용 완성도 가드 규칙

`content_guard.py`는 문서가 열리는지와 무관하게 결과 텍스트가 작업 의도와 일치하는지 검사한다. 다음 경우에는 반드시 규칙 파일을 만들어 실행한다.

- 문서의 기관/국가/회사/브랜드를 바꾸는 경우: 이전 명칭, 이전 담당자, 이전 전화번호, 이전 정책명을 `forbid`에 넣는다.
- 양식 placeholder를 채우는 경우: `○○`, `{{name}}`, `... . .` 같은 잔여 placeholder를 금지한다.
- 새 문서 관점의 핵심어가 반드시 있어야 하는 경우: 새 기관명, 새 법인명, 새 담당 부서 등을 `require`에 넣는다.
- 여러 붙임/참고/담당자 표가 있는 문서에서는 앞부분만 바꾸지 말고 전체 텍스트 추출 결과에 대해 `content_guard.py`를 실행한다.
- **기존 문서를 베이스로 재활용/재발송하는 경우(필수)**: 베이스 문서의 고유 명칭(행사명·강사명·기관명)과 **본문에 박힌 옛 날짜**(배부일·시행일·서명일)를 전부 `forbid`에 넣는다. "문구가 회차 무관 범용"이어도 날짜는 항상 새 배부일로 갱신해야 한다 — 2026. 7. 18. 기출문제 공개 안내에서 본문 끝 "2026. 4. 7. 화동중학교장"이 그대로 남은 것을 사용자가 잡아냈다. 2026. 8. 20. 가통도 5980 발송본을 베이스로 삼아 `인순이`·`명사`·`문화예술회관`·`석식`·`2025`를 forbid에 넣어 통과시켰다.
- “내용을 싹 바꾸라”, “미국에서 작성한 것처럼 바꾸라”처럼 전면 재작성 요청이면 `--reference`와 `--max-unchanged-ratio`를 함께 사용한다. 원본의 긴 문장이 많이 남으면 구조가 정상이어도 실패다.

예시:

```json
{
  "require": ["미국노동부", "좋은 일자리"],
  "forbid": ["고용노동부", "김영훈", "최영범", "장지훈", "044-"],
  "forbid_regex": ["○○+", "\\(\\s*\\.\\s*\\.\\s*\\.\\s*\\)"]
}
```

`content_guard.py`가 실패하면 구조가 아무리 정상이어도 결과를 완료로 제출하지 않는다. 실패 목록을 보고 남은 슬롯을 추가 수정하거나, 문서 전체 재작성 범위를 넓힌 뒤 다시 빌드한다.

## 환경 (2026. 8. 20. 실측)

```bash
# 이 SKILL.md가 있는 디렉토리
SKILL_DIR="<프로젝트>/.claude/skills/hwpx"
# 또는 Claude Code가 주입하는 base directory 경로

# 인터프리터 — 반드시 시스템 Python 3.12를 절대 경로로 지정한다
PY="C:/Users/22/AppData/Local/Programs/Python/Python312/python.exe"
```

**`python` / `python3` / `py`를 그냥 쓰지 않는다.** 이 PC의 PATH에서 셋 다 `textbook_wiki/.venv`로 해석되고, 그 venv에는 **pywin32도 python-hwpx도 없다**. 즉 맨 이름으로 부르면 lxml만 쓰는 스크립트는 우연히 돌아가지만 COM 계열(`finalize_hwpx.py --hancom`, 프로젝트 `scripts/render_check.py`)과 `create_document.py`는 조용히 실패한다. 실제로 2026. 8. 20. 가정통신문 작업에서 `--hancom`이 이 이유로 한 번 죽었고 시스템 Python312로 재실행해서 통과시켰다.

| 인터프리터 | lxml | PyMuPDF·pypdf | pywin32 | python-hwpx | 용도 |
|---|---|---|---|---|---|
| `Python312\python.exe` (시스템) | O | O | O | O | **전부 여기서 실행** |
| PATH의 `python`/`python3`/`py` (textbook_wiki venv) | O | O | **X** | **X** | 쓰지 말 것 |
| `python3.exe` (Store 3.14) | 별도 site-packages | — | — | `--no-deps` 설치 필요 | 쓰지 말 것 |

`$PY`가 아닌 인터프리터로 돌렸다면 그 사실을 보고에 남긴다. 이 문서의 모든 예시는 `"$PY"`를 전제로 한다.

## 디렉토리 구조

```
.claude/skills/hwpx/
├── SKILL.md                              # 이 파일
├── scripts/
│   ├── office/
│   │   ├── unpack.py                     # HWPX → 디렉토리 (기본 XML 바이트 보존, --pretty는 검사 전용)
│   │   └── pack.py                       # 디렉토리 → HWPX
│   ├── build_hwpx.py                     # 템플릿 + XML → .hwpx 조립 (핵심)
│   ├── edit_hwpx.py                      # 원본 패키지 보존 + 텍스트/셀 최소 수정
│   ├── hwpx_slots.py                     # 편집 가능한 문단/셀 슬롯 추출 (edit_hwpx --slot-json의 입력)
│   ├── create_document.py                # 마크다운 → HWPX 초고속 경로 (python-hwpx 필요)
│   ├── analyze_template.py               # HWPX 심층 분석 (레퍼런스 기반 생성용)
│   ├── validate.py                       # HWPX 구조 검증
│   ├── fix_namespaces.py                 # 표준 네임스페이스 프리픽스/header itemCnt 보정
│   ├── finalize_hwpx.py                  # 줄 배치 캐시 제거 + 레이아웃 위험 경고
│   ├── page_guard.py                     # 레퍼런스 대비 페이지 드리프트 위험 검사
│   ├── content_guard.py                  # 원문 잔재/placeholder/필수 키워드 검사
│   ├── gonmun_lint.py                    # 공문서 날짜/시간/금액/붙임 표기 검수
│   └── text_extract.py                   # 텍스트 추출
├── templates/
│   ├── base/                             # 베이스 템플릿 (Skeleton 기반)
│   │   ├── mimetype, META-INF/*, version.xml, settings.xml, Preview/*
│   │   └── Contents/ (header.xml, section0.xml, content.hpf)
│   ├── gonmun/                           # 공문 오버레이 (header.xml, section0.xml)
│   ├── report/                           # 보고서 오버레이
│   ├── minutes/                          # 회의록 오버레이
│   └── proposal/                         # 제안서/사업개요 오버레이 (색상 헤더바, 번호 배지)
├── tests/
│   └── test_hwpx_guards.py               # page_guard·content_guard 회귀 테스트
└── references/
    ├── hwpx-format.md                    # OWPML XML 요소 레퍼런스
    └── jkf87-hwpx-skill-comparison.md    # 폴백 스킬(hwpx-fallback)과의 기능 대조
```

`templates/base/`는 **11개 파일 전부**(mimetype · version.xml · settings.xml · META-INF 3종 · Contents 3종 · Preview 2종)를 갖고 있어야 `build_hwpx.py` 신규 생성이 동작한다. 2026. 8. 1.까지 `Contents/`·`META-INF/`·`Preview/`가 통째로 빠져 있어 신규 생성이 실패했고, python-hwpx 빈 문서 스켈레톤으로 보수했다(validate + COM 실열림 검증 완료). 다른 프로젝트로 이식할 때 이 11개를 먼저 확인할 것 — 전체 이식 절차는 프로젝트의 `docs/신규생성-이식-가이드.md`에 있다. 같은 11개 요건은 **산출물에도 적용된다** — `validate.py`의 `REQUIRED_FILES`가 2026. 8. 20.부터 11개 전부를 검사한다(그 전에는 4개만 봐서 9파일 패키지 5건이 그대로 나갔다).

---

## 워크플로우 1: XML-first 문서 생성 (보조 워크플로우, 레퍼런스 파일이 없을 때만)

### 흐름

1. **템플릿 선택** (base/gonmun/report/minutes/proposal)
2. **section0.xml 작성** (본문 내용)
3. **(선택) header.xml 수정** (새 스타일 추가 필요 시)
4. **build_hwpx.py로 빌드**
5. **validate.py로 검증**

> 원칙: 사용자가 레퍼런스 HWPX를 제공한 경우에는 이 워크플로우 대신 상단의 "기본 동작 모드(레퍼런스 복원 우선)"를 사용한다.

#### 신규 생성 경로 3가지 (2026. 8. 1. 전부 실행 검증)

| 경로 | 방법 | 언제 |
|---|---|---|
| **A (표준)** | `build_hwpx.py --template <유형> --section my_section0.xml` | 기본. 스킬 템플릿이 있는 환경 |
| **B (기증자)** | 유효한 HWPX 하나를 `office/unpack.py`로 풀어 `header.xml`·`section0.xml`만 교체 → `office/pack.py` | 스킬 `templates/`가 없는 환경으로 이식했을 때. 가장 확실 |
| **C (마크다운)** | `create_document.py --input content.md --output result.hwpx` | 초안·간단 문서. 서식 제어 제한적, python-hwpx 필요 |

경로 B에서는 나머지 9개 파일을 손대지 않는다. `--pretty`로 푼 디렉토리는 pack 입력으로 쓰지 않고, 일반 ZIP 명령으로 재압축하지 않는다. 상세 절차와 검증 기록은 프로젝트 `docs/신규생성-이식-가이드.md`.

### 기본 사용법

```bash
# 빈 문서 (base 템플릿)
"$PY" "$SKILL_DIR/scripts/build_hwpx.py" --output result.hwpx

# 템플릿 사용
"$PY" "$SKILL_DIR/scripts/build_hwpx.py" --template gonmun --output result.hwpx

# 커스텀 section0.xml 오버라이드
"$PY" "$SKILL_DIR/scripts/build_hwpx.py" --template gonmun --section my_section0.xml --output result.hwpx

# header도 오버라이드
"$PY" "$SKILL_DIR/scripts/build_hwpx.py" --header my_header.xml --section my_section0.xml --output result.hwpx

# 메타데이터 설정
"$PY" "$SKILL_DIR/scripts/build_hwpx.py" --template report --section my.xml \
  --title "제목" --creator "작성자" --output result.hwpx
```

### 실전 패턴: section0.xml을 인라인 작성 → 빌드

```bash
# 1. section0.xml을 임시파일로 작성
SECTION=$(mktemp /tmp/section0_XXXX.xml)
cat > "$SECTION" << 'XMLEOF'
<?xml version='1.0' encoding='UTF-8'?>
<hs:sec xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph"
        xmlns:hs="http://www.hancom.co.kr/hwpml/2011/section">
  <!-- secPr 포함 첫 문단 (base/section0.xml에서 복사) -->
  <!-- ... -->
  <hp:p id="1000000002" paraPrIDRef="0" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0">
    <hp:run charPrIDRef="0">
      <hp:t>본문 내용</hp:t>
    </hp:run>
  </hp:p>
</hs:sec>
XMLEOF

# 2. 빌드
"$PY" "$SKILL_DIR/scripts/build_hwpx.py" --section "$SECTION" --output result.hwpx

# 3. 정리
rm -f "$SECTION"
```

---

## section0.xml 작성 가이드

### 필수 구조

section0.xml의 첫 문단(`<hp:p>`)의 첫 런(`<hp:run>`)에 반드시 `<hp:secPr>`과 `<hp:colPr>` 포함:

```xml
<hp:p id="1000000001" paraPrIDRef="0" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0">
  <hp:run charPrIDRef="0">
    <hp:secPr ...>
      <!-- 페이지 크기, 여백, 각주/미주 설정 등 -->
    </hp:secPr>
    <hp:ctrl>
      <hp:colPr id="" type="NEWSPAPER" layout="LEFT" colCount="1" sameSz="1" sameGap="0"/>
    </hp:ctrl>
  </hp:run>
  <hp:run charPrIDRef="0"><hp:t/></hp:run>
</hp:p>
```

**Tip**: `templates/base/Contents/section0.xml` 의 첫 문단을 그대로 복사하면 된다.

### 문단

```xml
<hp:p id="고유ID" paraPrIDRef="문단스타일ID" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0">
  <hp:run charPrIDRef="글자스타일ID">
    <hp:t>텍스트 내용</hp:t>
  </hp:run>
</hp:p>
```

### 빈 줄

```xml
<hp:p id="고유ID" paraPrIDRef="0" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0">
  <hp:run charPrIDRef="0"><hp:t/></hp:run>
</hp:p>
```

### 서식 혼합 런 (한 문단에 여러 스타일)

```xml
<hp:p id="고유ID" paraPrIDRef="0" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0">
  <hp:run charPrIDRef="0"><hp:t>일반 텍스트 </hp:t></hp:run>
  <hp:run charPrIDRef="7"><hp:t>볼드 텍스트</hp:t></hp:run>
  <hp:run charPrIDRef="0"><hp:t> 다시 일반</hp:t></hp:run>
</hp:p>
```

### 표 작성법

```xml
<hp:p id="고유ID" paraPrIDRef="0" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0">
  <hp:run charPrIDRef="0">
    <hp:tbl id="고유ID" zOrder="0" numberingType="TABLE" textWrap="TOP_AND_BOTTOM"
            textFlow="BOTH_SIDES" lock="0" dropcapstyle="None" pageBreak="CELL"
            repeatHeader="0" rowCnt="행수" colCnt="열수" cellSpacing="0"
            borderFillIDRef="3" noAdjust="0">
      <hp:sz width="42520" widthRelTo="ABSOLUTE" height="전체높이" heightRelTo="ABSOLUTE" protect="0"/>
      <hp:pos treatAsChar="1" affectLSpacing="0" flowWithText="1" allowOverlap="0"
              holdAnchorAndSO="0" vertRelTo="PARA" horzRelTo="COLUMN" vertAlign="TOP"
              horzAlign="LEFT" vertOffset="0" horzOffset="0"/>
      <hp:outMargin left="0" right="0" top="0" bottom="0"/>
      <hp:inMargin left="0" right="0" top="0" bottom="0"/>
      <hp:tr>
        <hp:tc name="" header="0" hasMargin="0" protect="0" editable="0" dirty="1" borderFillIDRef="4">
          <hp:subList id="" textDirection="HORIZONTAL" lineWrap="BREAK" vertAlign="CENTER"
                     linkListIDRef="0" linkListNextIDRef="0" textWidth="0" textHeight="0"
                     hasTextRef="0" hasNumRef="0">
            <hp:p paraPrIDRef="21" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0" id="고유ID">
              <hp:run charPrIDRef="9"><hp:t>헤더 셀</hp:t></hp:run>
            </hp:p>
          </hp:subList>
          <hp:cellAddr colAddr="0" rowAddr="0"/>
          <hp:cellSpan colSpan="1" rowSpan="1"/>
          <hp:cellSz width="열너비" height="행높이"/>
          <hp:cellMargin left="0" right="0" top="0" bottom="0"/>
        </hp:tc>
        <!-- 나머지 셀... -->
      </hp:tr>
    </hp:tbl>
  </hp:run>
</hp:p>
```

### 표 크기 계산

- **A4 본문폭**: 42520 HWPUNIT = 59528(용지) - 8504×2(좌우여백)
- **열 너비 합 = 본문폭** (42520)
- 예: 3열 균등 → 14173 + 14173 + 14174 = 42520
- 예: 2열 (라벨:내용 = 1:4) → 8504 + 34016 = 42520
- **행 높이**: 셀당 보통 2400~3600 HWPUNIT

### ID 규칙

- 문단 id: `1000000001`부터 순차 증가
- 표 id: `1000000099` 등 별도 범위 사용 권장
- 모든 id는 문서 내 고유해야 함

---

## header.xml 수정 가이드

### 커스텀 스타일 추가 방법

1. `templates/base/Contents/header.xml` 복사
2. 필요한 charPr/paraPr/borderFill 추가
3. 각 그룹의 `itemCnt` 속성 업데이트

### charPr 추가 예시 (볼드 14pt)

```xml
<hh:charPr id="8" height="1400" textColor="#000000" shadeColor="none"
           useFontSpace="0" useKerning="0" symMark="NONE" borderFillIDRef="2">
  <hh:fontRef hangul="1" latin="1" hanja="1" japanese="1" other="1" symbol="1" user="1"/>
  <hh:ratio hangul="100" latin="100" hanja="100" japanese="100" other="100" symbol="100" user="100"/>
  <hh:spacing hangul="0" latin="0" hanja="0" japanese="0" other="0" symbol="0" user="0"/>
  <hh:relSz hangul="100" latin="100" hanja="100" japanese="100" other="100" symbol="100" user="100"/>
  <hh:offset hangul="0" latin="0" hanja="0" japanese="0" other="0" symbol="0" user="0"/>
  <hh:bold/>
  <hh:underline type="NONE" shape="SOLID" color="#000000"/>
  <hh:strikeout shape="NONE" color="#000000"/>
  <hh:outline type="NONE"/>
  <hh:shadow type="NONE" color="#C0C0C0" offsetX="10" offsetY="10"/>
</hh:charPr>
```

### 폰트 참조 체계

- `fontRef` 값은 `fontfaces`에 정의된 font id
- `hangul="0"` → 함초롬돋움 (고딕)
- `hangul="1"` → 함초롬바탕 (명조)
- 7개 언어 모두 동일하게 설정

### paraPr 추가 시 주의

- 반드시 `hp:switch` 구조 포함 (`hp:case` + `hp:default`)
- `hp:case`와 `hp:default`의 값은 보통 동일 (또는 default가 2배)
- `borderFillIDRef="2"` 유지

---

## 템플릿별 스타일 ID 맵

### base (기본)

| ID | 유형 | 설명 |
|----|------|------|
| charPr 0 | 글자 | 10pt 함초롬바탕, 기본 |
| charPr 1 | 글자 | 10pt 함초롬돋움 |
| charPr 2~6 | 글자 | Skeleton 기본 스타일 |
| paraPr 0 | 문단 | JUSTIFY, 160% 줄간격 |
| paraPr 1~19 | 문단 | Skeleton 기본 (개요, 각주 등) |
| borderFill 1 | 테두리 | 없음 (페이지 보더) |
| borderFill 2 | 테두리 | 없음 + 투명배경 (참조용) |

### gonmun (공문) — base + 추가

| ID | 유형 | 설명 |
|----|------|------|
| charPr 7 | 글자 | 22pt 볼드 함초롬바탕 (기관명/제목) |
| charPr 8 | 글자 | 16pt 볼드 함초롬바탕 (서명자) |
| charPr 9 | 글자 | 8pt 함초롬바탕 (하단 연락처) |
| charPr 10 | 글자 | 10pt 볼드 함초롬바탕 (표 헤더) |
| paraPr 20 | 문단 | CENTER, 160% 줄간격 |
| paraPr 21 | 문단 | CENTER, 130% (표 셀) |
| paraPr 22 | 문단 | JUSTIFY, 130% (표 셀) |
| borderFill 3 | 테두리 | SOLID 0.12mm 4면 |
| borderFill 4 | 테두리 | SOLID 0.12mm + #D6DCE4 배경 |

### report (보고서) — base + 추가

| ID | 유형 | 설명 |
|----|------|------|
| charPr 7 | 글자 | 20pt 볼드 (문서 제목) |
| charPr 8 | 글자 | 14pt 볼드 (소제목) |
| charPr 9 | 글자 | 10pt 볼드 (표 헤더) |
| charPr 10 | 글자 | 10pt 볼드+밑줄 (강조 텍스트) |
| charPr 11 | 글자 | 9pt 함초롬바탕 (소형/각주) |
| charPr 12 | 글자 | 16pt 볼드 함초롬바탕 (1줄 제목) |
| charPr 13 | 글자 | 12pt 볼드 함초롬돋움 (섹션 헤더) |
| paraPr 20~22 | 문단 | CENTER/JUSTIFY 변형 |
| paraPr 23 | 문단 | RIGHT 정렬, 160% 줄간격 |
| paraPr 24 | 문단 | JUSTIFY, left 600 (□ 체크항목 들여쓰기) |
| paraPr 25 | 문단 | JUSTIFY, left 1200 (하위항목 ①②③ 들여쓰기) |
| paraPr 26 | 문단 | JUSTIFY, left 1800 (깊은 하위항목 - 들여쓰기) |
| paraPr 27 | 문단 | LEFT, 상하단 테두리선 (섹션 헤더용), prev 400 |
| borderFill 3 | 테두리 | SOLID 0.12mm 4면 |
| borderFill 4 | 테두리 | SOLID 0.12mm + #DAEEF3 배경 |
| borderFill 5 | 테두리 | 상단 0.4mm 굵은선 + 하단 0.12mm 얇은선 (섹션 헤더) |

**들여쓰기 규칙**: 공백 문자가 아닌 반드시 paraPr의 left margin 사용. □ 항목은 paraPr 24, 하위 ①②③ 는 paraPr 25, 깊은 - 항목은 paraPr 26.

**섹션 헤더 규칙**: paraPr 27 + charPr 13 조합. 문단 테두리(borderFillIDRef="5")로 상단 굵은선 + 하단 얇은선 자동 표시.

### minutes (회의록) — base + 추가

| ID | 유형 | 설명 |
|----|------|------|
| charPr 7 | 글자 | 18pt 볼드 (제목) |
| charPr 8 | 글자 | 12pt 볼드 (섹션 라벨) |
| charPr 9 | 글자 | 10pt 볼드 (표 헤더) |
| paraPr 20~22 | 문단 | CENTER/JUSTIFY 변형 |
| borderFill 3 | 테두리 | SOLID 0.12mm 4면 |
| borderFill 4 | 테두리 | SOLID 0.12mm + #E2EFDA 배경 |

### proposal (제안서/사업개요) — base + 추가

시각적 구분이 필요한 공식 문서용. 색상 배경 헤더바와 번호 배지를 표(table) 기반 레이아웃으로 구현.

| ID | 유형 | 설명 |
|----|------|------|
| charPr 7 | 글자 | 20pt 볼드 함초롬바탕 (문서 제목) |
| charPr 8 | 글자 | 14pt 볼드 함초롬바탕 (소제목) |
| charPr 9 | 글자 | 10pt 볼드 함초롬바탕 (표 헤더) |
| charPr 10 | 글자 | 14pt 볼드 흰색 함초롬돋움 (대항목 번호, 녹색 배경) |
| charPr 11 | 글자 | 11pt 볼드 흰색 함초롬돋움 (소항목 번호, 파란 배경) |
| paraPr 20 | 문단 | CENTER, 160% 줄간격 |
| paraPr 21 | 문단 | CENTER, 130% (표 셀) |
| paraPr 22 | 문단 | JUSTIFY, 130% (표 셀) |
| borderFill 3 | 테두리 | SOLID 0.12mm 4면 |
| borderFill 4 | 테두리 | SOLID 0.12mm + #DAEEF3 배경 |
| borderFill 5 | 테두리 | 올리브녹색 배경 #7B8B3D (대항목 번호 셀) |
| borderFill 6 | 테두리 | 연한 회색 배경 #F2F2F2 + 회색 테두리 (대항목 제목 셀) |
| borderFill 7 | 테두리 | 파란색 배경 #4472C4 (소항목 번호 배지) |
| borderFill 8 | 테두리 | 하단 테두리만 #D0D0D0 (소항목 제목 영역) |

#### proposal 레이아웃 패턴

**대항목 헤더** (2셀 표: 번호 + 제목):
```xml
<!-- borderFillIDRef="5" + charPrIDRef="10" → 녹색배경 흰색 로마숫자 -->
<!-- borderFillIDRef="6" + charPrIDRef="8"  → 회색배경 검정 볼드 제목 -->
```

**소항목 헤더** (2셀 표: 번호배지 + 제목):
```xml
<!-- borderFillIDRef="7" + charPrIDRef="11" → 파란배경 흰색 아라비아숫자 -->
<!-- borderFillIDRef="8" + charPrIDRef="8"  → 하단선만 검정 볼드 제목 -->
```

---

## 워크플로우 2: 기존 문서 편집 (unpack → Edit → pack)

```bash
# 1. HWPX → 디렉토리 (기본값은 XML 바이트 보존)
"$PY" "$SKILL_DIR/scripts/office/unpack.py" document.hwpx ./unpacked/

# 2. XML 직접 편집 (Claude가 Read/Edit 도구로)
#    본문: ./unpacked/Contents/section0.xml
#    스타일: ./unpacked/Contents/header.xml

# 3. 다시 HWPX로 패키징
"$PY" "$SKILL_DIR/scripts/office/pack.py" ./unpacked/ edited.hwpx

# 4. 검증
"$PY" "$SKILL_DIR/scripts/validate.py" edited.hwpx
```

`unpack.py --pretty`는 사람이 XML을 읽기 좋게 확인할 때만 사용한다. HWPX의 `hp:t`는 텍스트와 `hp:fwSpace`, `hp:lineBreak` 같은 자식 컨트롤이 섞인 mixed content를 가질 수 있고, pretty-print가 삽입한 줄바꿈/공백이 한컴에서 실제 텍스트처럼 렌더링될 수 있다. 따라서 `--pretty`로 푼 디렉토리를 다시 `pack.py` 입력으로 사용하지 않는다.

---

## 워크플로우 3: 읽기/텍스트 추출

```bash
# 순수 텍스트
"$PY" "$SKILL_DIR/scripts/text_extract.py" document.hwpx

# 테이블 포함
"$PY" "$SKILL_DIR/scripts/text_extract.py" document.hwpx --include-tables

# 마크다운 형식
"$PY" "$SKILL_DIR/scripts/text_extract.py" document.hwpx --format markdown
```

### Python API

```python
from hwpx import TextExtractor
with TextExtractor("document.hwpx") as ext:
    text = ext.extract_text(include_nested=True, object_behavior="nested")
    print(text)
```

---

## 워크플로우 4: 검증

```bash
"$PY" "$SKILL_DIR/scripts/validate.py" document.hwpx
```

검증 항목: ZIP 유효성, 필수 파일 존재, mimetype 내용/위치/압축방식, XML well-formedness

---

## 워크플로우 5: 레퍼런스 기반 문서 생성 (첨부 HWPX가 있을 때 기본 적용)

사용자가 제공한 HWPX 파일을 분석하여 동일한 레이아웃의 문서를 생성하는 워크플로우.
이 스킬에서는 첨부 레퍼런스가 존재하면 본 워크플로우를 기본으로 사용한다.

### 흐름

1. **분석** — `analyze_template.py`로 레퍼런스 문서 심층 분석
2. **header.xml 추출** — 레퍼런스의 스타일 정의를 그대로 사용
3. **section0.xml 작성** — 분석 결과의 구조를 따라 새 내용으로 작성
4. **빌드** — 추출한 header.xml + 새 section0.xml로 빌드
5. **검증** — `validate.py`
6. **쪽수 가드** — `page_guard.py` (실패 시 재수정)

### 사용법

```bash
# 1. 심층 분석 (구조 청사진 출력)
"$PY" "$SKILL_DIR/scripts/analyze_template.py" reference.hwpx

# 2. header.xml과 section0.xml을 추출하여 참고용으로 보관
"$PY" "$SKILL_DIR/scripts/analyze_template.py" reference.hwpx \
  --extract-header /tmp/ref_header.xml \
  --extract-section /tmp/ref_section.xml

# 3. 분석 결과를 보고 새 section0.xml 작성
#    - 동일한 charPrIDRef, paraPrIDRef 사용
#    - 동일한 테이블 구조 (열 수, 열 너비, 행 수, rowSpan/colSpan)
#    - 동일한 borderFillIDRef, cellMargin

# 4. 추출한 header.xml + 새 section0.xml로 빌드
"$PY" "$SKILL_DIR/scripts/build_hwpx.py" \
  --header /tmp/ref_header.xml \
  --section /tmp/new_section0.xml \
  --output result.hwpx

# 5. 검증
"$PY" "$SKILL_DIR/scripts/validate.py" result.hwpx

# 6. 쪽수 드리프트 가드 (필수)
"$PY" "$SKILL_DIR/scripts/page_guard.py" \
  --reference reference.hwpx \
  --output result.hwpx
```

### 분석 출력 항목

| 항목 | 설명 |
|------|------|
| 폰트 정의 | hangul/latin 폰트 매핑 |
| borderFill | 테두리 타입/두께 + 배경색 (각 면별 상세) |
| charPr | 글꼴 크기(pt), 폰트명, 색상, 볼드/이탤릭/밑줄/취소선, fontRef |
| paraPr | 정렬, 줄간격, 여백(left/right/prev/next/intent), heading, borderFillIDRef |
| 문서 구조 | 페이지 크기, 여백, 페이지 테두리, 본문폭 |
| 본문 상세 | 모든 문단의 id/paraPr/charPr + 텍스트 내용 |
| 표 상세 | 행×열, 열너비 배열, 셀별 span/margin/borderFill/vertAlign + 내용 |

### 핵심 원칙

- **charPrIDRef/paraPrIDRef를 그대로 사용**: 추출한 header.xml의 스타일 ID를 변경하지 말 것
- **열 너비 합계 = 본문폭**: 분석 결과의 열너비 배열을 그대로 복제
- **rowSpan/colSpan 패턴 유지**: 분석된 셀 병합 구조를 정확히 재현
- **cellMargin 보존**: 분석된 셀 여백 값을 동일하게 적용
- **페이지 증가 금지**: 사용자 명시 승인 없이 결과 쪽수를 늘리지 말 것
- **치환 우선 편집**: 새 문단/표 추가보다 기존 텍스트 노드 치환을 우선할 것

---

## 스크립트 요약

| 스크립트 | 용도 |
|----------|------|
| `scripts/build_hwpx.py` | **핵심** — 템플릿 + XML → HWPX 조립 |
| `scripts/edit_hwpx.py` | 원본 패키지 보존 + 슬롯/셀 최소 수정 (**양식이 있으면 1순위**) |
| `scripts/hwpx_slots.py` | 편집 가능한 문단/셀 슬롯 추출 → `edit_hwpx.py --slot-json` 입력 |
| `scripts/create_document.py` | 마크다운 → HWPX 초고속 경로 (python-hwpx 필요, 서식 제어 제한적) |
| `scripts/analyze_template.py` | HWPX 심층 분석 (레퍼런스 기반 생성의 청사진) |
| `scripts/office/unpack.py` | HWPX → 디렉토리 (기본 XML 바이트 보존, `--pretty`는 검사 전용) |
| `scripts/office/pack.py` | 디렉토리 → HWPX (mimetype first) |
| `scripts/validate.py` | HWPX 파일 구조 검증 |
| `scripts/fix_namespaces.py` | 표준 네임스페이스 프리픽스와 header itemCnt 보정 |
| `scripts/finalize_hwpx.py` | 줄 배치 캐시 제거, 레이아웃 위험 경고, Windows Hancom 열림 검사 |
| `scripts/page_guard.py` | 레퍼런스 대비 페이지 드리프트 위험 검사 (필수 게이트) |
| `scripts/content_guard.py` | 원문 잔재, placeholder, 필수 키워드 누락 검사 |
| `scripts/gonmun_lint.py` | 공문서 날짜/시간/금액/붙임 표기 검수 |
| `scripts/text_extract.py` | HWPX 텍스트 추출 (kordoc MCP 불가 시 읽기 폴백) |
| (프로젝트) `scripts/render_check.py` | **스킬 밖** — COM 쪽수 대조 + PDF 내보내기로 렌더링 붕괴 검사, `--keep-pdf`로 육안 확인용 PDF 보존 |

## 단위 변환

| 값 | HWPUNIT | 의미 |
|----|---------|------|
| 1pt | 100 | 기본 단위 |
| 10pt | 1000 | 기본 글자크기 |
| 1mm | 283.5 | 밀리미터 |
| 1cm | 2835 | 센티미터 |
| A4 폭 | 59528 | 210mm |
| A4 높이 | 84186 | 297mm |
| 좌우여백 | 8504 | 30mm |
| 본문폭 | 42520 | 150mm (A4-좌우여백) |

## 실패 이력 (실제로 일어난 것만)

이 스킬의 규칙은 예방적 상상이 아니라 **실제 사고**에서 나왔다. 새 규칙을 추가할 때도 같은 기준을 지킨다 — 실패 2회가 규칙 1개.

**이 표가 근거의 집결지다.** 프로젝트 CLAUDE.md는 규칙 한 줄만 두고 "근거: SKILL.md 「실패 이력」 <날짜>"로 이 표를 가리킨다. 새 실패를 겪으면 규칙은 CLAUDE.md에, 무슨 일이 있었는지는 여기에 적는다.

| 날짜 | 무엇이 뚫렸나 | 왜 기계 검사가 못 잡았나 | 지금의 방어선 |
|---|---|---|---|
| 2026. 7. 7. | 재활용 문서에 직전 행사(사람책 도서관) 명칭이 예산·기대효과에 잔존 | 스키마·구조는 정상 | `content_guard` forbid에 베이스의 고유 명칭 |
| 2026. 7. 13.·7. 15. | finalize 이전에 뜬 `--write-budget/--write-structure` 프로파일이 자기 자신을 FAIL시킴 (2회 재발) | 프로파일이 낡은 패키징 기준 | 프로파일은 **3단계 finalize 완료 후** 결과물에서만 생성 |
| 2026. 7. 17. | `.hwp`→hwpx 변환본(pyhwp)에서 세로쓰기 캡션 역순·표 앵커 붕괴 | 텍스트 계층 검증 7겹이 **전부 통과** | 편집 베이스 변환은 한글 COM 네이티브 저장 1순위 + `render_check.py` 필수 |
| 2026. 7. 18. | 재발송 가통 본문 끝 날짜가 `2026. 4. 7.`(1학기)로 잔존 | 본문 텍스트 검사엔 걸릴 이유가 없음(형식은 정상) | 재사용 시 옛 날짜를 forbid에 명시 |
| 2026. 7. 18. | COM 실열림 검사 때마다 보안 승인 대화상자가 떠 사용자가 클릭 중이었음 | 에이전트는 화면을 못 봄 → "미발생"으로 오판 | `FilePathCheckerModule` 레지스트리 등록(무클릭 PASS) |
| 2026. 7. 18.(2건) | 배부일 셀 예산 1자 초과를 "구조적 한계"라며 그대로 제출 | 예산 경고를 무시 처리 | ↓ 아래 항목으로 승격 |
| **2026. 8. 20. (v2)** | **표 셀 글자가 셀 폭을 넘겨 렌더링에서 줄바꿈**(`불참 (` 뒤 닫는 괄호가 다음 줄로) | validate·page_guard·content_guard·gonmun_lint·COM 실열림·render_check **전부 PASS**. 예산 경고는 있었으나 `--allow-over-budget`으로 넘김 | 축약이 기본, `--allow-over-budget`은 폭 확인 시에만 + **PDF 렌더 이미지 육안 확인** |
| **2026. 8. 20. (v3)** | 셀 폭 초과를 **"글자를 줄여서" 고치는 쪽으로 처리해 내용이 훼손**됐다. 일정표(헤더 1 + 데이터 4행)에 활동 5개를 넣으려다 2건이 뭉개짐 — 「센터 이동 및 로봇 스포츠 챌린지」 → 「이동·로봇 체험」, 「학교 복귀 및 귀가 지도」 → 「복귀·귀가 지도」 | 폭 초과에는 ① 축약 ② 열 폭 확보 ③ 행 추가 세 선택지가 있는데, 예산·구조 검사가 ②③만 경고하므로 **검사를 피하는 유일한 길이 ①**이 된다. 검사는 "행이 모자라다"를 모른다 | **행 수는 내용에 맞춘다** — 축약은 마지막 수단이다. 행 추가는 「의도된 구조 변경 경로」로 승인·검증하면 되는 정상 경로다(사용자는 데이터 4행 → 5행으로 해결). 행을 늘릴 때 행 높이도 함께 확보 |
| **2026. 8. 20. (최종)** | 에이전트가 만든 재패키징본보다 **사용자가 한글에서 직접 고쳐 저장한 최종본**이 품질이 높았음 | 기계 검사로는 잡을 수 없는 종류의 차이(네이티브 저장 = Preview·container.rdf 정상) | 사람 최종본을 `knowledge/templates/`로 **승격**해 다음 작업의 베이스로 삼는다 (`가정통신문-회신형`) |
| **2026. 8. 20. (사후 대조)** | 재패키징본이 **11개 최소 패키지에 못 미치는 9파일**이었다 — `Preview/PrvImage.png`·`Preview/PrvText.txt`·`META-INF/container.rdf` 누락. `output/` 26건을 훑으니 **같은 누락이 5건**(전부 가정통신문 재패키징 경로), 그중 3건은 4.5점으로 동의까지 받고 지나갔다 | `validate.py`가 4개 파일만 검사하고 있었다. **한글은 9파일도 그냥 열기 때문에 COM 실열림·render_check도 통과한다** — 파이프라인 전체에 이 결함을 잡는 지점이 없었다 | `validate.py`의 `REQUIRED_FILES`를 **11개로 확장**(2026. 8. 20. 반영). 누락이 뜨면 **한컴에서 열어 「다른 이름으로 저장」**하면 네이티브가 전부 생성한다 — 이게 가장 확실한 복구 경로다 |

## 알려진 한계 (재발견·재제안 금지)

- **`content.hpf` 메타데이터는 갱신되지 않는다.** `edit_hwpx.py --slot-json`은 `section0.xml`의 슬롯 텍스트만 바꾸므로, 한글 "문서 속성"에는 템플릿이 유래한 옛 문서의 제목·작성일이 남는다. 2026. 7. 18. 사용자 확정: **갱신 불필요**("메타데이터는 난 못봐"). Validator 단계 추가를 다시 제안하지 않는다. 중요한 것은 본문에 **보이는** 잔재뿐이다.
- **빈 셀 자동 검사는 만들지 않는다.** 2026. 7. 15. 제안 → 사용자 거절. 표의 빈 셀은 병합 자리·의도적 공란인 경우가 많아 소음이 된다. 발견하면 검토 요청에 한 줄로만 언급한다.
- **표의 행·열 삭제는 에이전트가 하지 않는다.** 미응시 학년 등으로 행·열이 통째로 비는 경우, 사용자는 삭제된 표를 선호하지만 **직접 하겠다**고 두 번 확정했다(2026. 7. 18.) — 구조 변경은 재생성 경로라 비용 대비 이득이 없다는 판단. 에이전트는 선례대로 라벨링("정상수업" 등)해 두고 "필요하면 직접 지워달라"고 한 줄 안내만 한다.
- **사용자가 안 알려준 값은 결함이 아니다.** 관련번호처럼 제공되지 않은 정보를 placeholder로 남겨 `content_guard`/`page_guard`가 FAIL해도, 지어내지 않은 것이 정답이다. 사과하지 말고 "예상된 정상 상태"로만 담백하게 보고한다.
- **파일이 한글에서 열려 있으면 덮어쓰기가 실패한다** ("Device or resource busy"). 사용자가 검토하려고 열어둔 경우가 흔하므로, 쓰기 실패 시 이 가능성부터 확인한다.
- **Bash heredoc은 백슬래시를 잃는다.** 이 환경에서 `<<'EOF'` 인용 heredoc으로도 `\\[`가 `\[`로 줄어 JSON이 깨진다 (이 줄을 쓸 때도 실제로 한 번 깨졌다). `content_guard` 규칙 JSON처럼 정규식 이스케이프가 있는 파일은 **Write 도구로** 만든다.

## Critical Rules

1. **HWPX만 지원 / HWP 작성 거부**: `.hwp`(바이너리) 파일 작성, 생성, 저장, 직접 편집, 채우기 요청은 거부한다. 사용자가 명시적으로 HWPX 대체 산출물을 허용한 경우에만 `.hwpx`로 작업한다. 사용자가 `.hwp` 파일을 제공하면 **한글 오피스에서 `.hwpx`로 다시 저장**하도록 안내할 것. (파일 → 다른 이름으로 저장 → 파일 형식: HWPX)
2. **secPr 필수**: section0.xml 첫 문단의 첫 run에 반드시 secPr + colPr 포함
3. **mimetype 순서**: HWPX 패키징 시 mimetype은 첫 번째 ZIP 엔트리, ZIP_STORED
4. **네임스페이스 보존**: XML 편집 시 `hp:`, `hs:`, `hh:`, `hc:` 접두사 유지
5. **itemCnt 정합성**: header.xml의 charProperties/paraProperties/borderFills itemCnt가 실제 자식 수와 일치
6. **ID 참조 정합성**: section0.xml의 charPrIDRef/paraPrIDRef가 header.xml 정의와 일치
7. **인터프리터 고정**: 맨 `python`/`python3`가 아니라 시스템 Python312 절대 경로(`$PY`)로 실행한다. PATH의 것은 pywin32·python-hwpx가 없어 COM 검사가 조용히 죽는다 (「환경」 절)
8. **검증**: 생성 후 반드시 `validate.py`로 무결성 확인
9. **레퍼런스**: 상세 XML 구조는 `$SKILL_DIR/references/hwpx-format.md` 참조
10. **build_hwpx.py 우선**: 새 문서 생성은 build_hwpx.py 사용 (python-hwpx API 직접 호출 지양)
11. **빈 줄**: `<hp:t/>` 사용 (self-closing tag)
12. **레퍼런스 우선 강제**: 사용자가 HWPX를 첨부하면 반드시 `analyze_template.py` + 추출 XML 기반으로 복원/재작성할 것
13. **examples 폴더 미사용**: 작업 중 `.claude/skills/hwpx/examples/*` 파일은 읽기/참조/복사에 사용하지 말 것 (해당 폴더는 현재 없음. 프로젝트의 knowledge/examples/와는 무관 — 그쪽은 CLAUDE.md에 따라 검색해 사용한다)
14. **쪽수 동일 필수**: 레퍼런스 기반 작업에서는 최종 결과의 쪽수를 레퍼런스와 동일하게 유지할 것
15. **무단 페이지 증가 금지**: 사용자 명시 요청/승인 없이 쪽수 증가를 유발하는 구조 변경 금지
16. **구조 변경 제한**: 사용자 요청이 없는 한 문단/표의 추가·삭제·분할·병합 금지 (치환 중심 편집)
17. **page_guard 필수 통과**: `validate.py`와 별개로 `page_guard.py`를 반드시 통과해야 완료 처리
18. **셀 예산은 축약이 기본**: 표 셀·짧은 필드가 예산을 넘으면 문구를 줄이거나 사용자에게 묻는다. `--allow-over-budget`은 셀 폭을 실제로 확인했을 때만 (2026. 8. 20. 렌더링 붕괴)
19. **눈으로 볼 것**: 예산을 넘겨 넣었다면 기계 검사 전건 PASS도 완료가 아니다. PDF 렌더 이미지로 그 셀을 확인하고, 마지막에 항상 **"발송 전 한글로 열어 확인해주세요"**를 안내한다
