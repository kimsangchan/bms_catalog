# WORKLOG — solution-planning

세션/에이전트 간 핸드오프 로그. **"다음 할 일"은 여기 쓰지 않는다 → `NEXT.md`.**
긴 로그는 붙이지 말고 결과만 요약한다.

## Current State

- Status: doing
- Focus: 카탈로그 축 개편(설비 ↔ 제조사) + JCI 오브젝트 취입 — 다음은 판 분리 판정(NEXT.md)
- Last updated: 2026-08-14
- 규모: 모델 **140건**(별칭 10 포함) · 판 **84개** · 오브젝트 **30,485점**
  (평면 24,423 + 인터페이스 6,062) · 정격 사양 **71모델** · `validate.py` 오류 0 ·
  테스트 85건 통과 · 계열 10/19

### 오래 유지되는 사실 (구조 메모)

- **포인트는 모델이 아니라 인터페이스에 속한다** (D-016). 모델 = 제품, 인터페이스 =
  그 제품이 내보내는 목록의 판(계통·펌웨어·개정). 한 문서가 여러 제품을 덮으면 주
  제품에만 붙이고 `appliesTo` 로 밝힌다. 사전은 `data/point-schema.json`(v2),
  게이트는 `validate.check_interfaces` + `test_interfaces.py` 11건.
- **화면은 축이 둘이다** — 좌측 레일에서 설비 기준 ↔ 제조사 기준을 바꾼다(D-016 ⑵).
  계열 화면의 모델 목록은 제조사로 묶이고, 모델 안에서는 판(인터페이스)을 골라 본다.
  `build.py PUBLIC_MODEL_EQUIP_IDS` 가 화면에 싣는 계열(이제 e5 하나가 아니다),
  `PURPOSE_EQUIP_IDS` 는 형번·템플릿 워크스페이스가 정의된 계열(e5)만.
- 검토 화면은 둘이다 — `review/equip-catalog.html`(전체 카탈로그, `build.py`) ·
  `review/jci-ingest.html`(JCI 취입 검사대, `ingest_jci.py --export`).

- **형번 데이터는 확정 데이터셋(골든 레코드)** — 추출은 제안, 정본은
  `pipeline/data/units/<모델>.json`(23모델 360건). 속성 사전 `data/unit-schema.json`
  (ETIM식: 공유 features + 설비 클래스별 열·라벨·역할 — 냉동기는 응축 코일·팬 라벨).
  새 벤더 등록 후 **`units.py --sync` 필수**, 검수 승격 `--verify`. 화면은 확정본만
  읽고 상태 배지(자동 추출/확인됨/수기 입력)·표↔카드 토글(카드=시리즈 대표 사진)이 있다.
- **형번 추출 대상 설비는 코드가 아니라 `unit-schema.json` classes 가 정한다**
  (2026-08-05 전수 감사, 하드코딩 제거). 클래스 설비(e5·e9) 42모델 전수 = 형번 확정본
  24모델 + 무형번 18모델(전부 gap 에 문서 한계 사유 기록). validate
  `units-none`/`units-unclassed` 정보로 상시 표면화, 사유 없는 무형번은 W. 게이트 테스트로 강제.
- ⚠ **Daikin 신형 카탈로그(CAT 261·639·641)는 표 없는 브로슈어** — ED/구판을 써야 한다.

## History (append; 최신이 위)

