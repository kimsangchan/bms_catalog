<!-- NEXT-ACTION:START -->
## ▶ 지금 할 일 (새 세션은 이 블록부터 — SessionStart 훅이 자동 주입)

**2026-09-08 인수인계 (5차).** `validate.py` 오류 0 · 모델 **158** · 판 **140** · 오브젝트 **37,385점** ·
형번 확정본 **31모델**. 시험은 **[C] 1건만 빨강**(Trane Precedent — 일부러 둔 것).

### 이번에 끝낸 것 — 삼성 정격을 전용 판독기로 다시 읽었다

범용 추출(specs.py)이 낸 표 127개·4,088행은 **값이 뭉개져 있었다.** 사용자가 짚은 그대로,
`DVM S (프리미엄)` 표의 한 칸에 `"23.0 26.5 21.7"` 처럼 **3개 행의 값이 함께** 들어 있었다.

| | 전 | 후 |
|---|---|---|
| 표 / 행 | 127 / 4,088 | **117 / 4,349** |
| 형번 | — | **407** (실외기 335 · 실내기 72) |
| 이웃 수치가 그냥 붙은 칸 | 다수 | **0** |
| 빈 값 | — | **0 %** |

`ingest_samsung_ratings.py`. 원문 구조를 **추측하지 않는다** — 이 PDF 는 셀 눈금선을
얇은 채움 사각형(`get_drawings()` 의 `type='f'`)으로 그리고 **병합된 칸에는 그 선이 없다.**

- ⚠ **값 칸에는 행 구분선이 아예 없다.** 대분류 묶음(성능 3행)을 상자 하나로만 긋는다.
  '선이 없으면 병합' 을 값 열에 그대로 쓰면 find_tables 와 **똑같이** 뭉갠다 —
  세로 병합 판정은 **라벨 열에만** 쓰고 값 열은 늘 한 행씩 읽는다.
- ⚠ 병합 칸은 **위로도** 걸어 올라가야 한다. 아래로만 걸으면 묶음의 마지막 행이
  한가운데 앉은 글자를 놓친다(실제로 '저온 난방' 행에서 대분류 '성능' 이 사라졌다).
- ⚠ 좌·우 두 표를 **x 간격으로 가르면 안 된다**(표 사이 여백 48pt < 값 칸 피치 72pt).
  쪽 한가운데(x=615)로 자른다. 반쪽 안에서 위·아래로 붙은 표는 **머리글이 나올 때마다** 가른다.
- 검산: 표에서 **떨어진 자리**에 있는 `용량` 행과 `성능·냉방` 행이 같아야 한다 →
  **101/101 통과**. 격자가 한 칸이라도 어긋나면 깨진다.
- 규칙 4 대로 **그림으로** 되짚었다 — p27·p46 을 렌더해 눈으로 읽고 **312칸 대조, 불일치 0**.

담지 않은 것(조판이 달라 gap 에 적었다): ERV 환기 p61~63(열이 형번이 아니라 풍량 구분) ·
DVM AHU p50(라벨 4단·한 열에 표 둘) · Hydro Unit p59(한 열에 형번 둘).

### 함께 정리한 것

- **규칙 0**: 요구 프로파일 `e5.pac` → **`e8.vrf`** 로 옮겼다(`catPrefix` 를
  `HVAC.AIR.VRF` 로 적었는데 실제 cat 은 `HVAC.AIR.TERMINAL.VRF` 라 **매칭 0** 이었다).
  `unit-schema` 에 **클래스 e8** 과 **feature 10개**를 새로 등재했다
  (lowTempHeatingCapacity · heatingPower · lowTempHeatingPower · eera ·
  energyEfficiencyGrade · ratedRunningCurrentCooling/Heating · maxRunningCurrent ·
  refrigerantType · tonsRefrigeration). `equip-templates.json` · `test_datasets` 도 같이 옮겼다.
- **확정본 407형번** — `data/units/samsung-mim-b17bn-bacnet-gateway.json`.
  ⚠ 원문이 쪽마다 표기를 달리 쓴다('통합 냉방 소비전력' ↔ '소비전력 (정격) 냉방',
  '본체 치수' ↔ '본체치수'). 한 쪽만 보고 패턴을 박으면 나머지 쪽 형번이 **조용히 빈다** —
  처음에 55/64 쪽만 걸렸다. 라벨을 전수로 뽑아 변형을 다 덮었다(`SAMSUNG_VRF_PICKS`).
