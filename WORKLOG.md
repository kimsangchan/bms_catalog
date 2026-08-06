# WORKLOG — solution-planning

세션/에이전트 간 핸드오프 로그. **"다음 할 일"은 여기 쓰지 않는다 → `NEXT.md`.**
긴 로그는 붙이지 말고 결과만 요약한다.

## Current State

- Status: doing
- Focus: BMS 장비 스펙·태그 기준 DB — 공조기(e5) 완결, 다음은 형번 클래스 확장(NEXT.md)
- Last updated: 2026-08-06
- 규모: 모델 **95건** · 오브젝트 **24,376점** · 정격 사양 **76모델** · `validate.py` 오류 0 · 계열 10/19

### 오래 유지되는 사실 (구조 메모)

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
