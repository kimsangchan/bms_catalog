# 실측 근거 — 서울캠퍼스 자동제어 포인트리스트 전수 프로파일

- 실행: 2026-07-27, `evidence/profile-pointlists.py` (Python 3.14, `PYTHONUTF8=1`)
- 대상: `D:\DB\서울캠퍼스\포인트리스트_자동제어` 전체 (하위 11 폴더)
- 원자료: `pointlist-profile.json`(2차·정본), `pointlist-profile-pass1.json`(1차, 인코딩 오류로 한글 손상 — 참고용)
- 이 프로파일의 용도: **카탈로그(표준 장비 스펙 DB)가 실제 현장을 얼마나 덮는지 측정하는 베이스라인.**
  카탈로그의 원천이 아니다 (스코프 정정 2026-07-27 — `README.md` 참조).

## 1. 규모 — 기존 조사(01) 수치 정정

| 항목 | 01-domain-discovery 기재 | 전수 실측 | 차이 원인 |
|---|---|---|---|
| CSV 파일 | 161 | **1,027** | 01은 `1캠퍼스_04월_기존`(81) + `2캠퍼스_02월_기존`(80)만 열었다 |
| 포인트 행 | 25,205 | **114,962** | 위와 동일 + `2025/` 폴더(485파일) 미포함 |
| 원천 포맷 | 1종 | **2종** | Niagara BACnet export 129파일이 미발견 상태였다 |

폴더별 파일 수: `2025` 485, `1캠퍼스_01월_기존` 77 / `_추가` 21, `1캠퍼스_04월_기존` 81 / `_추가` 51,
`2캠퍼스_01월_기존` 71 / `_추가` 62, `2캠퍼스_02월_기존` 80 / `_추가` 33, `2캠퍼스_04월_추가` 66.
→ **월별·기존/추가 스냅샷이 중첩된 시계열**이다. 같은 `OBJ_NAME`이 최대 **104개 파일**에 등장한다.

## 2. 원천 포맷 2종

### (A) 셔블 계열 — 898 파일 / 93,235 행
컬럼 37개: `SERVER_ID, SYSTEM_ID, DEVICE_ID, OBJ_TYPE, DEVICE_SEQ, SYSTEM_PT_ID, OBJ_NAME,
OBJ_UNIT_NUM, OBJ_DECIMAL, OBJ_NUMBER, ROUND_YN, OBJ_DESC, OBJ_STATUS1~10, ALARM_LV, DEADBAND,
OBJ_ABOVE, OBJ_BELOW, OBJ_IMPORTANCE, OBJ_TREND_CYCLE, OBJ_ALARM_PAGE, OBJ_ALARM_MSG, OBJ_FMS,
FMS_NAME, FMS_START_DATA, FMS_UPDATA_CYCLE, OBJ_SECURITY, OBJ_PDA, OBJ_NOTE`

### (B) Niagara BACnet export — 129 파일 / 21,727 행
컬럼 12개: `Name, Target Name, Object Name, Type, Object Type, Inst Num, Value, Export Ord,
Export, Fault Cause, Description, BACnet Writable`

이쪽이 **BACnet discovery 원천**(01 문서가 "수집 필요"로 남긴 항목)에 해당한다. 이미 보유 중이다.

## 3. 스펙 DB 설계에 직접 영향을 주는 관측