- **단위 파싱**: `datasets.label_unit` 이 한글 라벨의 끝 괄호를 단위로 읽게 했다(kg·A·kW…).
  ⚠ 영문에 같은 규칙을 쓰면 `dB(A)` 의 A, `Dry Weight lbs (kg)` 의 kg 을 단위로 잘못 읽는다 —
  **한글이 든 라벨에만** 적용한다. LS H100 확정본도 덕분에 단위가 찼다.
- **실외기 정격을 따로 모델로 만들지 않는다.** 카탈로그 관례가 그렇다 — 정격을 가진
  모델 57건 중 **52건이 오브젝트(통신 매뉴얼)와 정격(제품 카탈로그)을 다른 문서에서
  끌어와 한 modelId 에 합친다.** `spec-map.json` 의 고아 예약 둘
  (`samsung-dvm-s-outdoor-unit` · `lg-multi-v-5-outdoor-unit`)을 기존 게이트웨이로 돌리고
  `_실외기정격` 주석에 근거를 남겼다.
- **LG 시험 3건을 고쳤다** — 지난 세션의 Modbus-TCP 판 99점 취입이 BACnet 전제로 쓰인
  단언을 깼는데 그때 확인을 안 했다(규칙 3 위반). 판을 갈라 보게 하고,
  Modbus 쪽도 `test_modbus_tcp_side_is_a_separate_set_of_interfaces` 로 함께 세웠다.

### 이번에 함께 끝낸 것 — e8.vrf 템플릿 22행 (2026-09-08)

`e5.pac` 시절부터 **0행**으로 비어 있던 프로파일을 채웠다. 근거는 국내 VRF 게이트웨이
**5모델 619점**을 실제로 훑은 것이다(LG AC Smart 264 · 삼성 MIM-B17BN 264 ·
JCI SI-VRFCBN02 실내기 32·실외기 26 · Daikin DMS502B71 33).

**"모델을 몰라도 템플릿을 만들 수 있다"는 말이 왜 맞는가** — 개념은 같고 이름만 다르다.

| 개념 | Daikin | JCI | LG | 삼성 |
|---|---|---|---|---|
| 실내온도 | `RoomTemp` | `ZN-T` | `RoomTemp_XXX` | `AC_RoomTemp_xx` |
| 설정온도 | `TempAdjust` | `ZN-SP` | `SetTempStatus_XXX` | `AC_Temp_Set_xx` |
| 운전/정지 | `StartStopCommand` | (없음) | `StartStopCommand_XXX` | `AC_Power_xx` |
| 에러 코드 | `MalfunctionCode` | `ALARM-CODE` | `MalfunctionCode_XXX` | `AC_Error_Code_xx` |

화면(왼쪽 열)은 모델 없이 설계되고, 모델은 **주소를 붙일 때만** 필요하다. 그 흡수를
각 행의 `match.include` 가 한다. 씨앗은 `data/equips/e8.json` 의 손으로 쓴 11행이었고
실측 노출로 22행이 됐다 — **운전/정지·운전상태·적산 전력량·배관온도·EEV 개도·외기온도가
빠져 있었다. 전력 계산의 뼈대인데 없었다.**

⚠ **정규식만 믿으면 안 된다. 집힌 것을 하나씩 봐야 한다** — 오답이 여덟 있었다:

| 행 | 잘못 집은 것 | 왜 틀렸나 |
|---|---|---|
| 적산 전력량 | `GasTotalPower · 적산 가스` | 가스다, 전력이 아니다 |
| 적산 전력량 | `AC_Baseline_kWh` | 기준값이다, 적산값은 `Period` 쪽 |
| 소비전력 | `AccumPowerStatus_XXX` | 적산이다, 순시가 아니다 |
| 풍량 단계 | `FANSPD-LO · 리모컨 풍량 잠금` | 잠금이다, 지령이 아니다 |
| 풍향 | `LOUVER-LO · 리모컨 루버 잠금` | 〃 |
| 압축기 운전율 | `INV-HRS · 압축기1 운전시간` | 누적 시간이다, 운전율이 아니다 |
| 급기 온도 | `InverterDischargeTemp_XXX` | 압축기 **냉매** 토출이다, 급기(공기)가 아니다 |
| 운전 모드 | `RemoteControlAirConModeSet` | 리모컨 허용이다, 모드 지령이 아니다 |

⚠ **밑줄은 낱말 문자다.** `kwh` 가 `AC_Period_kWh_xx` 를 못 잡는다 — 국내 게이트웨이
이름은 밑줄로 이어 붙는다. `` 를 빼야 걸린다.