- 2026-08-14 — **카탈로그 축 조사 → D-016 → JCI 취입.** 업계가 오브젝트 목록·정격을
  어떻게 정리하는지 조사했다(BTL/PICS·LonMark XIF·KNX ETS·Niagara / AHRI·ASHRAE 205·
  CIBSE PDT·ISO 16757). 공통점 둘 — ⑴ 제품과 **인터페이스(판)** 를 가른다 ⑵ 같은 집합에
  **입구를 둘**(제조사 축 · 유형 축) 둔다. 그대로 옮겼다:
  `point-schema.json` v2(interfaces 절·provenance.interfaceId/block·bacnet.alternates),
  `validate.check_interfaces` 게이트 12종, `test_interfaces.py` 11건.
  JCI 56문서를 등록(`sources.jci-york-bas-points` · collected.json 56건 SHA)하고
  `ingest_jci.py` 로 취입 — **제품 33건 · 판 84개 · 오브젝트 6,062점**. 파서 4개는
  이제 임시 폴더가 아니라 대장에서 문서 목록을 받는다(다른 PC 재현 가능).
  판 분리는 **주소 대역**으로 자동 판정한다 — 다음 블록이 앞 블록 최대 주소 위에서
  시작하면 같은 판(쪽 넘어감), 처음부터 다시 시작하면 별개 판(한 장치가 같은 주소를
  두 번 쓸 수 없다). 한 문서가 덮는 다른 제품 10개는 **별칭 모델**(`aliasOf`)로 세워
  코드로도 찾아진다 — 목록은 복제하지 않는다.
  설비 분류는 JCI 제품명의 낱말로 `cat` 4단계(`…CHILLER.SCREW`)와 Haystack 태그
  (`chiller-rotaryScrew`·`airCooling`)를 붙였다. 스크롤은 Haystack 4 에 값이 없어
  태그 없이 gap 에 적었다.
  화면은 **취입을 커밋한 뒤 따로** 했다 — 좌측 축 전환(설비 ↔ 제조사)·제조사별 묶음·
  판 선택 표, 그리고 계열 제한 해제(모델 19 → 140건). 6.2MB → 12.3MB(옛 포인트의 빈
  칸을 빼 16.9MB 에서 줄였다).
  ⚠ 고친 함정 — collect 의 최소 크기 필터(20KB)가 list 소스에서 살아 있는 문서를
  조용히 버렸다(YSAA Native 18KB). 계통 판정을 페이지 글자로 하면 머리글이 열끼리
  뒤섞여 21건이 미분류가 된다(표 머리글로 봐야 한다).

- 2026-08-05 — LG AHU 통신 킷 추가: 번호 재사용 두 킷을 구간 분리로 2모델 (`2eff576`).
  공조기(e5) 완결 — gap 전수 해소·Lennox 대용량·SEER/난방 확장 (`5132b82`).
  스키마 확장 워크플로 — 미채택 속성 발굴 도구 + 확장 4종 채택 (`4277106`).
- 2026-08-04 — Mitsubishi PAC-IF013 추가로 공조기 수집 대기열 완료 (`26e671f`).
  Systemair Access·Geniox 추가 — Modbus 절대참조로 997점 구제 (`8162e79`).
- 2026-08-04 — **상태 스냅샷 (AGENTS.md 「지금 상태」절에서 무손실 이관):**
  - 글로벌 공조기 커버리지(e5 15모델) — 수집 대기열 완료: 리더 4사 전부(Trane·
    Daikin·JCI/York·Carrier) + 미국 AAON·Lennox + 유럽 Swegon·IV Produkt·
    Systemair(Access Modbus 1,897점 — 절대참조로 997점 구제, Geniox 크기 12형번+치수)
    + 일본 Mitsubishi(PAC-IF013 킷 20점, 조합 실외기 22형번). 다음 e5 확장은
    실외기 데이터북·대용량 EHB 등 기존 모델 심화가 후보.
  - 공조기(e5) 9모델(Trane 6 + Daikin MicroTech·JCI Simplicity SE·Siemens Climatix) —
    8모델 형번·정격 후보 완료(형번 133건·전기 특성 373행 — York 32·Rebel 13 포함,
    Envistar 만 미지원: 카탈로그 표 제목이 각주 조각). 신규 6모델 사진·근거 문서 연결 완료.
  - 형번·정격 작업 화면이 냉동기(e9)까지 확장 — Daikin AGZ 16·Trane CGAM 14×3·
    Ascend·Sintesis 등 형번 후보 118건(전체 251건). 게이트는 "형번이 실제로 뽑힌 모델".
  - 냉동기(e9)에 Daikin MicroTech 3모델(AGZ·AWV·WME 계열 등) 추가.
  - 신규 6모델 전부 제품 카탈로그 정격 연결 완료(Trailblazer CAT624/635 · Rebel ED19116 ·
    York 기술가이드 2권 · Envistar 2024 · Magnitude CAT632/ED19135) — spec-map 9문서 추가.