| # | 관측 (실측치) | 설계 영향 |
|---|---|---|
| O-01 | 인코딩 3종 혼재: UTF-8 BOM 498파일 / CP949 396 / ASCII 133. **손실 디코딩 0** | "깨진 인코딩"이 아니라 **디코더 선택 문제**. BOM 우선 → CP949 폴백으로 무손실 처리 가능 |
| O-02 | 단위 표기 변형: `℃` 6,168 vs `°C` 334 (셔블), `m³/hr` 538 (Niagara) vs `CMH` 2,487 (셔블) | **단위 별칭 사전 필수**(canonical 1건 수렴). 동일 물리량이 원천마다 다른 표기 |
| O-03 | 단위 오염값: `129`, `2`, `73` 이 단위 칸에 들어있음 (총 22행) | 단위는 자유문자열 금지 → `bes_unit` FK + 별칭 사전 경유 |
| O-04 | `OBJ_UNIT_NUM` 공란 74,217 / 93,235 (**79.6%**). AI(type 0)만 봐도 13,570행 공란 | 현장 데이터에서 단위를 얻을 수 없다 → **단위는 카탈로그(포인트 타입 기본단위)가 공급해야 한다** |
| O-05 | `OBJ_TYPE` 분포 3(BI) 29,086 / 0(AI) 23,493 / 2(AV) 15,019 / 4(BO) 8,326 / 1(AO) 7,409 / 5(BV) 7,379 / 7 2,297 / 8 201 / 9 17. **6(MSI) 0건** | NEUROS 코드는 BACnet enum과 **0~5만 일치**. BACnet은 MSI=13·MSO=14·MSV=19 → 코드 매핑 테이블 필수 |
| O-06 | `OBJ_TYPE`에 `"2.0" "3.0" "5.0" "0.0"` 8행 (부동소수 오염) | 취입 시 정수 강제 파싱 + 위반 행 격리 |
| O-07 | `ALARM_LV` 비영값 **0건**, `OBJ_TREND_CYCLE` 전부 공란 | 알람 등급·트렌드 주기는 현장 export에 없다 → **카탈로그 기본값이 공급**해야 함 (프로파일 default) |
| O-08 | `OBJ_STATUS1` 사용률 극저 (ON 19,536 / TRUE 20 / Off 10 / Cool 5) | 상태 enum도 현장에 없다 → `bes_enum_set` 카탈로그가 공급 |
| O-09 | `OBJ_DESC` 채움 34.8%, Niagara `Description` 32.6% | 설명 텍스트 기반 자동 분류는 3분의 1에만 작동 |
| O-10 | `(SERVER_ID, SYSTEM_ID, DEVICE_ID)` 조합 **161종** = 한 스냅샷의 파일 수와 일치 | **1 파일 = 1 컨트롤러(판넬/NC)**. 컨트롤러 토폴로지를 파일 단위로 복원 가능 |
| O-11 | `(SERVER_ID, SYSTEM_ID, DEVICE_ID, SYSTEM_PT_ID)` 29,329종 중 26,098종이 중복 | 이 키는 **스냅샷 내에서만 유일**. 취입 PK에 스냅샷 축이 반드시 필요 |
| O-12 | `OBJ_NAME` 패턴: flat 67,657(72.6%) / `장비.points.포인트` 22,502(24.1%) / 기타 dot 3,076(3.3%) | 01이 전제한 `.points.` 분해는 **24%에만** 적용된다. 이름 파싱 의존 설계는 성립하지 않음 |
| O-13 | Niagara `BACnet Writable`: 공란 12,037 / `in1,in4,in7,in8` 8,720 / `in1,in4,in8` 674 / 전 우선순위 265 | **쓰기 가능 여부 + BACnet priority array 슬롯**을 실데이터로 확보 가능 |
| O-14 | Niagara `Value` 상태 플래그: ok 15,135 / **overridden 3,608** / unackedAlarm 1,791 / null 838 / down 142 / fault 12 | 현장 3,608점이 수동 오버라이드 상태 — 스펙 대조 시 "정상 아님"으로 걸러야 함 |
| O-15 | Niagara `Object Type`에 `Notification Class` 127, `Structured View` 24 포함 | 포인트가 아닌 BACnet 객체가 섞여 있다 → 취입 필터 필요 |
| O-16 | 포인트명에 Modbus 레지스터 주소가 박혀 있음: `유량값40002`, `환수온도40036`, `순방향 적산값40010` | 40001+ = holding register. 주소는 **모델 통신맵**에 있어야 할 정보가 이름으로 새어나온 것 |