⚠ **매처가 보는 글자는 이름 + 비고다.** Daikin 의 `Alarm · 알람` 은 비고가
`Normal / Malfunction` 이라 `malfunction` 하나로 에러 코드 행에 걸렸다 — 그건 코드가
아니라 **상태 열거**다. '코드' 가 가까이 붙은 이름만 받게 고쳤다.

**규칙 ⑦ Haystack 대조**(`haystack.py --diff e8`): 표준에 짝이 있는 행 **10**, 애매 3,
우리에만 있는 행 9(냉매측·전력·제상·통신은 VRF proto 에 자리가 없다). 대조가 값을 했다 —
`운전 모드`·`필터 청소 신호` 가 '표준에 없음' 으로 떨어져 있었는데 **우리 태그 낱말이 틀린
것**이었다(`airfilter` → 표준은 `filter`). 고치니 짝을 찾았다.

판별 매칭 결과(`data/datasets/model-mappings.json`):
LG 실내기 판 **12/22** · Daikin 12/22 · 삼성 11/22 · JCI 실내기 11/22 · JCI 실외기 6/22.
`소비전력` 은 **0/5** 다 — 게이트웨이가 순시 전력을 안 낸다. 지우지 않고 `appliesWhen` 에
"별도 전력계(e19)나 형번별 정격표에서 온다" 고 적었다(미충족이 아니라 여기서 나올 값이 아님).

### ⚠ 우선순위를 벗어났다 — 2026-09-08 사용자가 지적, 바로잡는다

**정본 순서는 `10-site-driven-priority.md` 「우선순위」다**(현장 물량 기준):

| 순위 | 설비 | 현장 | 카탈로그 |
|---|---|---|---|
| 1 | **팬(급·배기, 인버터)** | 305대 | 4모델 |
| 2 | **공조기·외조기** | 215 + 27대 | 9모델 · **0모델** |
| 3 | VRF/DVM | 주력 계통 | 2모델 |
| 4 | 펌프 | 96대 | 7모델 |
| 5 | 열교환기·냉각탑 | 26 · 16대 | **0모델** |
| 6 | ⬇ **냉동기는 멈춘다** | 12대 | 70모델 14,520점 (과잉) |

어긴 것:
- ❌ **YORK 냉동기 Engineering Guide 86건 수집**(소스 `jci-chiller-eg`) — 이것이 바로
  **6순위, "멈춘다"고 적어 둔 것**이다. 파일은 받아 뒀지만(`data/raw/JCI_EG_*`, gitignore
  라 저장소 비용 0) **취입하지 않는다.** 냉동기를 다시 열 이유가 생기기 전까지 그대로 둔다.
- ⚠ **Belimo 19모델 정격** — 우선순위 목록에 없다. 필드기기(댐퍼·밸브 액추에이터)라
  현장에 붙기는 하나 현장 VAV 벤더는 나라컨트롤(후보)이지 Belimo 가 아니다.
  이미 끝냈고 오류 0 이라 되돌리지 않지만, **다음 것을 고를 때 기준이 되면 안 된다.**

원인: 2026-09-07 정격 결손 전수 조사가 낸 순위는 **카탈로그 내부 기준**
(정격이 빈 모델이 물고 있는 오브젝트 점수)이었다. 그건 "우리 데이터의 구멍이 어디 큰가"
이지 **"현장에 무엇이 많은가"가 아니다.** 두 순위를 섞어 읽었다.

### ▶ 되돌린 다음 할 일 (현장 순위대로)

1. **[1순위 팬·인버터] Danfoss FC 101 형번별 정격 확정본** — 현장 인버터 222대의 유력
   후보이고 오브젝트 410점은 이미 들어와 있는데 **형번별 정격 확정본이 없다.**
   원문에는 다 있다(Table 10~19 'Mains Supply …' 의 열이 곧 형번 PK25·P1K5·P11K,
   9열 전수 읽힘). 막힌 곳 둘뿐: `datasets.unit_models` 의 제목 관문이
   `general data|physical data|형번별 정격` 만 받고, e15 픽이 LS 의 한글 라벨로만 쓰여 있다.
   **문서를 더 구할 필요가 없다.**
2. **[2순위 공조기·외조기] 국내 벤더 수집** — 신성엔지니어링·센추리·우원기계가 계획서
   1순위로 지목돼 있다. **외조기는 0모델**이다.
3. **[3순위] 가스트론 GTC-200A 취입** — 수집 완료. 레지스터가 행이 아니라 **식**이다
   (농도 `30000+n`, 상태 `10001+((n-1)*8)`). 행으로 펼치지 말고 식으로 저장.
