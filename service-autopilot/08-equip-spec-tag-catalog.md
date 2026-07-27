# 자동제어 장비별 spec · tag 표준 조사

- 조사 2026-07-27 · 대상: 빌딩 자동제어 장비 — **공조/HVAC 계통 전체** (D-006에 따라 HVAC 우선)
- 목적: **장비 종류가 정해지면 따라 정해지는 것**을 정리한다 — 태그(고정), 포인트 목록(고정), spec 항목(고정).
  값이 아니라 **항목·구조**를 확정하는 문서다.

## 이 문서의 근거

| 근거 | 무엇을 가져왔나 |
|---|---|
| **Project Haystack 4** — [Equips](https://project-haystack.org/doc/docHaystack/Equips) · [AHUs](https://project-haystack.org/doc/AHUs) · [ChangeLog](https://project-haystack.org/doc/docHaystack/ChangeLog) | 태그 정본. 장비 계층·물질·물리량·역할 마커 |
| **Haystack 4.0 사전 실물** — `haystack-tags.json`(equip 178 / property 368 / role 8) + `haystack-tag-relations.json`(부모관계 333건) | 실제 사용 가능한 태그와 **부모 계층**. 아래 표의 계층은 이 관계 파일에서 그대로 인용 |
| **Brick Schema** — [개념](https://docs.brickschema.org/brick/concepts.html) · [클래스](https://brick.andrew.cmu.edu/schema/1.1/Brick/) | 대응 클래스명 (그래프 질의용 매핑 레이어) |
| **건축기계설비 설계기준** (국토해양부 제정 / 대한설비공학회) · **기계설비 기술기준** ([codil.or.kr](https://www.codil.or.kr/filebank/construction/DC/CIGCDCC90009/CIGCDCC90009.pdf)) | 국내 spec 항목·표기 기준 |
| **표준품셈 기계설비공사** ([자료](https://files-scs.pstatic.net/2024/12/06/d4igyJKhBl/052009%ED%91%9C%EC%A4%80%ED%92%88%EC%85%88%EC%84%A4%EB%B9%84%EC%B5%9C%EC%A2%85.pdf)) · 장비일람표 관례 | 장비별 필수 기재 항목 (형식·규격·용량·동력·전원) |
| **ASHRAE Guideline 36-2024** ([ANSI](https://webstore.ansi.org/standards/ashrae/ashraeguideline362024)) | 제어 시퀀스 정본 — 유료 표준이라 **조항 참조만** 두고 원문은 복제하지 않는다 |

**현장 포인트리스트는 이 문서의 근거가 아니다.** 조사 결과가 실제 현장 이름에 걸리는지 채점한 결과는
별도 노트로 분리했다 → `evidence/tag-match-note.md`.

---

# 1. 태그 체계 읽는 법

Haystack은 태그를 **여러 개 조합해서** 의미를 만든다. 단일 코드가 아니다. 포인트 하나는 4요소로 표현된다.

```
① 역할(role)      sensor(계측) | cmd(지령) | sp(설정값)
② 물리량(quantity) temp | pressure | flow | humidity | volt | elec-power | freq | …
③ 물질·구간        물: chilled-water | hot-water | condenser-water | steam
                   공기: supply-air | return-air | outside-air | exhaust-air | mixed-air
④ 소속 장비        equipRef → 그 장비의 equip 태그 (ahu, vav, chiller …)
```

예시 (사전 실물에 전부 존재):

| 포인트 | 태그 조합 |
|---|---|
| 공조기 급기온도 | `discharge` + `air` + `temp` + `sensor` + `point` → equipRef=`ahu` |
| 냉동기 냉수 출구온도 | `chilled-water` + `temp` + `sensor` + `point` → equipRef=`chiller` |
| 냉수밸브 개도 지령 | `chilled-water` + `valve` + `cmd` + `point` (+ `position`★) |
| 급기 정압 설정값 | `discharge` + `static-pressure` + `sp` + `point` |

물에는 공기 계열 태그(`supply-air` 등)를 쓰지 않는다. 반대도 같다. **물질 계열을 섞으면 안 된다.**

표기 규약: **✓** = 사전 실물에 존재 확인 · **★** = 사전에 없음(보강 필요, 17절)

---

# 2. 장비 분류 트리 — Haystack 4 정본 계층

`haystack-tag-relations.json`의 부모관계를 그대로 옮긴 것이다. 우리 분류 체계는 이 계층을 따른다.

```
equip
├─ airHandlingEquip
│  ├─ ahu ✓
│  │  ├─ doas ✓ (외기전용) ─ mau ✓ (급기전용)
│  │  └─ rtu ✓ (옥상형 일체)
│  └─ fcu ✓
│     ├─ crac ✓ (항온항습·전산실)
│     └─ unitVent ✓ (유닛벤틸레이터)
├─ airTerminalUnit ✓
│  ├─ vav ✓ (변풍량)
│  ├─ cav ✓ (정풍량)
│  └─ chilledBeam ✓
├─ chiller ✓            냉동기
├─ coolingTower ✓       냉각탑
├─ boiler ✓ ── hot-water-boiler ✓ · steam-boiler ✓ · biomass-boiler ✓
├─ heatExchanger ✓ ── condenser ✓ · evaporator ✓
├─ compressor ✓
├─ heatPump ✓ ── air-source ✓ · water-source ✓ · geothermal ✓
├─ heat-recovery ✓      전열교환
├─ pump ✓ ── booster-pump ✓ · submersible-pump ✓ · fire-pump ✓
├─ fan ✓ ── supply-fan ✓ · return-fan ✓ · exhaust-fan ✓ · cooling-tower-fan ✓
├─ coil ✓ ── coolingCoil ✓ · heatingCoil ✓
├─ valve ✓ ── two-way-valve ✓ · three-way-valve ✓ · check-valve ✓
│              pressure-relief-valve ✓ · expansion-valve ✓
├─ damper ✓ ── smoke-damper ✓ · fire-damper ✓
├─ actuator ✓ ── valve-actuator ✓ · damper-actuator ✓
├─ motor ✓ ── fan-motor ✓ · pump-motor ✓
├─ vfd ✓                인버터
├─ airfilter ✓ · humidifier-equip ✓ · dehumidifier ✓
├─ vrf-equip
│  ├─ vrf-indoorUnit ✓ ── vrf-indoorUnit-fcu ✓
│  ├─ vrf-outdoorUnit ✓
│  └─ branchSelector ✓
├─ plant
│  ├─ chilled-water-plant ✓ · hot-water-plant ✓ · steam-plant ✓
│  └─ vrf-refrig-plant ✓ · ates ✓ (대수·계통 묶음)
├─ meter ✓ ── elec-meter ✓ (ac/dc) · flow-meter ✓ · power-meter ✓
├─ 계측기 pressure-sensor ✓ · flow-sensor ✓ · level-sensor ✓ · thermocouple ✓
│         vibration-sensor ✓ · noise-sensor ✓
├─ 제어기 ddc ✓ · io-module ✓ · thermostat ✓ · gateway ✓ · control-panel ✓ · mcc ✓
└─ 배관·덕트 conduit ✓ ── pipe ✓ · duct ✓ · strainer ✓ · header ✓ · expansion-tank ✓
```

**물질(substance) 계열** — 포인트 태깅에 쓰는 유체:
`chilled-water` ✓ · `hot-water` ✓ · `cool-water` ✓ · `warm-water` ✓ · `condenser-water` ✓ ·
`cold-water` ✓ · `domestic-water` ✓ · `makeup-water` ✓ · `blowdown-water` ✓ · `condensate` ✓ ·
`steam` ✓ · `ice` ✓ · `refrig` ✓ / 공기: `supply-air` ✓ `return-air` ✓ `exhaust-air` ✓ `outside-air` ✓ `mixed-air` ✓

**물리량(quantity) 계열**:
`temp` ✓(하위 `air-temp` `dewPoint` `wetBulb`) · `pressure` ✓(하위 `static-pressure` `total-pressure`
`velocity-pressure` `differential-pressure`) · `humidity` ✓ · `flow` ✓ · `volume` ✓ · `level` ✓ ·
`freq` ✓(하위 `ac-freq` **`vfd-freq`**) · `speed` ✓(하위 **`vfd-speed`** `air-velocity`) ·
`current` ✓(`elec-current` `phaseCurrent` `leakage-current`) · `volt` ✓(`phase-voltage`) ·
`power` ✓(`elec-power` `active-power` `reactive-power` `apparent-power`) · `energy` ✓(`elec-energy`) ·
`concentration` ✓(`co2-concentration` `voc` `pm25-concentration`) · `occupancy` ✓

**경보(alarm) 계열**: `critical` `major` `minor` `warning` `info` `low-low` `high-high`
`alarm-priority` `alarm-source` `alarm-text` `alarm-time` — 전부 ✓ (부모 `alarm`)

---

# 3. spec 항목의 공통 골격

국내 장비일람표·설계기준이 요구하는 공통 기재 항목이다. 장비별 표는 이 골격 위에 고유 항목을 얹는다.

| 공통 항목 | 단위 | 비고 |
|---|---|---|
| 형식 | — | 장비 종류별 세부 형식 (터보/스크류, 시로코/터보, 판형/쉘앤튜브…) |
| 규격·호칭 | — | 모델 계열 |
| 용량 | 장비별 | **조건 없는 용량은 무효** (4절) |
| 전동기 출력 | kW | 대수 포함 |
| 회전수 | rpm | |
| 전원 | V / φ / Hz | 예 `380V/3φ/60Hz` |
| 수량 | 대 | |
| 중량 / 치수 | kg / mm | W×D×H |
| 소음 | dB(A) | |
| 제조사 · 모델코드 | — | 근거 문서 필수 |

## spec 값의 3가지 성격 — 섞으면 안 된다

| 구분 | 뜻 | 예 |
|---|---|---|
| **정격(rated)** | 명판 값. 장비 수명 내 불변 | 정격풍량 12,000 CMH |
| **설계(design)** | 이 현장에서 요구한 값 | 설계풍량 10,500 CMH |
| **조건부 성능** | 특정 조건에서의 값. **조건 없이 쓰면 무의미** | 냉동능력 300 RT @ 냉수 12/7℃, 냉각수 32/37℃ |
| (참고) 가변값 | 운전 중 변함 → **spec 아님, 포인트다** | 현재 부하율, 현재 풍량 |

---

# 4. 단위 표기 기준

| 물리량 | 표기 | 정규 코드 |
|---|---|---|
| 온도 | ℃ | `degC` |
| 개도·백분율 | % | `percent` |
| 풍량 | CMH (=㎥/h) | `m3h` |
| 수량(유량) | LPM, ㎥/h | `Lpm`, `m3h` |
| 정압 | mmAq, Pa | `mmH2O`, `Pa` |
| 수압 | kPa, MPa | `kPa`, `MPa` |
| 주파수 | Hz | `Hz` |
| 전압·전류 | V, A | `V`, `A` |
| 전력·전력량 | kW, kWh | `kW`, `kWh` |
| 열량 | kW, kcal/h, RT | `kW`, `kcal/h`, `RT` |
| 농도 | ppm, ㎍/㎥ | `ppm`, `ug/m3` |

동일 물리량에 표기가 둘 이상이면 하나로 모은다(℃/°C → `degC`, CMH/㎥/h → `m3h`).
**RT ↔ kW 환산은 1 RT = 3.516 kW**(냉동톤)로 고정한다.

---

# 5. 공조기 (AHU)

**태그** `ahu` ✓ ← 부모 `airHandlingEquip` ✓ / 변형 `doas` ✓(외기전용) · `mau` ✓ · `rtu` ✓(옥상형)
**Brick** `Air_Handling_Unit` (`AHU`) / 옥상형 `Rooftop_Unit`
**부속 장비** `supply-fan` ✓ · `return-fan` ✓ · `coolingCoil` ✓ · `heatingCoil` ✓ · `airfilter` ✓ ·
`humidifier-equip` ✓ · `damper-actuator` ✓ (부속은 `equipRef`로 AHU에 매단다)

## spec 항목

| 항목 | 단위 | 조건·비고 |
|---|---|---|
| 급기 풍량 | CMH | 정격/설계 구분 |
| 환기 풍량 | CMH | 환기팬 있는 경우 |
| 최소 외기량 | CMH 또는 % | 환기기준 산출값 |
| 기외정압 | mmAq / Pa | 덕트 저항 |
| 급기팬 형식·모터출력 | — / kW | 시로코·터보·플러그 |
| 환기팬 형식·모터출력 | — / kW | |
| 냉수코일 능력 | kW | **조건**: 냉수 7/12℃, 입구공기 27℃DB·19℃WB |
| 온수코일 능력 | kW | **조건**: 온수 60/50℃, 입구공기 5℃ |
| 냉수·온수 유량 | LPM | |
| 코일 열수·핀피치 | row / mm | 냉수·온수 각각 |
| 코일 정면풍속 | m/s | 보통 2.5~3.0 |
| 필터 형식·효율·차압 | — / % / Pa | 프리·미디엄·HEPA (초기·최종 차압) |
| 가습 방식·가습량 | — / kg/h | 증기·기화·초음파 |
| 열회수 유무·효율 | — / % | 전열교환 내장형 |
| 케이싱·단열 | — | 판넬 두께·단열재 |
| 전원 | V/φ/Hz | |

## 표준 포인트

| 포인트 | 종류 | 단위 | 역할 | 태그 조합 | 등급 |
|---|---|---|---|---|---|
| 급기온도 | AI | ℃ | sensor | `discharge`✓ `air`✓ `temp`✓ | 필수 |
| 환기온도 | AI | ℃ | sensor | `return-air`✓ `temp`✓ | 필수 |
| 외기온도 | AI | ℃ | sensor | `outside-air`✓ `temp`✓ | 필수 |
| 혼합공기온도 | AI | ℃ | sensor | `mixed-air`✓ `temp`✓ | 권장 |
| 급기습도 | AI | % | sensor | `discharge`✓ `air`✓ `humidity`✓ | 권장 |
| 환기습도 | AI | % | sensor | `return-air`✓ `humidity`✓ | 권장 |
| 급기 정압 | AI | Pa | sensor | `discharge`✓ `static-pressure`✓ | 필수 |
| 급기 풍량 | AI | CMH | sensor | `discharge`✓ `air`✓ `flow`✓ | 권장 |
| 환기 CO2 | AI | ppm | sensor | `return-air`✓ `co2-concentration`✓ | 권장 |
| 급기온도 설정값 | AV | ℃ | sp | `discharge`✓ `air`✓ `temp`✓ | 필수 |
| 급기 정압 설정값 | AV | Pa | sp | `discharge`✓ `static-pressure`✓ | 권장 |
| 급기팬 주파수 지령 | AO | Hz | cmd | `supply-fan`✓ `vfd-freq`✓ | 필수 |
| 환기팬 주파수 지령 | AO | Hz | cmd | `return-fan`✓ `vfd-freq`✓ | 권장 |
| 냉수밸브 개도 | AO | % | cmd | `chilled-water`✓ `valve`✓ `position`★ | 필수 |
| 온수밸브 개도 | AO | % | cmd | `hot-water`✓ `valve`✓ `position`★ | 필수 |
| 외기댐퍼 개도 | AO | % | cmd | `outside-air`✓ `damper`✓ `position`★ | 필수 |
| 환기댐퍼 개도 | AO | % | cmd | `return-air`✓ `damper`✓ `position`★ | 권장 |
| 배기댐퍼 개도 | AO | % | cmd | `exhaust-air`✓ `damper`✓ `position`★ | 권장 |
| 가습 지령 | AO/BO | % | cmd | `humidifier-equip`✓ `cmd`✓ | 선택 |
| 필터 차압 | AI/BI | Pa | sensor | `airfilter`✓ `differential-pressure`✓ | 권장 |
| 동결 방지 경보 | BI | — | sensor | `temp`✓ `alarm`✓ `critical`✓ | 권장 |
| 운전 모드 | MSO | — | cmd | (정지/냉방/난방/송풍/외기냉방) | 필수 |
| 외기냉방 모드 | BV | — | cmd | `economizer-mode`✓ `free-cooling`✓ | 권장 |

> 제어 시퀀스: ASHRAE Guideline 36-2024 다구역 VAV AHU 절 참조.

---

# 6. 터미널 유닛 (VAV · CAV)

**태그** `vav` ✓ / `cav` ✓ ← 부모 `airTerminalUnit` ✓ / 형제 `chilledBeam` ✓
**Brick** `Variable_Air_Volume_Box` / `Constant_Air_Volume_Box`

## spec 항목

| 항목 | 단위 | 조건·비고 |
|---|---|---|
| 정격 풍량 | CMH | |
| 최대·최소 풍량 | CMH | 최소는 환기 확보량 |
| 인렛 구경 | mm | 200·250·300·350·400 |
| 정압 손실 | Pa | 정격 풍량 기준 |
| 풍량 측정 방식 | — | 차압식·열선식 |
| 재열코일 유무·능력 | — / kW | 온수 유량·구경 포함 |
| 팬 내장(팬파워드) 유무·출력 | — / kW | |
| 액추에이터 토크·구동시간 | Nm / s | |
| 소음(NC) | — | |

## 표준 포인트

| 포인트 | 종류 | 단위 | 역할 | 태그 조합 | 등급 |
|---|---|---|---|---|---|
| 실내온도 | AI | ℃ | sensor | `zone`✓ `air`✓ `temp`✓ | 필수 |
| 풍량 | AI | CMH | sensor | `discharge`✓ `air`✓ `flow`✓ | 필수 |
| 풍량 설정값 | AV | CMH | sp | `discharge`✓ `air`✓ `flow`✓ | 필수 |
| 최대 풍량 설정 | AV | CMH | sp | `air`✓ `flow`✓ `maxVal`✓ | 필수 |
| 최소 풍량 설정 | AV | CMH | sp | `air`✓ `flow`✓ `minVal`✓ | 필수 |
| 댐퍼 개도 지령 | AO | % | cmd | `damper`✓ `position`★ | 필수 |
| 최소 댐퍼 개도 | AV | % | sp | `damper`✓ `minVal`✓ `position`★ | 권장 |
| 재실 냉방 설정온도 | AV | ℃ | sp | `occupied`✓ `zone`✓ `temp`✓ | 필수 |
| 재실 난방 설정온도 | AV | ℃ | sp | `occupied`✓ `zone`✓ `temp`✓ | 필수 |
| 비재실 설정온도 | AV | ℃ | sp | `zone`✓ `temp`✓ `setback`✓ | 권장 |
| 운전 모드 | MSO | — | cmd | (정지/냉방/난방/환기) | 필수 |
| 재실 감지 | BI | — | sensor | `occupancy`✓ `occupied`✓ | 권장 |
| 재열밸브 개도 | AO | % | cmd | `hot-water`✓ `valve`✓ `reheat`★ | 선택 |
| 내장팬 운전 | BO | — | cmd | `fan`✓ `run`✓ | 선택 |

---

# 7. 팬코일 유닛 (FCU) · 항온항습기 (CRAC)

**태그** `fcu` ✓ ← 부모 `airHandlingEquip` ✓ / 하위 `crac` ✓(항온항습·전산실) · `unitVent` ✓
**Brick** `Fan_Coil_Unit` / `Computer_Room_Air_Conditioning`

## spec 항목

| 항목 | 단위 | 조건·비고 |
|---|---|---|
| 냉방능력 | kW | **조건**: 냉수 7/12℃, 실내 27℃DB·19.5℃WB |
| 난방능력 | kW | **조건**: 온수 60/50℃, 실내 20℃ |
| 정격 풍량 | CMH | 강 단계 기준 |
| 팬 단계 수 | 단 | 보통 3단 |
| 모터 출력 | W | |
| 냉수·온수 유량 | LPM | |
| 배관 구경 | mm | 공급·환수 |
| 응축수 배관·드레인펌프 | mm / — | |
| 정압 | Pa | 덕트형 |
| 형식 | — | 노출·매입·덕트·카세트 |
| (CRAC) 제습·가습 능력 | kg/h | 항온항습만 |
| (CRAC) 온·습도 정밀도 | ±℃ / ±% | 항온항습만 |

## 표준 포인트

| 포인트 | 종류 | 단위 | 역할 | 태그 조합 | 등급 |
|---|---|---|---|---|---|
| 실내온도 | AI | ℃ | sensor | `zone`✓ `air`✓ `temp`✓ | 필수 |
| 설정온도 | AV | ℃ | sp | `zone`✓ `air`✓ `temp`✓ | 필수 |
| 팬 단계 | MSO | — | cmd | `fan`✓ `speed`✓ | 필수 |
| 냉수밸브 | BO/AO | — / % | cmd | `chilled-water`✓ `valve`✓ | 필수 |
| 온수밸브 | BO/AO | — / % | cmd | `hot-water`✓ `valve`✓ | 필수 |
| 냉난방 모드 | MSO | — | cmd | `cooling-mode`✓ `heating-mode`✓ | 필수 |
| 실내습도 | AI | % | sensor | `zone`✓ `humidity`✓ | 선택(CRAC 필수) |
| 습도 설정값 | AV | % | sp | `zone`✓ `humidity`✓ | 선택(CRAC 필수) |
| 응축수 넘침 | BI | — | sensor | `condensate`✓ `level`✓ `alarm`✓ | 권장 |
| 스케줄 사용 | BV | — | cmd | `enable`✓ `occupied`✓ | 권장 |

---

# 8. VRF (실내기 · 실외기)

**태그** `vrf-indoorUnit-fcu` ✓ ← `vrf-indoorUnit` ✓ ← `vrf-equip` / 실외기 `vrf-outdoorUnit` ✓ ·
분배기 `branchSelector` ✓ · 계통 `vrf-refrig-plant` ✓ / 히트펌프 계열은 `heatPump` ✓
**Brick** `Terminal_Unit` / `Heat_Pump`

## spec 항목

| 항목 | 단위 | 조건·비고 |
|---|---|---|
| 냉방능력 / 난방능력 | kW | 표준조건 (냉방 실내27/실외35℃, 난방 실내20/실외7℃) |
| 정격 소비전력 | kW | 냉방·난방 각각 |
| COP / SEER | — | `cop` ✓ `eer` ✓ 태그 존재 |
| 냉매 종류·충전량 | — / kg | R410A·R32·R134a |
| 배관 구경 (액·가스) | mm | |
| 정격 풍량 | CMH | 강 기준 |
| 형식 | — | 4WAY 카세트·1WAY·덕트·벽걸이·바닥 |
| 실외기 조합 | — | 매칭 모델·연결 대수·최대 연장배관 |
| 통신 방식 | — | 벤더 게이트웨이 (BACnet/Modbus 변환) |

## 표준 포인트

| 포인트 | 종류 | 단위 | 역할 | 태그 조합 | 등급 |
|---|---|---|---|---|---|
| 실내온도 | AI | ℃ | sensor | `zone`✓ `air`✓ `temp`✓ | 필수 |
| 설정온도 | AV | ℃ | sp | `zone`✓ `air`✓ `temp`✓ | 필수 |
| 토출온도 | AI | ℃ | sensor | `discharge`✓ `air`✓ `temp`✓ | 권장 |
| 운전 모드 | MSO | — | cmd | (냉방/난방/송풍/제습/자동) | 필수 |
| 풍량 단계 | MSO | — | cmd | `fan`✓ `speed`✓ | 필수 |
| 에러 코드 | AI/MSO | — | sensor | `fault`✓ `alarm-text`✓ | 필수 |
| 필터 청소 신호 | BI | — | sensor | `airfilter`✓ `alarm`✓ | 권장 |
| 재실 감지 | BI | — | sensor | `occupancy`✓ | 권장 |
| 리모컨 잠금 | BO | — | cmd | `enable`✓ | 선택 |
| (실외기) 압축기 운전율 | AI | % | sensor | `compressor`✓ `load`★ | 권장 |
| (실외기) 소비전력 | AI | kW | sensor | `elec-power`✓ | 권장 |

---

# 9. 냉동기 (칠러)

**태그** `chiller` ✓ / 계통 `chilled-water-plant` ✓ / 부속 `compressor` ✓ · `evaporator` ✓ · `condenser` ✓
**Brick** `Chiller` (하위 `Absorption_Chiller`, `Centrifugal_Chiller`, `Screw_Chiller` 계열)
**형식 구분은 태그가 아니라 spec 항목으로** — 사전에 `centrifugal-chiller` 등은 없다(17절)

## spec 항목

| 항목 | 단위 | 조건·비고 |
|---|---|---|
| 냉동능력 | RT 또는 kW | **조건 필수**: 냉수 12/7℃, 냉각수 32/37℃ |
| 압축기 형식 | — | 터보(원심)·스크류·스크롤·왕복동·흡수식 |
| COP / IPLV | — | 부분부하 효율 |
| 냉수 입·출구온도 | ℃ | 설계치 |
| 냉수 유량 | LPM 또는 ㎥/h | |
| 냉각수 입·출구온도 | ℃ | 수냉식 |
| 냉각수 유량 | LPM | |
| 증발기·응축기 압력손실 | kPa | |
| 정격 전압·전류·소비전력 | V / A / kW | |
| 기동 방식 | — | Y-Δ·리액터·인버터 |
| 냉매 종류·충전량 | — / kg | R134a·R1234ze·R513A |
| 최소 부하율 | % | 언로딩 한계 |
| (흡수식) 열원·소비량 | — / N㎥/h·kg/h | 가스·중온수·증기 |
| 소음 | dB(A) | |

## 표준 포인트

| 포인트 | 종류 | 단위 | 역할 | 태그 조합 | 등급 |
|---|---|---|---|---|---|
| 냉수 출구온도 | AI | ℃ | sensor | `chilled-water`✓ `temp`✓ `leaving`★ | 필수 |
| 냉수 입구온도 | AI | ℃ | sensor | `chilled-water`✓ `temp`✓ `entering`★ | 필수 |
| 냉수 출구온도 설정값 | AV | ℃ | sp | `chilled-water`✓ `temp`✓ | 필수 |
| 냉각수 출구온도 | AI | ℃ | sensor | `condenser-water`✓ `temp`✓ `leaving`★ | 필수 |
| 냉각수 입구온도 | AI | ℃ | sensor | `condenser-water`✓ `temp`✓ `entering`★ | 필수 |
| 부하율 | AI | % | sensor | `load`★ | 필수 |
| 소비전력 | AI | kW | sensor | `elec-power`✓ | 필수 |
| 적산 전력량 | AI | kWh | sensor | `elec-energy`✓ | 권장 |
| 압축기 전류 | AI | A | sensor | `compressor`✓ `elec-current`✓ | 권장 |
| 증발 압력·온도 | AI | kPa / ℃ | sensor | `evaporator`✓ `refrig`✓ `pressure`✓ | 권장 |
| 응축 압력·온도 | AI | kPa / ℃ | sensor | `condenser`✓ `refrig`✓ `pressure`✓ | 권장 |
| 냉수 유량 | AI | ㎥/h | sensor | `chilled-water`✓ `flow`✓ | 권장 |
| 알람 코드 | AI/MSO | — | sensor | `fault`✓ `alarm-text`✓ | 필수 |
| 대수제어 순위 | AV | — | sp | `stage`★ | 권장 |
| 원격 기동 허용 | BO | — | cmd | `enable`✓ | 필수 |

---

# 10. 냉각탑

**태그** `coolingTower` ✓ / 팬 `cooling-tower-fan` ✓ ← `fan` ✓
**Brick** `Cooling_Tower`

## spec 항목

| 항목 | 단위 | 조건·비고 |
|---|---|---|
| 냉각능력 | RT 또는 kW | **조건**: 입구 37℃ / 출구 32℃ / 습구 27℃ (국내 표준) |
| 순환 수량 | LPM 또는 ㎥/h | |
| 설계 습구온도 | ℃ | 지역별 |
| 형식 | — | 직교류·대향류 / 개방식·밀폐식 |
| 팬 형식·모터출력·대수 | — / kW / 대 | |
| 팬 인버터 유무 | — | |
| 충진재 형식 | — | 필름·스플래시 |
| 보충수량 | LPM | 증발·비산·블로우다운 |
| 살수 압력 | kPa | |
| 소음 | dB(A) | |
| 중량 (운전시) | kg | 구조 검토용 |

## 표준 포인트

| 포인트 | 종류 | 단위 | 역할 | 태그 조합 | 등급 |
|---|---|---|---|---|---|
| 냉각수 출구온도 | AI | ℃ | sensor | `condenser-water`✓ `temp`✓ `leaving`★ | 필수 |
| 냉각수 입구온도 | AI | ℃ | sensor | `condenser-water`✓ `temp`✓ `entering`★ | 필수 |
| 출구온도 설정값 | AV | ℃ | sp | `condenser-water`✓ `temp`✓ | 필수 |
| 외기 습구온도 | AI | ℃ | sensor | `outside-air`✓ `wetBulb`✓ | 권장 |
| 팬 주파수 지령 | AO | Hz | cmd | `cooling-tower-fan`✓ `vfd-freq`✓ | 권장 |
| 팬 현재 주파수 | AI | Hz | sensor | `cooling-tower-fan`✓ `vfd-freq`✓ | 권장 |
| 수위 (저·고) | BI | — | sensor | `level`✓ `alarm`✓ | 필수 |
| 보충수 밸브 | BO | — | cmd | `makeup-water`✓ `valve`✓ | 권장 |
| 블로우다운 밸브 | BO | — | cmd | `blowdown-water`✓ `valve`✓ | 선택 |
| 입구 전동밸브 개도 | AO | % | cmd | `condenser-water`✓ `valve`✓ `position`★ | 권장 |
| 진동 경보 | BI | — | sensor | `vibration-sensor`✓ `alarm`✓ | 선택 |
| 수질 (전도도·pH) | AI | µS/cm · — | sensor | `condenser-water`✓ `tds`✓ / `ph`✓ | 선택 |

---

# 11. 보일러 · 온수발생기

**태그** `boiler` ✓ / 하위 `hot-water-boiler` ✓ · `steam-boiler` ✓ · `biomass-boiler` ✓ / 계통 `hot-water-plant` ✓ · `steam-plant` ✓
**Brick** `Boiler`

## spec 항목

| 항목 | 단위 | 조건·비고 |
|---|---|---|
| 정격 열출력 | kW 또는 kcal/h | |
| 열효율 | % | **저위발열량 기준 명기** |
| 연료 종류 | — | 도시가스(LNG)·LPG·경유·전기·바이오매스 |
| 연료 소비량 | N㎥/h 또는 L/h | 정격 기준 |
| 최고 사용압력 | MPa | |
| 온수 출구온도 범위 | ℃ | (증기식은 증기압력 범위) |
| 전열면적 | ㎡ | |
| 버너 형식·제어 | — | 단단·2단·비례·저NOx |
| NOx 배출 | ppm | 환경 규제치 |
| 배기 온도·배기통 구경 | ℃ / mm | |
| 안전장치 | — | 저수위·과압·실화 |
| 전원 | V/φ | |

## 표준 포인트

| 포인트 | 종류 | 단위 | 역할 | 태그 조합 | 등급 |
|---|---|---|---|---|---|
| 온수 출구온도 | AI | ℃ | sensor | `hot-water`✓ `temp`✓ `leaving`★ | 필수 |
| 온수 환수온도 | AI | ℃ | sensor | `hot-water`✓ `temp`✓ `entering`★ | 필수 |
| 출구온도 설정값 | AV | ℃ | sp | `hot-water`✓ `temp`✓ | 필수 |
| 버너 단계 / 출력 | MSO/AO | — / % | cmd | `stage`★ / `load`★ | 권장 |
| 관내 압력 | AI | kPa | sensor | `hot-water`✓ `pressure`✓ | 권장 |
| (증기) 증기압력 | AI | MPa | sensor | `steam`✓ `pressure`✓ | 필수(증기식) |
| 급수 저수위 | BI | — | sensor | `level`✓ `low-low`✓ `alarm`✓ | 필수 |
| 가스 누설 | BI | — | sensor | `gas-detector`✓ `alarm`✓ `critical`✓ | 필수 |
| 연료 적산 사용량 | AI | N㎥ | sensor | `naturalGas`✓ `volume`✓ | 권장 |
| 배기 온도 | AI | ℃ | sensor | `exhaust-air`✓ `temp`✓ | 선택 |
| 실화·소염 경보 | BI | — | sensor | `fault`✓ `critical`✓ | 필수 |

---

# 12. 열교환기 · 전열교환기

**태그** 수-수 열교환 `heatExchanger` ✓ / 공기 전열교환 `heat-recovery` ✓ /
냉매측 `condenser` ✓ · `evaporator` ✓ (부모 `heatExchanger`)
**Brick** `Heat_Exchanger` / `Energy_Recovery_Ventilator`

## spec 항목

| 항목 | 단위 | 조건·비고 |
|---|---|---|
| 열교환량 | kW | **조건**: 1·2차 입출구온도·유량 명기 |
| 형식 | — | 판형·쉘앤튜브 / 회전식·고정식(현열·전열) |
| 1차·2차 유체 | — | 냉수-냉각수, 급기-배기 등 |
| 1차·2차 유량 | LPM / CMH | |
| 1차·2차 입·출구온도 | ℃ | |
| 전열 면적 | ㎡ | |
| 압력 손실 | kPa / Pa | 1·2차 각각 |
| 온도(현열)교환효율 | % | |
| 습도(전열)교환효율 | % | 전열교환기만 |
| 최고 사용압력·온도 | MPa / ℃ | |

## 표준 포인트

| 포인트 | 종류 | 단위 | 역할 | 태그 조합 | 등급 |
|---|---|---|---|---|---|
| 1차 입구온도 | AI | ℃ | sensor | (해당 유체)✓ `temp`✓ `entering`★ | 필수 |
| 1차 출구온도 | AI | ℃ | sensor | (해당 유체)✓ `temp`✓ `leaving`★ | 필수 |
| 2차 입구온도 | AI | ℃ | sensor | (해당 유체)✓ `temp`✓ `entering`★ | 필수 |
| 2차 출구온도 | AI | ℃ | sensor | (해당 유체)✓ `temp`✓ `leaving`★ | 필수 |
| 급기온도 (전열) | AI | ℃ | sensor | `discharge`✓ `air`✓ `temp`✓ | 필수 |
| 배기온도 (전열) | AI | ℃ | sensor | `exhaust-air`✓ `temp`✓ | 필수 |
| 바이패스 댐퍼 | AO/BO | % | cmd | `bypass`✓ `damper`✓ | 권장 |
| 로터 회전 확인 (회전식) | BI | — | sensor | `heat-recovery`✓ `run`✓ | 권장 |
| 차압 | AI | Pa / kPa | sensor | `differential-pressure`✓ | 권장 |
| 급기 CO2 | AI | ppm | sensor | `discharge`✓ `air`✓ `co2-concentration`✓ | 선택 |
| 2차측 제어밸브 개도 | AO | % | cmd | (유체)✓ `valve`✓ `position`★ | 권장 |

---

# 13. 송풍기 (급기 · 환기 · 배기)

**태그** `supply-fan` ✓ / `return-fan` ✓ / `exhaust-fan` ✓ ← 부모 `fan` ✓ / 전동기 `fan-motor` ✓
**Brick** `Supply_Fan` / `Return_Fan` / `Exhaust_Fan`

## spec 항목 — 장비일람표 필수 기재(형식·규격·풍량·정압·회전수·동력·전원)

| 항목 | 단위 | 조건·비고 |
|---|---|---|
| 풍량 | CMH | |
| 정압 | mmAq 또는 Pa | 전압·정압 구분 |
| 형식 | — | 시로코(다익)·터보·익형·축류·사류·플러그 |
| 회전수 | rpm | |
| 전동기 출력 | kW | |
| 전원 | V/φ/Hz | |
| 인버터 유무 | — | |
| 효율 | % | |
| 소음 | dB(A) | |
| 구동 방식 | — | 직결·벨트 |
| 용도 | — | 급기·환기·배기·주방배기·제연 (**태그가 달라진다**) |

## 표준 포인트

| 포인트 | 종류 | 단위 | 역할 | 태그 조합 | 등급 |
|---|---|---|---|---|---|
| 주파수 지령 | AO | Hz | cmd | (용도 fan)✓ `vfd-freq`✓ | 권장 |
| 현재 주파수 | AI | Hz | sensor | (용도 fan)✓ `vfd-freq`✓ | 권장 |
| 풍량 | AI | CMH | sensor | `air`✓ `flow`✓ | 선택 |
| 벨트 끊김·차압 | BI | — | sensor | `differential-pressure`✓ `alarm`✓ | 권장 |
| 전류 | AI | A | sensor | `elec-current`✓ | 선택 |

> 용도 태그를 반드시 붙인다 — 급기 `supply-fan`, 환기 `return-fan`, 배기 `exhaust-fan`.
> 부모 `fan` 하나만 붙이면 세 종류가 구별되지 않는다.

---

# 14. 펌프

**태그** `pump` ✓ / 하위 `booster-pump` ✓ · `submersible-pump` ✓ · `fire-pump` ✓ / 전동기 `pump-motor` ✓
**Brick** `Pump` (하위 `Chilled_Water_Pump`, `Condenser_Water_Pump`, `Hot_Water_Pump`)

## spec 항목

| 항목 | 단위 | 조건·비고 |
|---|---|---|
| 정격 유량 | LPM 또는 ㎥/h | |
| 전양정 | m | |
| 전동기 출력 | kW | |
| 극수 / 회전수 | P / rpm | |
| 형식 | — | 원심·다단·라인·수중·인라인 |
| 효율 | % | 최고효율점(BEP) |
| 흡입·토출 구경 | mm | |
| 필요 NPSH | m | 캐비테이션 검토 |
| 인버터 유무 | — | 변유량 계통은 필수 |
| 전원 | V/φ | |
| 용도(계통) | — | 냉수·냉각수·온수·급수·소화 (**태그가 달라진다**) |

## 표준 포인트

| 포인트 | 종류 | 단위 | 역할 | 태그 조합 | 등급 |
|---|---|---|---|---|---|
| 주파수 지령 | AO | Hz | cmd | `pump`✓ `vfd-freq`✓ | 필수(변유량) |
| 현재 주파수 | AI | Hz | sensor | `pump`✓ `vfd-freq`✓ | 필수(변유량) |
| 토출 압력 | AI | kPa | sensor | (계통 유체)✓ `discharge`✓ `pressure`✓ | 권장 |
| 계통 차압 | AI | kPa | sensor | (계통 유체)✓ `differential-pressure`✓ | 필수(변유량) |
| 차압 설정값 | AV | kPa | sp | (계통 유체)✓ `differential-pressure`✓ | 필수(변유량) |
| 유량 | AI | ㎥/h | sensor | (계통 유체)✓ `flow`✓ | 권장 |
| 전류 | AI | A | sensor | `elec-current`✓ | 권장 |

> 계통 태그 필수: 냉수 `chilled-water` ✓ · 냉각수 `condenser-water` ✓ · 온수 `hot-water` ✓ ·
> 급수 `domestic-water` ✓. 같은 모델이라도 계통이 다르면 태그가 다르다.

---

# 15. 인버터 (VFD)

**태그** `vfd` ✓ / 유량형 `flowInverter` ✓ / 구동 대상 `motor` ✓ (`fan-motor` ✓ · `pump-motor` ✓)
**Brick** `Variable_Frequency_Drive`
**전용 물리량 태그 존재**: `vfd-freq` ✓ · `vfd-speed` ✓ — 일반 `freq`/`speed`보다 이것을 쓴다.

## spec 항목

| 항목 | 단위 | 조건·비고 |
|---|---|---|
| 정격 용량 | kW | 적용 모터 기준 |
| 정격 입력 전압·상 | V / φ | |
| 정격 출력 전류 | A | |
| 과부하 내량 | % / s | 예 110%/60s (HVAC용), 150%/60s (일반) |
| 제어 방식 | — | V/f·센서리스 벡터·벡터 |
| 통신 프로토콜 | — | Modbus RTU·BACnet MSTP·Profibus·EtherNet/IP |
| 내장 필터·리액터 | — | EMC 필터·DC 리액터 |
| 냉각 방식 | — | 강제공랭·수랭 |
| 보호등급 | IP | |
| 주변온도 범위 | ℃ | 디레이팅 조건 |

## 표준 포인트

| 포인트 | 종류 | 단위 | 역할 | 태그 조합 | 등급 |
|---|---|---|---|---|---|
| 주파수 지령 | AO | Hz | cmd | `vfd`✓ `vfd-freq`✓ | 필수 |
| 현재 주파수 | AI | Hz | sensor | `vfd`✓ `vfd-freq`✓ | 필수 |
| 출력 전류 | AI | A | sensor | `vfd`✓ `elec-current`✓ | 필수 |
| 출력 전압 | AI | V | sensor | `vfd`✓ `volt`✓ | 권장 |
| 출력 전력 | AI | kW | sensor | `vfd`✓ `elec-power`✓ | 필수 |
| 적산 전력량 | AI | kWh | sensor | `vfd`✓ `elec-energy`✓ | 권장 |
| DC 링크 전압 | AI | V | sensor | `vfd`✓ `dc-elec`✓ `volt`✓ | 권장 |
| 방열판 온도 | AI | ℃ | sensor | `vfd`✓ `temp`✓ | 권장 |
| 누적 운전시간 | AI | h | sensor | `vfd`✓ `runtime`★ | 권장 |
| 트립·고장 | BI | — | sensor | `vfd`✓ `fault`✓ `alarm`✓ | 필수 |
| 트립 코드 | AI/MSO | — | sensor | `vfd`✓ `fault`✓ `alarm-text`✓ | 권장 |
| 정·역 지령 | BO | — | cmd | `vfd`✓ `cmd`✓ | 선택 |

---

# 16. 계량 · 계측 · 제어기

## 16-1 계량기

**태그** `elec-meter` ✓(하위 `ac-elec-meter` ✓ `dc-elec-meter` ✓) · `flow-meter` ✓ · `power-meter` ✓ ← `meter` ✓
**Brick** `Electrical_Meter` / `Water_Flow_Meter` / `Building_Electrical_Meter`

| spec 항목 | 단위 | 비고 |
|---|---|---|
| 측정 범위 | 물리량 단위 | |
| 정확도 등급 | % | 예 ±0.5%, KS C 계량 등급 |
| 관경 (유량계) | mm | |
| 방식 | — | 초음파·전자식·터빈·차압 / CT·직결·PT |
| 출력 | — | 4–20mA·펄스·통신 |
| 펄스 정수 | 펄스/단위 | **적산 환산에 필수** |
| 통신 프로토콜 | — | Modbus RTU·BACnet·M-Bus |

| 포인트 | 종류 | 단위 | 역할 | 태그 조합 | 등급 |
|---|---|---|---|---|---|
| 순시 유량 | AI | ㎥/h | sensor | (유체)✓ `flow`✓ | 필수 |
| 적산 유량 | AI | ㎥ | sensor | (유체)✓ `volume`✓ | 필수 |
| 순시 전력 | AI | kW | sensor | `elec-power`✓ `active-power`✓ | 필수 |
| 적산 전력량 | AI | kWh | sensor | `elec-energy`✓ `active-energy`✓ | 필수 |
| 상전압 / 선전류 | AI | V / A | sensor | `phase-voltage`✓ / `phaseCurrent`✓ | 권장 |
| 무효·피상 전력 | AI | kvar / kVA | sensor | `reactive-power`✓ / `apparent-power`✓ | 권장 |
| 역률 | AI | — | sensor | `power-factor`★ | 권장 |

## 16-2 계측기 (단독 센서)

**태그** `pressure-sensor` ✓ · `flow-sensor` ✓ · `level-sensor` ✓ · `thermocouple` ✓ ·
`vibration-sensor` ✓ · `noise-sensor` ✓ · `gas-detector` ✓ · `co-detector` ✓ · `heat-detector` ✓

| spec 항목 | 단위 |
|---|---|
| 측정 범위 · 정확도 | 물리량 단위 / % |
| 출력 신호 | 4–20mA · 0–10V · 접점 · 통신 |
| 전원 | V DC |
| 보호등급 · 사용 온도 | IP / ℃ |
| 응답 시간 | s |

## 16-3 제어기 · 판넬 (장비가 아니라 토폴로지)

**태그** `ddc` ✓ · `io-module` ✓ · `thermostat` ✓ · `gateway` ✓ · `control-panel` ✓ · `mcc` ✓ · `client-device` ✓

| spec 항목 | 단위 | 비고 |
|---|---|---|
| I/O 점수 | 점 | AI/AO/DI/DO 각각 |
| 확장 가능 점수 | 점 | |
| 지원 프로토콜 | — | BACnet IP/MSTP·Modbus TCP/RTU·LonWorks·전용 |
| 프로그램 용량 | — | |
| 전원 | V | |
| 통신 속도 | bps | MSTP 보율 |

> 제어기·판넬은 **장비 대장이 아니라 통신 토폴로지**로 관리한다. 포인트를 소유하는 주체이지
> 스펙 카탈로그의 적용 대상(장비)이 아니다.

---

# 17. 결손 태그 — 사전에 보강해야 할 것

위 표에서 ★로 표시한 것이다. 이 태그 없이는 기본 포인트를 정확히 표현할 수 없다.

| 결손 태그 | 필요한 곳 | 사전 내 유사 | 처리 |
|---|---|---|---|
| `entering` / `leaving` | **냉동기·냉각탑·보일러·열교환기의 입·출구 온도 전부** | 없음 | Haystack 표준 마커 → 로컬 추가 (최우선) |
| `position` | 밸브·댐퍼 개도 전부 | `floor-position` | 로컬 추가 |
| `runtime` | 전 장비 누적 운전시간 | 없음 | 로컬 추가 |
| `stage` | 보일러 버너 단계, 냉동기 대수제어 | 없음 | 로컬 추가 |
| `load` | 냉동기·압축기 부하율 | `baseload`·`peakload` | 로컬 추가 |
| `reheat` / `preheat` | VAV 재열, AHU 예열 | 없음 | 로컬 추가 |
| `power-factor` | 전력 계량 역률 | `reactive-power`·`apparent-power` | 로컬 추가 |
| `unocc` | 비재실 설정값 | `occ`·`occupied`·`setback` | `setback`으로 대체 가능 |
| 냉동기 형식 (`centrifugal-chiller` 등) | 압축기 형식 구분 | 없음 | **태그로 만들지 않고 spec 항목으로 처리** |
| `capacity` / `rated` / `design` | spec 값 성격 구분 | 없음 | **태그 아님 — spec 속성 메타로 처리**(3절) |

## 사전 자체의 정합성 문제 (조사 중 발견)

`haystack-tags.json`의 **카테고리 분류가 부모관계와 어긋난다.**
`pump` · `fan` · `valve` · `damper` · `coil`은 `haystack-tag-relations.json`에서 부모가 `equip`인데,
태그 사전의 카테고리는 `property`로 매겨져 있다. 즉 **장비인데 속성으로 분류돼 있다.**

→ 태그를 카탈로그로 승격할 때 **relations를 기준으로 카테고리를 재계산**해야 한다.
그러지 않으면 장비 분류 화면에서 `pump`·`fan`이 목록에 나오지 않는다.

---

# 18. 이 조사에서 확정된 것

1. **장비 종류가 정해지면 태그와 포인트는 따라온다** — 5~16절 표가 그 고정분이다. 장비 12계열 ·
   표준 포인트 약 150종 · spec 항목 약 160종.
2. **태그는 조합이다** — 역할 + 물리량 + 물질/구간 + 소속 장비. 단일 코드로 표현하려 하면 실패한다(1절).
3. **spec은 조건과 함께여야 값이 된다** — 냉동능력은 수온 조건, 코일 능력은 공기·수온 조건과 한 몸이다(3절).
4. **같은 장비라도 계통·용도가 태그를 바꾼다** — 펌프는 냉수/냉각수/온수, 송풍기는 급기/환기/배기.
   부모 태그(`pump`·`fan`)만으로는 구별되지 않는다.
5. **결손 태그 7종을 보강해야** 입·출구 온도와 개도 같은 가장 기본적인 포인트가 표현된다(17절).
6. **사전의 카테고리 분류에 오류가 있다** — relations 기준으로 재계산 필요(17절).

## 문서 구성

| 부 | 절 | 내용 |
|---|---|---|
| 제1부 | 1~18 | 태그 체계·HVAC 12계열 spec·포인트 (위) |
| **제2부** | **19~25** | **나머지 도메인** — 전력·조명·방재·승강·보안·환경·급배수 |
| **제3부** | **26~29** | **장비 공통 정의** — 상태 enum·알람/트렌드 기본값·통신 관례·제어 시퀀스 |
| **제4부** | **30** | **모델 spec 채우기** — 등록 템플릿 + 실제 예시 |

## 아직 남은 것

| 항목 | 내용 |
|---|---|
| 모델별 실물 spec **값 확대** | 30절이 템플릿과 예시 1건까지. 나머지 모델은 제조사 카탈로그에서 근거와 함께 |
| 제어 시퀀스 **조항 번호** | 29절에 시퀀스 목록까지. 정확한 조항 번호는 G36 구매본 대조 필요 |
| Brick 클래스명 확정 | Brick 열은 공개 문서 기준 표기. 릴리스 버전을 고정해 대조할 것 |

---
---

# 제2부 — 나머지 도메인 장비

HVAC 외 자동제어·감시 대상이다. **해당 도메인 태그 142개를 사전 실물과 대조한 결과 전부 존재한다**
(결손 0건 — HVAC의 `entering`/`leaving` 같은 공백이 여기엔 없다).

---

# 19. 전력 설비

## 19-1 수변전

**태그** `substation` ✓ · `transformer` ✓ · `switchgear` ✓ · `incoming-power` ✓ · `breaker` ✓ ·
`elec-panel` ✓ · `distribution-panel` ✓ · `sub-distribution-panel` ✓ · `mcc` ✓ · `pdu` ✓ · `contactor` ✓ · `fuse` ✓ · `relay` ✓
**Brick** `Switchgear` / `Transformer` / `Electrical_Meter` 계열

| spec 항목 | 단위 | 조건·비고 |
|---|---|---|
| 정격 용량 | kVA | 변압기 |
| 1차·2차 전압 | V | 예 22.9kV / 380-220V |
| 결선 | — | Δ-Y, Y-Y |
| 임피던스 전압 | % | 단락전류 계산용 |
| 냉각 방식 | — | 건식(몰드)·유입 |
| 무부하손·부하손 | W | 효율 산정 |
| 정격 전류 / 차단 용량 | A / kA | 차단기 |
| 절연 등급·내압 | — / kV | |
| 보호 계전 방식 | — | OCR·OCGR·디지털 계전기 |

| 포인트 | 종류 | 단위 | 역할 | 태그 조합 | 등급 |
|---|---|---|---|---|---|
| 상전압 (R/S/T) | AI | V | sensor | `phase-voltage` ✓ | 필수 |
| 선전류 | AI | A | sensor | `phaseCurrent` ✓ / `lineCurrent` ✓ | 필수 |
| 유효 전력 | AI | kW | sensor | `active-power` ✓ | 필수 |
| 무효 / 피상 전력 | AI | kvar / kVA | sensor | `reactive-power` ✓ / `apparent-power` ✓ | 권장 |
| 역률 | AI | — | sensor | `power-factor` ★ | 권장 |
| 주파수 | AI | Hz | sensor | `ac-freq` ✓ | 권장 |
| 적산 전력량 | AI | kWh | sensor | `active-energy` ✓ | 필수 |
| 차단기 개폐 상태 | BI | — | sensor | `breaker` ✓ `run` ✓ | 필수 |
| 차단기 트립 | BI | — | sensor | `breaker` ✓ `fault` ✓ `critical` ✓ | 필수 |
| 변압기 권선 온도 | AI | ℃ | sensor | `transformer` ✓ `temp` ✓ | 필수 |
| 누설 전류 | AI | mA | sensor | `leakage-current` ✓ | 권장 |
| 전압·전류 불평형 | AI | % | sensor | `volt-imbalance` ✓ / `current-imbalance` ✓ | 선택 |
| 고조파 왜형률 | AI | % | sensor | `volt-thd` ✓ / `current-thd` ✓ | 선택 |
| 정전 | BI | — | sensor | `incoming-power` ✓ `fault` ✓ `critical` ✓ | 필수 |

## 19-2 비상 발전기

**태그** `generator` ✓ · **Brick** `Generator`

| spec 항목 | 단위 | 비고 |
|---|---|---|
| 정격 출력 | kVA / kW | 비상용·상용 구분 |
| 원동기 형식 | — | 디젤·가스 |
| 연료 종류·소비량 | — / L/h | 정격 부하 기준 |
| 연료 탱크 용량·연속 운전시간 | L / h | 법정 확보시간 |
| 정격 전압·주파수·역률 | V / Hz / — | |
| 기동 방식 | — | 전기식(축전지)·공기식 |
| 기동 시간 | s | 법정 요구(비상전원) |
| 축전지 사양 | V / Ah | |
| 소음·배기 처리 | dB(A) / — | |

| 포인트 | 종류 | 단위 | 역할 | 태그 조합 | 등급 |
|---|---|---|---|---|---|
| 발전 전압 / 전류 / 전력 | AI | V / A / kW | sensor | `generator` ✓ + `volt`·`elec-current`·`elec-power` ✓ | 필수 |
| 주파수 | AI | Hz | sensor | `generator` ✓ `ac-freq` ✓ | 필수 |
| 연료 수위 | AI | % | sensor | `generator` ✓ `level` ✓ | 필수 |
| 냉각수 온도 / 윤활유 압력 | AI | ℃ / kPa | sensor | `generator` ✓ + `temp`·`pressure` ✓ | 권장 |
| 축전지 전압 | AI | V | sensor | `battery` ✓ `volt` ✓ | 권장 |
| 자동 / 수동 절환 | BI | — | sensor | `enable` ✓ | 필수 |
| 시동 실패 | BI | — | sensor | `fault` ✓ `critical` ✓ | 필수 |
| 누적 운전시간 | AI | h | sensor | `runtime` ★ | 권장 |

## 19-3 UPS · ESS · 태양광 · EV충전

**태그** `ups` ✓ · `ess` ✓ · `battery-storage` ✓ · `battery` ✓ · `pcs` ✓ · `inverter` ✓ · `rectifier` ✓ ·
`pv-array` ✓ · `microgrid` ✓ · `evse-equip` ✓ · `ac-evse-port` ✓ · `dc-evse-port` ✓ · `evse-dispenser` ✓ · `evse-cable` ✓

| 장비 | 핵심 spec 항목 |
|---|---|
| **UPS** | 정격 용량(kVA/kW), 방식(온라인 더블컨버전·라인인터랙티브), 백업 시간(분), 입·출력 전압·주파수, 배터리 형식·수량·설계수명, 효율(%), 바이패스 방식 |
| **ESS** | 정격 용량(kWh), 정격 출력(kW), 셀 화학(LFP·NMC), C-rate, 왕복 효율(%), 사이클 수명, 동작 온도범위, PCS 정격(kW)·계통연계 방식 |
| **태양광** | 모듈 정격(Wp)·수량·어레이 용량(kWp), 모듈 효율(%), 인버터 정격(kW)·MPPT 수·최대 효율(%), 계통 연계 전압, 경사각·방위각 |
| **EV충전** | 정격 출력(kW), 충전 방식(AC 완속·DC 급속), 커넥터 규격(AC 5핀·DC 콤보), 입력 전압, 통신 프로토콜(OCPP), 동시 충전 포트 수 |

| 포인트 | 종류 | 단위 | 태그 조합 | 적용 |
|---|---|---|---|---|
| 배터리 충전율 | AI | % | `stateOfCharge` ✓ | UPS·ESS |
| 충·방전 전력 | AI | kW | `elec-power` ✓ (부호로 방향) | ESS |
| 입력 / 출력 전압·전류 | AI | V / A | `volt` ✓ `elec-current` ✓ | UPS·PCS |
| 부하율 | AI | % | `load` ★ | UPS |
| 바이패스 / 배터리 운전 | BI | — | `ups` ✓ `run` ✓ | UPS |
| 셀 최고·최저 온도 | AI | ℃ | `battery` ✓ `temp` ✓ | ESS |
| 발전 전력 / 적산 발전량 | AI | kW / kWh | `pv-array` ✓ + `elec-power`·`elec-energy` ✓ | 태양광 |
| DC 전압 / 전류 | AI | V / A | `dc-elec` ✓ + `volt`·`elec-current` ✓ | 태양광·ESS |
| 일사량 | AI | W/㎡ | `solar-irradiance` ✓ | 태양광 |
| 모듈 온도 | AI | ℃ | `pv-array` ✓ `temp` ✓ | 태양광 |
| 충전 상태 | MSO | — | `evse-port` ✓ (대기/연결/충전/완료/고장) | EV충전 |
| 충전 전력 / 적산 충전량 | AI | kW / kWh | `evse-port` ✓ + `elec-power`·`elec-energy` ✓ | EV충전 |
| 커넥터 체결 | BI | — | `evse-cable` ✓ | EV충전 |

---

# 20. 조명 · 차양

**태그** `luminaire` ✓ · 비상조명 `emergency-light` ✓ · 블라인드 `blind` ✓ · 커튼 `curtain` ✓
**Brick** `Lighting_Equipment` / `Luminaire`

| spec 항목 | 단위 | 비고 |
|---|---|---|
| 정격 소비전력 | W | |
| 광속 | lm | |
| 광효율 | lm/W | |
| 색온도 | K | 3000·4000·5700 |
| 연색성 | Ra (CRI) | |
| 배광 각도 | ° | |
| 조광 방식 | — | 0–10V · DALI · PWM · 위상 |
| 정격 수명 | h | L70 기준 명기 |
| 보호등급 | IP | |
| (비상등) 예비전원 시간 | 분 | 법정 확보시간 |
| (블라인드) 구동 모터 출력·행정시간 | W / s | |

| 포인트 | 종류 | 단위 | 역할 | 태그 조합 | 등급 |
|---|---|---|---|---|---|
| 점멸 지령 | BO | — | cmd | `luminaire` ✓ `enable` ✓ | 필수 |
| 점등 상태 | BI | — | sensor | `luminaire` ✓ `run` ✓ | 필수 |
| 조광 지령 | AO | % | cmd | `dimming` ✓ | 권장 |
| 조도 (실측) | AI | lux | sensor | `illuminance` ✓ | 권장 |
| 색온도 지령 | AO | K | cmd | `color-temperature` ✓ | 선택 |
| 재실 감지 | BI | — | sensor | `occupancy` ✓ `motion-sensor` ✓ | 권장 |
| 그룹 / 씬 호출 | MSO | — | cmd | `luminaire` ✓ | 권장 |
| 비상등 자기진단 결과 | BI | — | sensor | `emergency-light` ✓ `fault` ✓ | 필수 |
| 블라인드 개도 | AO | % | cmd | `blind` ✓ `position` ★ | 선택 |
| 소비전력 | AI | kW | sensor | `elec-power` ✓ | 선택 |

---

# 21. 방재 (소방 · 제연 · 검지)

**태그** `firealarm-panel` ✓ · `sprinkler` ✓ · `pre-action` ✓ · `heat-detector` ✓ · `gas-detector` ✓ ·
`co-detector` ✓ · `alarm-bell` ✓ · `fire-extinguisher` ✓ · `fire-pump` ✓ · `smoke-damper` ✓ · `fire-damper` ✓
구역 태그 `fire-zone` ✓ · `smoke-zone` ✓ · 모드 `fire-mode` ✓

> ⚠ **원칙: BMS는 소방 설비를 감시만 하고 제어하지 않는다.** 자동화재탐지설비·소화설비는 법정 독립
> 계통이며 BMS의 제어 개입은 법적·안전상 허용되지 않는다. 카탈로그에서도 이 도메인 포인트는
> **`sensor` 역할만** 두고 `cmd`를 두지 않는 것을 원칙으로 한다(연동 제어는 소방 수신기가 수행).

| spec 항목 | 단위 | 대상 |
|---|---|---|
| 수신기 회로 수 | 회로 | 화재 수신기 |
| 감지기 종류·작동 온도 | — / ℃ | 정온·차동·광전·불꽃 |
| 경계구역 구성 | — | 층·구역 매핑 |
| 스프링클러 헤드 종류·방수량·작동온도 | — / LPM / ℃ | |
| 소화 배관 사용압력 | MPa | |
| 소화펌프 토출량·양정·출력 | LPM / m / kW | 주펌프·충압펌프 |
| 제연 풍량·정압 | CMH / Pa | 제연팬 |
| 방화·방연 댐퍼 구동방식 | — | 퓨즈·모터·복귀형 |
| 가스검지기 대상가스·검지범위·경보값 | — / ppm(%LEL) | |

| 포인트 | 종류 | 단위 | 역할 | 태그 조합 | 등급 |
|---|---|---|---|---|---|
| 화재 발생 (구역별) | BI | — | sensor | `fire-zone` ✓ `alarm` ✓ `critical` ✓ | 필수 |
| 감지기 동작 | BI | — | sensor | `heat-detector` ✓ `alarm` ✓ | 필수 |
| 수신기 고장·단선 | BI | — | sensor | `firealarm-panel` ✓ `fault` ✓ | 필수 |
| 경보 출력 상태 | BI | — | sensor | `alarm-bell` ✓ `run` ✓ | 권장 |
| 방화댐퍼 폐쇄 확인 | BI | — | sensor | `fire-damper` ✓ | 필수 |
| 제연댐퍼 개방 확인 | BI | — | sensor | `smoke-damper` ✓ `smoke-zone` ✓ | 필수 |
| 제연팬 운전 | BI | — | sensor | `exhaust-fan` ✓ `smoke-zone` ✓ `run` ✓ | 필수 |
| 소화펌프 운전 | BI | — | sensor | `fire-pump` ✓ `run` ✓ | 필수 |
| 소화배관 압력 | AI | MPa | sensor | `fire-pump` ✓ `pressure` ✓ | 권장 |
| 가스 농도 | AI | ppm / %LEL | sensor | `gas-detector` ✓ + `ch4`·`co` ✓ + `concentration` ✓ | 필수 |
| 일산화탄소 농도 | AI | ppm | sensor | `co-detector` ✓ `co-concentration` ✓ | 권장 |
| 누수 감지 | BI | — | sensor | `water-leak` ✓ `alarm` ✓ | 권장 |
| 화재 연동 운전 (설비측) | BI | — | sensor | `fire-mode` ✓ | 필수 |

---

# 22. 승강 설비

**태그** `elevator` ✓ · `escalator` ✓ · `movingWalkway` ✓ ← 부모 `verticalTransport` ✓
**Brick** `Elevator` / `Escalator`

| spec 항목 | 단위 | 비고 |
|---|---|---|
| 정격 적재하중 / 정원 | kg / 인 | |
| 정격 속도 | m/min | |
| 층수 / 정지층 / 행정거리 | 층 / 층 / m | |
| 구동 방식 | — | 권상(기어드·기어리스)·유압·MRL |
| 제어 방식 | — | VVVF·군관리 |
| 전동기 출력 | kW | |
| 도어 방식·개폐 시간 | — / s | 중앙개폐·측면개폐 |
| 비상 장치 | — | 정전시 구출운전·비상통화·자가발전 운전 |
| (에스컬레이터) 유효폭·경사각·양정 | mm / ° / m | |

| 포인트 | 종류 | 단위 | 역할 | 태그 조합 | 등급 |
|---|---|---|---|---|---|
| 현재 층 | AI | — | sensor | `elevator` ✓ `floor-position` ✓ | 필수 |
| 운행 방향 | MSO | — | sensor | `elevator` ✓ (정지/상승/하강) | 필수 |
| 운전 상태 | BI | — | sensor | `elevator` ✓ `run` ✓ | 필수 |
| 도어 개폐 | BI | — | sensor | `door` ✓ | 권장 |
| 고장 | BI | — | sensor | `elevator` ✓ `fault` ✓ `major` ✓ | 필수 |
| 갇힘 (구출 요청) | BI | — | sensor | `elevator` ✓ `alarm` ✓ `critical` ✓ | 필수 |
| 화재관제 운전 | BI | — | sensor | `elevator` ✓ `fire-mode` ✓ | 필수 |
| 비상전원 운전 | BI | — | sensor | `elevator` ✓ `generator` ✓ | 권장 |
| 점검 중 | BI | — | sensor | `elevator` ✓ `enable` ✓ | 권장 |
| 소비전력 | AI | kW | sensor | `elec-power` ✓ | 선택 |
| 운행 횟수 | AI | 회 | sensor | `runtime` ★ | 선택 |

---

# 23. 보안 · 출입 (BMS 연동 범위)

**태그** `access-control` ✓ · `card-reader` ✓ · `door-controller` ✓ · `cctv` ✓ · `ip-camera` ✓ ·
`ptz` ✓ · `nvr` ✓ · `dvr` ✓ · `vms` ✓ · `motion-sensor` ✓ · `door-sensor` ✓ · `proximity-sensor` ✓

> BMS는 상태 감시와 **화재 연동 개방**까지만 다룬다. 출입 권한 관리는 전용 시스템 영역이다.

| spec 항목 | 단위 | 대상 |
|---|---|---|
| 해상도 / 프레임 / 압축 | MP / fps / — | 카메라 (H.264·H.265) |
| 렌즈 초점거리·화각 | mm / ° | 카메라 |
| 야간 촬영·IR 거리 | m | 카메라 |
| 보호등급·동작온도 | IP / ℃ | 카메라 |
| 리더 인증 방식 | — | RF(125kHz·13.56MHz)·생체·모바일 |
| 도어 잠금 방식 | — | EM락·데드볼트·스트라이크 |
| 저장 채널 수·보존 기간 | ch / 일 | NVR |
| 전원 | V / PoE | |

| 포인트 | 종류 | 단위 | 역할 | 태그 조합 | 등급 |
|---|---|---|---|---|---|
| 도어 개방 상태 | BI | — | sensor | `door-sensor` ✓ `door` ✓ | 필수 |
| 강제 개방 경보 | BI | — | sensor | `access-control` ✓ `alarm` ✓ `major` ✓ | 필수 |
| 장시간 개방 경보 | BI | — | sensor | `access-control` ✓ `alarm` ✓ `warning` ✓ | 권장 |
| 출입 이벤트 | BI | — | sensor | `card-reader` ✓ | 권장 |
| 카메라 상태 | BI | — | sensor | `ip-camera` ✓ `fault` ✓ | 권장 |
| 움직임 감지 | BI | — | sensor | `motion-sensor` ✓ | 선택 |
| 화재 연동 비상 개방 | BO | — | cmd | `door-controller` ✓ `fire-mode` ✓ | 필수 |

---

# 24. 환경 · 실내공기질

**태그(물리량)** `co2-concentration` ✓ · `pm25-concentration` ✓ · `pm10-concentration` ✓ ·
`pm01-concentration` ✓ · `tvoc-concentration` ✓ · `ch2o-concentration` ✓ (포름알데히드) · `radon` ✓ ·
`o3-concentration` ✓ · `no2-concentration` ✓ · `nh3-concentration` ✓ · `voc` ✓ · `occupancy` ✓
**외기·기상** `weatherCond` ✓ · `wind-speed` ✓ · `wind-direction` ✓ · `precipitation` ✓ ·
`visibility` ✓ · `cloudage` ✓ · `atmospheric-pressure` ✓ · `solar-irradiance` ✓ · `feelsLike` ✓ · `wetBulb` ✓ · `dewPoint` ✓

| spec 항목 | 단위 | 비고 |
|---|---|---|
| 측정 대상·범위 | — / 물리량 단위 | |
| 정확도 | ± 단위 또는 % | |
| 응답 시간 (T90) | s | |
| 교정 주기 | 개월 | **유지보수 계획의 입력값** |
| 센서 방식 | — | NDIR(CO2)·광산란(PM)·PID(VOC)·전기화학 |
| 출력 | — | 4–20mA·0–10V·Modbus·BACnet |
| 사용 환경 | ℃ / %RH | |

| 포인트 | 종류 | 단위 | 역할 | 태그 조합 | 등급 |
|---|---|---|---|---|---|
| CO2 농도 | AI | ppm | sensor | `co2-concentration` ✓ | 필수 |
| PM10 / PM2.5 | AI | ㎍/㎥ | sensor | `pm10-concentration` ✓ / `pm25-concentration` ✓ | 필수 |
| TVOC | AI | ppb / ㎍/㎥ | sensor | `tvoc-concentration` ✓ | 권장 |
| 포름알데히드 | AI | ㎍/㎥ | sensor | `ch2o-concentration` ✓ | 선택 |
| 라돈 | AI | Bq/㎥ | sensor | `radon` ✓ | 선택 |
| 실내 온·습도 | AI | ℃ / % | sensor | `zone` ✓ `air` ✓ + `temp`·`humidity` ✓ | 필수 |
| 재실 인원 | AI | 인 | sensor | `occupancy` ✓ | 권장 |
| 외기 온·습도 | AI | ℃ / % | sensor | `outside-air` ✓ + `temp`·`humidity` ✓ | 필수 |
| 외기 풍속 / 풍향 | AI | m/s / ° | sensor | `wind-speed` ✓ / `wind-direction` ✓ | 권장 |
| 일사량 | AI | W/㎡ | sensor | `solar-irradiance` ✓ | 권장 |
| 강수 감지 | BI | — | sensor | `precipitation` ✓ | 선택 |

> 알람 기본값은 **실내공기질 관리법 시행규칙의 유지기준**을 따르되, 수치는 법령 원문으로 확정한다
> (본 조사에서 법령 원문 미확인 → `unverified`로 등록). 관제 실무에서 CO2 1,000 ppm이 널리 쓰인다.

---

# 25. 급배수 · 위생

**태그** `tank` ✓ · `rooftop-tank` ✓ · `septic-tank` ✓ · `expansion-tank` ✓ · `expansion-vessel` ✓ ·
`well` ✓ · `booster-pump` ✓ · `submersible-pump` ✓ · `strainer` ✓ · `header` ✓ · `level-sensor` ✓
**유체** `domestic-water` ✓ · `cold-water` ✓ · `hot-water` ✓ · `ground-water` ✓ · `wastewater` ✓ ·
`greywater` ✓ · `makeup-water` ✓ · `condensate` ✓
**수질** `ph` ✓ · `tds` ✓ · `chlorine` ✓ · `hardness` ✓ · `salinity` ✓ · `dissolved-oxygen` ✓

| spec 항목 | 단위 | 대상 |
|---|---|---|
| 수조 용량 / 재질 / 형식 | ㎥ / — | 저수조·고가수조 |
| 급수 방식 | — | 고가수조·압력수조·부스터(인버터) |
| 부스터 펌프 대수·토출압·유량 | 대 / kPa / LPM | |
| 배수 방식·펌프 사양 | — / LPM·m·kW | 오수·잡배수·우수 |
| 정수·소독 방식 | — | 염소·자외선 |
| 배관 재질·구경 | — / mm | |
| 급탕 저탕량·가열능력 | L / kW | |

| 포인트 | 종류 | 단위 | 역할 | 태그 조합 | 등급 |
|---|---|---|---|---|---|
| 수조 수위 | AI | % | sensor | `domestic-water` ✓ `level` ✓ | 필수 |
| 고수위 / 저수위 경보 | BI | — | sensor | `level` ✓ + `high-high` ✓ / `low-low` ✓ + `alarm` ✓ | 필수 |
| 급수 펌프 운전 | BI | — | sensor | `booster-pump` ✓ `run` ✓ | 필수 |
| 토출 압력 | AI | kPa | sensor | `domestic-water` ✓ `pressure` ✓ `discharge` ✓ | 필수 |
| 급수 유량 / 적산 | AI | ㎥/h / ㎥ | sensor | `domestic-water` ✓ + `flow` ✓ / `volume` ✓ | 필수 |
| 배수(오수) 수위 | AI/BI | % | sensor | `wastewater` ✓ `level` ✓ | 필수 |
| 배수 펌프 운전 | BI | — | sensor | `submersible-pump` ✓ `run` ✓ | 필수 |
| 누수 감지 | BI | — | sensor | `water-leak` ✓ `alarm` ✓ | 필수 |
| 잔류 염소 | AI | mg/L | sensor | `chlorine` ✓ | 권장 |
| pH / 전도도(TDS) | AI | — / µS/cm | sensor | `ph` ✓ / `tds` ✓ | 선택 |
| 급탕 온도 | AI | ℃ | sensor | `hot-water` ✓ `temp` ✓ | 필수 |

---
---

# 제3부 — 장비 공통 정의

여기부터는 장비마다 반복되는 것을 한 번만 정의한다. 앞의 포인트 표가 이것을 참조한다.

---

# 26. 상태 enum 표준 집합

다중상태(MSO/MSI/MSV) 포인트의 값 정의다. **DB에는 0-base로 정의하고 BACnet 매핑 시 +1 한다** —
BACnet 다중상태 객체의 `present-value`는 **1부터** 시작하기 때문이다.

| enum 집합 | 값 | 적용 |
|---|---|---|
| `RUN.STOP` | 0 정지 · 1 운전 | 전 장비 |
| `AUTO.MANUAL` | 0 수동(현장) · 1 자동(원격) | 전 장비 |
| `HVAC.MODE` | 0 정지 · 1 냉방 · 2 난방 · 3 송풍 · 4 제습 · 5 자동 | FCU·VRF |
| `AHU.MODE` | 0 정지 · 1 냉방 · 2 난방 · 3 송풍 · 4 외기냉방 · 5 예열 | AHU |
| `VAV.OPMODE` | 0 정지 · 1 냉방 · 2 난방 · 3 최소환기 | VAV |
| `FAN.SPEED` | 0 정지 · 1 약 · 2 중 · 3 강 · 4 자동 | FCU·VRF |
| `CHILLER.STATE` | 0 정지 · 1 기동중 · 2 운전 · 3 정지중 · 4 고장 · 5 국부운전 | 냉동기 |
| `BURNER.STAGE` | 0 소화 · 1 저연소 · 2 고연소 | 보일러 |
| `ELEV.DIR` | 0 정지 · 1 상승 · 2 하강 | 승강기 |
| `EVSE.STATE` | 0 대기 · 1 연결 · 2 충전중 · 3 완료 · 4 고장 | EV충전 |
| `ALARM.PRIORITY` | 0 정보 · 1 주의 · 2 경고 · 3 중대 · 4 긴급 | 전 알람 |
| `ALARM.STATE` | 0 정상 · 1 발생 · 2 확인 · 3 해제 · 4 복구 | 전 알람 |

`ALARM.PRIORITY`는 Haystack 태그 `info` ✓ · `warning` ✓ · `minor` ✓ · `major` ✓ · `critical` ✓ 에,
`ALARM.STATE`는 `acknowledged` ✓ · `cleared` ✓ · `resolved` ✓ 에 각각 대응한다.

---

# 27. 알람 · 트렌드 기본값 권장치

현장 데이터에는 알람 등급도 트렌드 주기도 사실상 비어 있다. **카탈로그가 이 기본값을 공급해야 한다.**
아래는 출발점이며 현장 튜닝 대상이다.

| 포인트 타입 | 알람 상한 | 알람 하한 | 데드밴드 | 트렌드 주기 | 비고 |
|---|---|---|---|---|---|
| 실내온도 | 30 ℃ | 15 ℃ | 0.5 ℃ | 300 s | 재실 기준 |
| 급기온도 | 40 ℃ | 5 ℃ | 0.5 ℃ | 300 s | 동결 하한 주의 |
| 외기온도 | 45 ℃ | −25 ℃ | 0.5 ℃ | 600 s | 센서 이상 판정용 |
| 냉수 출구온도 | 12 ℃ | 3 ℃ | 0.3 ℃ | 60 s | 동결 위험 |
| 냉각수 출구온도 | 38 ℃ | 20 ℃ | 0.5 ℃ | 300 s | |
| 온수 출구온도 | 95 ℃ | 40 ℃ | 0.5 ℃ | 300 s | |
| 실내습도 | 70 % | 20 % | 2 % | 600 s | |
| CO2 | 1,000 ppm | — | 20 ppm | 300 s | 법령 기준 확인 후 확정 |
| PM2.5 | 35 ㎍/㎥ | — | 2 ㎍/㎥ | 300 s | 법령 기준 확인 후 확정 |
| 급기 정압 | 설정+50 Pa | 설정−50 Pa | 5 Pa | 60 s | 설정값 상대 |
| 필터 차압 | 250 Pa | — | 10 Pa | 300 s | 교체 시점 판단 |
| 인버터 주파수 | 60 Hz | 0 Hz | 0.5 Hz | 60 s | |
| 전류 | 정격의 110 % | — | 정격의 1 % | 60 s | 모터 보호 |
| 전력 | 계약전력의 95 % | — | 1 % | 60 s | 피크 관리 |
| 적산 전력량·유량 | — | — | — | 900 s | 또는 변화 시 기록 |
| 수조 수위 | 95 % | 10 % | 2 % | 300 s | 고·저수위 별도 접점 |
| 상태 접점(BI) | — | — | — | **변화 시(COV)** | 주기 폴링 금지 |

원칙 3가지:
1. **상태 접점은 변화 시 기록(COV)** — 주기 폴링은 저장 공간만 먹는다.
2. **적산값은 주기를 길게** — 단조증가라 촘촘히 저장할 이유가 없다.
3. **동결·과열 등 안전 관련 상·하한은 데드밴드를 좁게** — 놓치면 장비가 손상된다.

---

# 28. 통신 프로파일 관례

## 28-1 BACnet 오브젝트 타입 선택 규칙

| 포인트 성격 | 오브젝트 타입 | BACnet enum | NEUROS 코드 |
|---|---|---|---|
| 계측값 (읽기) | Analog Input | 0 | 0 |
| 아날로그 지령 (쓰기) | Analog Output | 1 | 1 |
| 설정값·계산값 | Analog Value | 2 | 2 |
| 상태 접점 (읽기) | Binary Input | 3 | 3 |
| 개폐 지령 (쓰기) | Binary Output | 4 | 4 |
| 소프트 플래그 | Binary Value | 5 | 5 |
| 모드 상태 (읽기) | Multi-State Input | **13** | **6** |
| 모드 지령 (쓰기) | Multi-State Output | **14** | **7** |
| 모드 설정값 | Multi-State Value | **19** | **8** |

**⚠ 다중상태부터 번호가 어긋난다.** BACnet 표준은 13·14·19인데 NEUROS 내부 코드는 6·7·8이다
(BACnet 표준 enum 근거: [Chipkin](https://docs.chipkin.com/articles/bacnet-object-types-properties-reference/) ·
[OPC UA for BACnet](https://reference.opcfoundation.org/BACnet/v200/docs/10.4.21)).
**단일 canonical 코드 + 체계별 매핑 테이블**로 처리하고 왕복 무손실을 강제한다(`07-api-contract.md` SC-008).

## 28-2 BACnet 쓰기 우선순위 (priority array)

BACnet 출력 객체는 우선순위 1~16을 가지며 **낮은 번호가 우선**한다. 실무 관례:

| 우선순위 | 용도 |
|---|---|
| 1 | 수동 생명안전 (Manual-Life Safety) |
| 2 | 자동 생명안전 (Automatic-Life Safety) |
| 5 | 임계 장비 제어 |
| **8** | **수동 오퍼레이터** — 관제 화면의 수동 조작 |
| **16** | **기본 자동 제어** — 스케줄·시퀀스 |
| (해제) | Relinquish Default — 전 우선순위 해제 시 되돌아가는 값 |

BMS 자동 제어는 16(또는 10), 사람의 수동 개입은 8로 쓴다. **8로 쓴 값을 해제하지 않으면 자동 제어가
먹지 않는다** — 현장에서 "제어가 안 먹는다"의 최다 원인이다.

## 28-3 Modbus 레지스터 관례

| 영역 | 주소 표기 | 접근 | 용도 |
|---|---|---|---|
| Coil | `0xxxx` | 읽기/쓰기 (비트) | 접점 지령 |
| Discrete Input | `1xxxx` | 읽기 (비트) | 접점 상태 |
| Input Register | `3xxxx` | 읽기 (16bit) | 계측값 |
| Holding Register | `4xxxx` | 읽기/쓰기 (16bit) | 설정값·지령 |

`40001` = holding register **주소 0**이다(1-base 표기와 0-base 주소의 차이 — 오프매핑 최다 원인).
모델 통신맵에는 반드시 함께 기록한다: **데이터형(16/32bit, 부호 유무) · 워드 순서(big/little endian) ·
스케일 · 오프셋 · 단위**. 32비트 값은 레지스터 2개를 쓰며 순서가 벤더마다 다르다.

## 28-4 통신 파라미터 · 폴링 주기

| 항목 | 관례 |
|---|---|
| BACnet MS/TP | 보율 9.6k~76.8k, MAC 0~127, Max Master 설정, 종단저항 양단 |
| Modbus RTU | 보율 9600·19200·38400, 패리티 N/E/O, 리피터 없이 최대 32노드 |
| BACnet/IP | UDP 47808(0xBAC0), BBMD/Foreign Device 설정 |
| 폴링 주기 | 상태 1~5 s · 계측 5~30 s · 적산 60~300 s |

---

# 29. 제어 시퀀스 참조

정본은 **ASHRAE Guideline 36-2024**(High-Performance Sequences of Operation for HVAC Systems)다.
2021판 대비 개정 23건이 반영됐고 2026년 2월 Addendum a가 나왔다
([ANSI Webstore](https://webstore.ansi.org/standards/ashrae/ashraeguideline362024) · [ASHRAE](https://ashrae.org/G36)).

**유료 표준이므로 원문·표를 복제하지 않는다.** 카탈로그에는 시퀀스 이름 · 조항 참조 · 자체 요약 ·
파라미터만 저장한다(`05-prd.md` FR-016).

| 시퀀스 | 적용 장비 | 카탈로그가 보유할 파라미터 |
|---|---|---|
| 다구역 VAV 공조기 제어 | AHU | 급기온도 리셋 범위, 급기정압 리셋 범위, 외기냉방 사용 조건, 최소외기량 |
| VAV 단말 — 냉방전용 | VAV | 최대·최소 풍량, 냉방 P·I 파라미터, 데드밴드 |
| VAV 단말 — 재열형 | VAV | 위 + 재열 개시 조건, 난방 최대풍량 |
| VAV 단말 — 팬파워드(직렬·병렬) | VAV(FP) | 위 + 팬 기동 조건 |
| 이중덕트 · CAV 단말 | CAV | 혼합비, 최소풍량 |
| 냉수 플랜트 | 냉동기·펌프·냉각탑 | 대수제어 기준, 냉수온도 리셋, 냉각수온도 리셋, 최소유량 |
| 존 습도 제한·제습 (2024 신설 3종) | AHU | 습도 상한, 급기온도 리셋 연동 |
| 외기오염 모드 (2024 신설) | AHU | 오염물질 임계치, 외기냉방 자동 해제 |

각 시퀀스는 **장비 분류에 매달고**(예: `HVAC.AIR.AHU` → 다구역 VAV AHU 시퀀스), 적용 시 파라미터
기본값을 함께 주입한다. **조항 번호는 G36 구매본을 대조해 확정한다**(본 조사 미보유).

---
---

# 제4부 — 모델 spec 채우기

# 30. 모델 등록 템플릿과 실제 예시

## 30-1 등록 템플릿

모델 1건은 5블록으로 구성된다. **모든 값 행에 근거(evidence) 또는 `unverified` 표시가 필수**다.

```
① 식별       제조사 / 모델코드 / 표시명 / 분류코드 / equip 태그 / 상태(active|eol)
② 정격 스펙   [항목 | 값 | 단위 | 조건 | 근거]   ← 3절의 정격·설계·조건부 구분 적용
③ 통신       [프로토콜 | 역할 | 기본 포트·보율 | 비고]
④ 모델 포인트 [벤더 포인트명 | 표준 포인트 타입 | 오브젝트/레지스터 | 데이터형 | 스케일 | 단위 | 쓰기 | 범위]
⑤ 근거 문서   [종류 | 제목 | 발행자 | 문서버전 | 발행일 | 경로 | SHA-256 | 페이지]
```

## 30-2 실제 예시 — Danfoss VLT® HVAC Basic Drive FC 101

**① 식별** — 제조사 `Danfoss` · 모델코드 `FC-101` · 분류 `HVAC.AUX.VFD` · equip 태그 `vfd` ✓ · 상태 active

**② 정격 스펙**

| 항목 | 값 | 단위 | 조건 | 근거 |
|---|---|---|---|---|
| 정격 용량 (200–240 V) | 0.25–45 | kW | 3상 | Fact Sheet |
| 정격 용량 (380–480 V) | 0.37–90 | kW | 3상 | Fact Sheet |
| 정격 용량 (525–600 V) | 2.2–90 | kW | 3상 | Fact Sheet |
| 공급 전압 허용범위 | ±10 | % | — | Fact Sheet |
| 공급 주파수 | 50 / 60 | Hz | — | Fact Sheet |
| 변위 역률 (cos φ) | > 0.98 | — | near unity | Fact Sheet |
| 출력 전압 | 0–100 | % | 공급 전압 대비 | Fact Sheet |
| 출력 주파수 | 0–400 | Hz | 개·폐루프 | Fact Sheet |
| 가감속 시간 | 1–3600 | s | — | Fact Sheet |
| 보호등급 | IP20 / IP21(UL Type 1, 옵션 키트) / IP54 | — | — | Fact Sheet |
| 최대 주위온도 | 50 | ℃ | 강제공랭 불요 | Fact Sheet |
| 내장 EMC 필터 등급 | C1 / C2 / C3 | — | C3 기본 내장, C1·C2 옵션 | Fact Sheet |
| 고조파 대책 | DC 초크 내장 | — | EN 61000-3-12 충족 | Fact Sheet |
| 옵션 고조파 필터 | 5 / 10 | % THDi | 옵션 | Fact Sheet |
| 에너지 절감 | 최대 25 | % | — | Fact Sheet (**제품 페이지는 50% — 출처 불일치, 확인 필요**) |
| **과부하 내량** | — | — | — | **`unverified`** — Fact Sheet 미기재, Design Guide 필요 |
| **용량별 정격 출력전류** | — | A | 용량별 | **`unverified`** — Design Guide 필요 |

**③ 통신** — 표준 내장(옵션 불요): **BACnet MS/TP · Modbus RTU · FC Protocol · N2 Metasys ·
FLN Apogee** (Fact Sheet). 물리계층 RS-485.

**④ 하드웨어 I/O** — 모델 포인트 매핑의 물리적 상한

| I/O | 수량 | 사양 | 근거 |
|---|---|---|---|
| 디지털 입력 | 4 | PNP/NPN 선택, 0–24 V DC | Fact Sheet |
| 아날로그 입력 | 2 | 0–10 V 또는 0/4–20 mA (스케일 가능) | Fact Sheet |
| 아날로그 출력 | 2 | 0/4–20 mA (디지털 출력 겸용) | Fact Sheet |
| 릴레이 출력 | 2 | 240 V AC 2 A / 400 V AC 2 A | Fact Sheet |

**⑤ 근거 문서**

| 종류 | 제목 | 발행자 | 문서번호 | 발행 | 경로 |
|---|---|---|---|---|---|
| catalog | VLT® HVAC Basic Drive FC 101 Fact Sheet | Danfoss Drives | DKDD.PFP.100.A4.02 | 2017-07 | [files.danfoss.com](https://files.danfoss.com/download/Drives/DKDDPFP100A402_HVAC_Basic.pdf) |
| manual | VLT® HVAC Basic Drive FC 101 Design Guide | Danfoss Drives | AJ275648114271 | — | [assets.danfoss.com](https://assets.danfoss.com/documents/latest/514925/AJ275648114271en-001201.pdf) — **미확보** (과부하·전류표 출처) |

> 저장 규칙(D-008): 원본 PDF는 보관하지 않고 **경로 + SHA-256 + 발행자·문서번호·발행일**만 등록한다.

## 30-3 이 예시가 보여주는 것

1. **근거가 있는 값과 없는 값이 한 표에 공존한다** — 과부하 내량은 비워 두고 `unverified`로 남겼다.
   추정해서 채우면 그 값이 현장 장비 설정으로 흘러간다.
2. **출처가 갈리면 그 사실을 기록한다** — 에너지 절감이 제품 페이지 50% / Fact Sheet 25%로 다르다.
   하나를 고르는 게 아니라 **불일치를 남기고** 1차 문서를 우선한다.
3. **하드웨어 I/O 수량이 모델 포인트의 상한**이다 — AI 2점짜리 인버터에 AI 포인트 5개를 매핑하는 계획은
   적용 미리보기에서 걸러져야 한다.
4. **통신 지원 목록이 곧 적용 가능 여부**다 — 이 모델은 BACnet MS/TP 내장이라 게이트웨이 없이 연동된다.

---
---

# 제5부 — 포인트 규모의 실제

# 31. 왜 앞의 표는 포인트가 적은가 — 3계층 구조

5~25절의 「표준 포인트」 표는 **장비 종류의 최소 공통 프로파일**이다. 모델이 무엇이든 항상 있는 것만
추린 것이라 적을 수밖에 없다. **실제 현장 포인트 수는 이것의 3~10배**다. 층이 다르기 때문이다.

| 계층 | 무엇 | 개수 규모 | 어디서 오나 |
|---|---|---|---|
| **L1 표준 포인트 타입 사전** | 재사용 단위. "급기온도"라는 개념 1건 | **250~300종** | 이 조사 |
| **L2 장비 분류 프로파일** | 분류별 필수·권장·선택 등급 | 계열당 10~25 → 계 **약 300행** | 이 조사 (5~25절) |
| **L2.5 부속 전개** | 장비 = 부속 조합. 부속마다 자기 포인트 | **장비 1대당 30~120점** | 장비 구성(부속 목록) |
| **L3 모델 통신맵** | 그 모델이 실제 노출하는 전체 오브젝트 | **모델 1건당 30~300점** | 제조사 통신 문서 |

**앞의 표는 L2다.** 규모가 커지는 지점은 L2.5(부속 전개)와 L3(모델 통신맵)이고, 그 둘은 각각
**장비 구성**과 **제조사 문서**가 있어야 채워진다.

---

## 31-1 실측 — 냉동기 모델 1건이 몇 점인가

Trane의 공개 통합 포인트 리스트를 직접 받아 세었다.

| 문서 | 대상 | 확인 결과 |
|---|---|---|
| [Symbio™ 800 Integration Points List — BACnet ACSA (UC800)](https://elibrary.tranetechnologies.com/public/commercial-hvac/Literature/Points%20List/BAS-PTS026A-EN_12062024.pdf) (2024-12-06) | 흡수식 냉동기 + UC800 컨트롤러 | 오브젝트 인스턴스 **30001 ~ 30167** 연속 대역 → **160점 이상** |
| [Symbio™ 800 — BACnet CGAM (CH530)](https://elibrary.tranetechnologies.com/public/commercial-hvac/Literature/Points%20List/BAS-PTS027A-EN_12062024.pdf) | 공랭 스크류 | 기종별 **별도 리스트** |
| [Symbio™ 800 — BACnet CTV-Simplex (UC800)](https://elibrary.tranetechnologies.com/public/commercial-hvac/Literature/Points%20List/BAS-PTS029A-EN_12062024.pdf) | 원심(터보) | 기종별 **별도 리스트** |

실제 포인트명 일부(문서에서 추출): `ActiveChilledWaterSetpoint` · `ActiveDemandLimitSetpoint` ·
`EvaporatorEnteringWaterTemperature` · `EvaporatorLeavingWaterTemperature` · `CapacityControlModeStatus` ·
`ChillerRunningState` · `DischargeTemperatureCkt1/Ckt2` · `LiquidLineTemperatureCkt1/Ckt2` ·
`LiquidLinePressureCkt1/Ckt2` · `Circuit1/2LatchingAlarm` · `EvaporatorPump1/2FaultInput` ·
`EvapPumpInv1RunCommand` · `FreeCoolingActive` · `NoiseReductionCommand` · `HeatRecoveryActive` ·
`EmergencyStopUnitStatus` · `ExternalHeatRecoverySetpoint` · `FrontPanelDemandLimitSetpoint`

**→ 내가 9절에 적은 냉동기 15점은 최소 공통이고, 모델 1건의 실제는 160점 이상이다.**
게다가 **같은 제조사라도 기종(흡수식·스크류·터보)마다 포인트 리스트가 다르다.**
회로(Ckt1/Ckt2)·압축기·펌프가 늘면 그만큼 곱해진다.

---

## 31-2 부속 전개 — 공조기 1대를 끝까지 펼치면

AHU는 단일 장비가 아니라 **부속의 조합**이다. 부속마다 공통 포인트(운전·지령·고장·자동수동·운전시간)를
갖는다. 중대형 공조기 1대 기준:

| 부속 | 수량 | 부속당 포인트 | 소계 | 주요 포인트 |
|---|---|---|---|---|
| 급기팬 + VFD | 1 | 12 | 12 | 운전·기동정지·고장·자동수동·운전시간·주파수지령·현재주파수·전류·전력·적산전력·트립코드·방열판온도 |
| 환기팬 + VFD | 1 | 12 | 12 | 위와 동일 |
| 배기팬 + VFD | 0~1 | 12 | 12 | 위와 동일 |
| 냉수코일 | 1 | 5 | 5 | 밸브개도·밸브피드백·입구수온·출구수온·유량 |
| 온수코일 | 1 | 5 | 5 | 위와 동일 |
| 예열코일 | 0~1 | 5 | 5 | 위와 동일 |
| 가습기 | 1 | 4 | 4 | 지령·운전상태·고장·급수 |
| 필터 (프리+미디엄) | 2 | 2 | 4 | 차압·막힘경보 |
| 댐퍼 (외기·환기·배기·혼합) | 4 | 3 | 12 | 개도지령·개도피드백·개폐확인 |
| 공기 계측 | — | — | 12 | 급기·환기·외기·혼합 온도 / 급기·환기·외기 습도 / 급기정압 / 급기·환기 풍량 / CO2 |
| 안전·인터록 | — | — | 5 | 동결방지·급기고온·정압고압·필터종합경보·화재연동 |
| 설정값 (AV) | — | — | 7 | 급기온도SP·급기정압SP·습도SP·CO2SP·최소외기량·외기냉방 활성조건·스케줄 |
| 상태·모드 | — | — | 4 | 운전모드·절기모드·원격현장·스케줄상태 |
| **합계** | | | **≈ 99** | |

**5절의 23점 → 부속을 끝까지 전개하면 약 99점.** 여기에 벤더 컨트롤러 고유 포인트(L3)가 더 붙는다.

---

## 31-3 계열별 규모 대조

| 장비 계열 | 현재 표(L2 최소공통) | 부속 전개(L2.5) | 모델 통신맵(L3) |
|---|---|---|---|
| 공조기 AHU | 23 | **≈ 99** | 벤더 컨트롤러 100~300 |
| 냉동기 | 15 | ≈ 40 (회로·압축기·펌프 전개) | **160+ (Trane UC800 실측)**, 기종별 상이 |
| 냉각탑 | 12 | ≈ 30 (팬 2~4대·밸브·수위·수질) | 50~ |
| 보일러 | 11 | ≈ 30 (버너·순환펌프·안전장치) | 50~150 |
| 열교환기 | 11 | ≈ 20 | 30~ |
| 펌프 (인버터 포함) | 7 | ≈ 15 | 30~ |
| 송풍기 (인버터 포함) | 5 | ≈ 15 | 30~ |
| VAV | 14 | 14~20 | 20~40 (단말 컨트롤러) |
| FCU | 10 | 12~15 | 15~30 |
| VRF 실내기 | 11 | 11~15 | 게이트웨이 15~40 / 실내기 대수만큼 배수 |
| 인버터 VFD | 12 | 12 | **통신 가능 파라미터 수백**, 실사용 매핑 10~20 |
| 수변전 | 35 | 회로 수만큼 배수 (피더 20회로 = 20×8) | 계전기·미터 100~300 |
| 승강기 | 11 | 대수만큼 배수 | 벤더 인터페이스 20~50 |

**두 가지가 곱셈으로 작동한다.**
① **부속 수** — 팬이 2대면 팬 포인트가 2배, 냉동기 회로가 2개면 회로 포인트가 2배.
② **인스턴스 수** — VAV 300대짜리 건물은 VAV만 300×20 = 6,000점. 건물 전체 포인트의 과반이 단말이다.

---

## 31-4 모델은 몇 개인가

계열마다 다르지만 구조는 같다: **제조사 수 × 모델 계열 수 × 용량 라인업**.

| 축 | 실태 |
|---|---|
| 제조사 | 계열당 국내 유통 기준 5~20개사 (예: 냉동기 = Trane·Carrier·York·LG·삼성·센추리·경원 등) |
| 모델 계열 | 제조사당 3~10 (예: Trane 냉동기 = ACSA·CGAM·CVHF·RTAC·RTWD…) |
| 용량 라인업 | 계열당 5~30 (동일 통신맵, spec 값만 다름) |

**중요한 절약 지점**: 같은 모델 계열이면 **용량만 달라도 통신맵(L3)은 같다.**
→ L3는 **모델 계열 단위로 1건**만 만들고, 용량별 차이는 L2의 spec 값(정격 용량·전류·유량)으로 흡수한다.
Trane이 기종(ACSA/CGAM/CTV)마다 points list를 따로 내는 것도 같은 이유다 —
**기종이 바뀌면 통신맵이 바뀌고, 용량만 바뀌면 안 바뀐다.**

## 31-5 그래서 카탈로그 총량은

| 대상 | 건수 추정 |
|---|---|
| L1 표준 포인트 타입 | 250~300종 (현재 조사 236행 → 중복 제거·보강) |
| L2 분류 프로파일 | 19계열 × 10~35 ≈ **300~400행** (현재 236행) |
| L3 모델 통신맵 | **모델 계열 1건당 30~300점.** 계열 50건 확보 시 **3,000~10,000행** |

**카탈로그의 부피는 L3가 만든다.** 그리고 L3는 조사로 지어낼 수 없고 **제조사 통신 문서를 받아야** 채워진다.
근거 강제(FR-021)와 evidence 메타(FR-020)가 있는 이유가 이것이다.

## 31-6 L3를 채우는 현실적 경로

| 경로 | 획득 방법 | 난이도 |
|---|---|---|
| **제조사 공개 points list** | Trane elibrary처럼 공개된 PDF (위 3건 확보 완료) | 낮음 — 즉시 가능 |
| 제조사 통신 매뉴얼 요청 | 대리점·기술지원 창구 | 중간 |
| **BACnet 실장비 스캔** | 현장 컨트롤러에서 오브젝트 목록 자동 수집 | 낮음 — **이미 Niagara export 보유** |
| Modbus 통신맵 | 벤더 문서 필수 (스캔으로 의미 추론 불가) | 높음 |
| 기존 현장 포인트리스트 | 의미·단위가 없어 **역추론 불가** | 참고용만 |

**BACnet 실장비 스캔이 가장 빠르다** — 오브젝트 타입·인스턴스·이름·쓰기가능 여부가 그대로 나온다.
다만 **의미(어떤 표준 포인트 타입인가)는 사람이 확정**해야 한다.

---

## 31-7 이 절이 바꾸는 것

1. **앞의 표를 "완성된 포인트 목록"으로 읽으면 안 된다.** L2 최소 공통 프로파일이다.
2. 카탈로그 스키마는 **L2와 L3를 분리해서** 담아야 한다 — `bes_category_point_profile`(L2)와
   `bes_model_point`(L3)가 이미 그렇게 분리돼 있다(`07-api-contract.md`).
3. **부속 전개(L2.5)를 스키마가 지원해야 한다** — 장비가 부속을 참조하고(`equipRef`), 부속마다 포인트가
   붙는 구조. 지금 스키마는 장비-포인트 1계층이라 **AHU 안의 팬 2대를 구별할 수 없다.** → 보완 필요.
4. **다음 작업의 실질은 L3 수집**이다. 조사가 아니라 문서 확보와 스캔이다.