## 4. 장비군 분포 (HVAC 우선 근거)

키워드 매칭 (한 행이 여러 군에 중복 계수될 수 있음):

| 장비군 | 매칭 행 | 대표 토큰 |
|---|---|---|
| AHU 공조기 | 17,541 | `AHU`, `AH-1xx`, 공조 |
| FAN 송풍기 | 16,519 | `SF`, `RF`, `KEF`, `EF` |
| VAV 변풍량 | 15,390 | `VAV`, `FP`, `AirFlow` |
| FCU 팬코일 | 6,493 | `FC-`, 팬코일 |
| HEATEX 열교환 | 4,097 | `HV`, `HVU`, 전열교환 |
| COOLING TOWER 냉각탑 | 3,210 | `CTCH`, `CT-`, 냉각탑 |
| BOILER 열원(온수) | 2,299 | `HWG`, 보일러 |
| EHP·항온항습 | 2,269 | `BIOT`, `AC_`, 실내기 |
| VFD 인버터 | 2,112 | `INV`, `FC101` |
| PUMP 펌프 | 1,538 | `WPC`, 펌프 |
| CHILLER 냉동기 | 1,322 | `UC-800`, `TRANE`, 터보 |
| 미매칭 | 40,144 | — |

매칭된 장비군은 **거의 전부 HVAC**이다 → "공조/HVAC부터" 결정(D-005)의 실증 근거.
미매칭 40,144행은 계량·가스검지·조명·방재 등 + 코드성 이름(`MD_11_AO1_A062`)이다.

## 5. 모델명 추출 가능성 (모델별 spec의 관건)

정규식 `[A-Z]{2,}[- ]?\d{2,4}[A-Z]?` 상위: `FC-101` 5,342 · `UC-800` 636 · `GTC-200A` 208 ·
`RGWA120` · `MGC_80` / 그리고 `AH-101~AH-405` 수십 종, `CT-101~CT-106`.

- **진짜 모델명**: `FC-101`(Danfoss VLT HVAC Drive), `UC-800`(Trane 냉동기 컨트롤러), `GTC-200A`, `RGWA120`
- **장비 태그번호(모델 아님)**: `AH-114`, `CT-103` — 같은 정규식에 걸린다
→ 이름에서 모델명을 자동 확정하는 것은 불가. **후보 추천 + 사람 확정**이 유일하게 안전한 경로.
  가정 A-05("spec은 제조사 문서로 보강")와 결정 D-003을 실측으로 재확인.

## 6. 포인트 타입 정본 후보 (상위 실측 포인트명)

VAV: `Op Mode` 1,074 · `Analog Damper Output` 1,072 · `AirFlow` 1,072 · `Zone Temperature` 1,068 ·
`Control Mode Config` 1,056 · `Occupied Max/Min Set Flow` 694/691 · `Occupied Cool/Heat Setpoint` 171/169 ·
`AirFlow Setpoint` 163 · `Min Damper Position` 110
VFD(FC-101): `DCLINK_VOLTAGE` · `INV_ACCUM_PWR` · `INV_OUT_CURRENT` · `INV_OUT_PWR` ·
`INV_OUT_VOLTAGE` · `INV_RUN_TIME` · `INV_SPEED_FC101` 각 762 · `INV_HEATsink TEMP` 700
계량·검지: `순시유량`/`적산유량` 각 102 · `채널N 고장/알람1~3/점검 상태` · `N번채널농도`
실내기: `현재온도`/`현재습도`/`가습·난방·냉방상태`/`팬상태`/`운전정지`

포인트명 고유값 **1,206종**(`.points.` 분해분 기준), 장비 인스턴스 고유값 **955종**.
→ SC-003(카탈로그 커버리지) 판정에 이 상위 목록을 고정 채점셋으로 쓴다.