4. **[3순위] 부스타 보일러 정격** — 사양표가 페이지 안 `<table>` HTML 이다.
   `collect.py` 최소 크기 필터를 손봐야 한다(imweb 이 길이 헤더를 안 준다).
5. **[5순위] 열교환기·냉각탑** — 26·16대인데 **0모델**. 빈 계열 중 물량이 확인된 둘.

### [참고] 정격 결손 전수 조사 결과 (2026-09-07 산출 — 우선순위가 아니라 지도다)

**모델 158건 중 정격 결손 98건(62 %)**, 그 98건이 물고 있는 오브젝트가 **18,198점(48.7 %)** 이다.
사유가 셋으로 갈린다 — **절반은 문서를 더 구할 필요가 없다.**

| # | 대상 | 점 | 상태 |
|---|---|---|---|
| 1 | **Belimo 19모델** | 492 | **`data/raw/belimo_*_datasheet_*.pdf` 60건이 이미 있는데 아무 모델도 참조하지 않는 고아다.** spec-map 에 매핑만 하면 찬다. 결손 **모델 수 기준 최대**. 겸사 flow-sensor-22PF·sensors-22DT/22UT·VRU-D3-BAC 3건은 통신맵도 raw 에 있는데 미취입이라 오브젝트까지 같이 찬다 |
| 2 | **YORK 냉동기 38모델** | 5,711 | **소스 `jci-chiller-eg` 등재 완료(EG 86건).** 웹이 아니라 `data/haystack/_jci_docs.json` 스냅샷에서 라우팅했다. 내려받아 취입하면 된다 |
| 3 | YORK 루프탑·자립형 8모델 | 4,650 | **IOM 이 이미 raw 에 있다**(`JCI_IOM_100.50-NOM8` 은 Electrical Data 33회). specs.py 를 안 돌렸을 뿐 |
| 4 | **Vertiv Liebert 19모델** | 5,515 | 새로 받아야 한다. URL 확인 완료(전부 `www.vertiv.com` 200 PDF): PDX/PCW·CW·CRV·Mini-Mate System Design Catalog, XDC·XDP User Manual. DSE·ICOM-XDM·DCP·CAHU·DME2 5건(1,358점)은 **미발견** |

**공식 출처로 확인된 것**(전부 살아 있음, 벤더 자사 호스트):
- 삼성 유럽 DVM S ODU TDB 659쪽 `images.samsung.com/…/common-techinfo-vrf-odu-dvm-s-for-europe-r410a-50hz-ver-1-3-tdb.pdf` (⚠ 50 Hz 유럽 모델 — 국내 60 Hz 와 형번이 다르다)
- LG Multi V 5 Engineering Manual 116쪽 `media.us.lg.com/m/12911aada56be160/original/EM_MULTI-V-5-LGRED-Outdoor-Units-Engineering-Manual_09_26_24-pdf.pdf`
- LG AC Smart 5 Submittal `media.us.lg.com/m/6250fa3a900bca23/original/SB_AC_Smart5_PACS5A000-pdf.pdf` (게이트웨이 자기 정격만)
- ❌ 삼성 국내 60 Hz TDB · LG 국내 카탈로그 직링크는 **없다**(회원 인증·JS 뷰어). 지어내지 않았다.

### [B] 남은 것

1. **Danfoss FC 101 형번별 확정본** — 원문에는 다 있다(Table 10~19 'Mains Supply …' 의
   열이 곧 형번 PK25·P1K5·P11K, 9열 전수 읽힘). 막힌 곳 둘: `datasets.unit_models` 의
   제목 관문이 `general data|physical data|형번별 정격` 만 받고, e15 픽이 LS 의 한글
   라벨로만 쓰여 있다. **관문을 넓히고 픽을 더하면 찬다 — 문서를 더 구할 필요 없다.**
2. 가스트론 GTC-200A 취입 — 레지스터가 행이 아니라 **식**이다(농도 `30000+n`,
   상태 `10001+((n-1)*8)`). 행으로 펼치지 말고 식으로 저장(Daikin DMS502B71 부류).
3. 부스타 보일러 정격 — 사양표는 페이지 안 `<table>` HTML 이다. `collect.py` 최소 크기
   필터를 손봐야 한다(imweb 이 길이 헤더를 안 준다). 통신은 `/70 BMCT` 쪽 — 아직 안 봤다.
4. LS H100 `Table of Functions`(본체 매뉴얼 409~506) — 설정 파라미터 전수라 필요 판단 먼저.
5. **평면 24,376점 재취입** — 손실 잣대는 `audit_legacy.py`. 1순위 Swegon GOLD
   (3,362점 · 안 읽힌 값 8,446), 그다음 Systemair · Trane UC800 7판 · Siemens ·
   ebm-papst · Vertiv(출처 미기록 4,929점).

### [C] 남은 빨강 1건 — Trane Precedent 중복 (이전부터 있던 것)

`units.py:57` 의 병합 열쇠가 `형번@페이지` 라 `Table 5 …(WHJ*)` 와 그 `(continued)` 가
같은 형번을 별개 레코드 둘로 만든다. 뒤엣것은 값이 비어 화면을 `—` 로 덮는다
(`test_precedent_rooftop_units_are_packaged_not_condensing` 의 `WHJ150` 이 그것이다).
고칠 자리 둘: `(continued)` 를 앞 표에 병합하거나(York·IntelliPak 은 이미 그렇게 한다),
병합 열쇠에서 페이지를 빼거나. **뷰어 쪽에서는 이미 같은 원인을 고쳤다** — 이어지는 표를
`(source, base_title, header[1:])` 로 묶는다.

### 이 파일들이 규칙을 담고 있다 (새 벤더 취입 전에 읽는다)

- `pipeline/README.md` 규칙 0~7 — 특히 **요구 항목을 먼저 정하고 문서를 연다**
- `data/point-schema.json` · `data/unit-schema.json` — 사전 우선. 새 계통·필드·feature 는 **먼저 등재**
- 취입기 본보기: `ingest_samsung_ratings.py`(**눈금선 격자** — 병합이 심한 표) ·
  `ingest_ls_ratings.py`(낱말 좌표 + 표 인식 병합) · `ingest_lg.py`(전치 표) ·
  `ingest_lg_modbus.py`(같은 문서의 다른 통로) · `ingest_lg_ahu.py`(각주 풀기)
<!-- NEXT-ACTION:END -->

<!--
규칙:
- 이 마커 사이는 "지금/다음 할 일" 1~3건만. 짧게(화면 한 판).
- 완료된 항목은 여기 두지 말고 WORKLOG.md 의 ## History 로 옮긴다 (단일 출처·비대 방지).
- 훅(tools/hooks/print_next_action.py)은 이 마커 사이만 세션에 주입한다.
-->

## 백로그 (착수 전 후보 — 순서 무관)

| 할 일 | 메모 |
|---|---|
| opendataloader-pdf 채택 여부 | 대조 완료(`parser-comparison.md`). 회수는 동률이라 급하지 않다. 20곳을 한 번에 바꾸지 말고 `crosscheck.py` 부터 붙여 보는 안 |
| 옛 평면 포인트 24,423점 이관 | 91모델. `pointmap.py` 로 변환은 되지만(유실 0) 검수 없이 밀면 추출 결함이 확정본으로 굳는다. 벤더 단위로 |
| YS 판을 YS 모델로 이동 | **접음**(2026-08-20). 판 id 가 두 모델에 중복되고 `--refresh` 가 맥락을 잃어 `appliesTo` 좁힘이 풀린다 |
| e9 무형번 18모델 정격 카탈로그 | RTAC·RTWD/RTHD·CentraVac·Agility·AGZ-F·WME 등 — 통신 문서뿐이라 제품 카탈로그 수집 필요(짝 규칙) |
| 빈 계열 8개 채우기 | 냉각탑·보일러·열교환기·조명·방재·승강·보안·환경 — 벤더 발굴부터 |
| Liebert CRAC 정격 사양 | 통신 레퍼런스엔 없다. Vertiv 제품 카탈로그가 따로 필요 |
| 「기타」 99개 표 정리 | EMC 시험결과·파라미터 목록이 섞여 있다. 실을지 말지 판단 필요 |
| 용어 사전 보강 | `data/spec-terms.json` 87개. 실제 데이터에 나온 용어만 넣는다 |
| 용어 교체 | `종`·`판` 대신 쓸 실무 용어(`기종`·`포인트 리스트` 후보)를 정한 뒤 화면·문서에 일괄 반영 |
| `Style A–C` 근거 | 판 이름 56벌 중 유일하게 원문 머리글 단서가 없다. 나머지 55벌은 `data/_iface_audit.json`에 근거 있음 |
| PostgreSQL 적재 | `07-api-contract.md` 의 `bes_*` 스키마. R-1~R-12 개정 반영 후 |
