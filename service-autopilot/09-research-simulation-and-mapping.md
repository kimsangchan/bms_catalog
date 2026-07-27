# 조사 — 시뮬레이션 데이터 요건 · 오브젝트 매핑 자동화 · 벤더 공개자료

- 조사 2026-07-27 · 3건 병렬 (Fable) · 접근 검증된 출처만 기재, 미확인은 **미확인**으로 명시
- 배경: 궁극 목표가 ⑴ **BMS에서 모델만 고르면 오브젝트 매핑 자동화** ⑵ **그 장비로 시뮬레이터를 만들었을 때
  전력 소모량·온도 제어가 가능할 만큼의 상세 데이터** 이므로, 현재 카탈로그(정격 항목 위주)로 충분한지 검증한 것.

---

# 제1부 — 시뮬레이션에 필요한 데이터

## 1-1. 결론: 정격값만으로는 전력 계산이 불가능하다

EnergyPlus의 냉동기 전력 계산식 ([Engineering Reference — Chillers](https://bigladdersoftware.com/epx/docs/24-1/engineering-reference/chillers.html)):

```
Q_avail   = Q_ref × CAPFT(출구냉수온도, 입구응축수온도)
P_chiller = Q_avail × (1/COP_ref) × EIRFT(같은 두 온도) × EIRFPLR(부분부하율) × CyclingRatio
```

정격용량·정격COP만 있으면 **정격점 1점의 kW만** 나온다. 온도나 부하가 변하는 순간 계산이 멈춘다.
변화를 담는 것이 **성능곡선 3종**(CAPFT·EIRFT·EIRFPLR)이다.

## 1-2. ASHRAE Standard 205 — 이 데이터의 교환 표준

**ANSI/ASHRAE 205-2023** "Representation of Performance Data for HVAC&R and Other Facility Equipment".
제조사 → 시뮬레이션 SW 간 성능 데이터 자동 교환을 위한 **데이터 모델 + 직렬화 포맷**.
현행: 205-2023 + Addenda a·b·c(2024-02), Addendum d(2025)로 RS0001이 수랭 한정에서 공랭·증발냉각 포함으로 확대.

| RS | 대상 | 내포 관계 |
|---|---|---|
| RS0001 | Chiller (구 Liquid-Cooled Chiller) | — |
| RS0002 | Unitary Cooling Air-Conditioning Equipment | RS0003 + RS0004 내장 |
| **RS0003** | **Fan Assembly** | **RS0005 + RS0007 내장** |
| RS0004 | Air-to-Air Direct Expansion System | — |
| RS0005 | Motor | RS0006 내장 |
| RS0006 | Electronic Motor Drive (VFD) | — |
| RS0007 | Mechanical Drive (벨트 등) | — |

**핵심 시사점**: RS0003(팬) = 팬 + 모터(RS0005) + 구동(RS0007)의 합성이다.
**즉 팬 소비전력은 팬 단독 스펙으로 표현되지 않는다** → 카탈로그도 모터·VFD를 장비에서 분리해야 한다.

- 형식: **CBOR(정본) / JSON(스키마) / XLSX(수기 입력 템플릿)**. 도구 [toolkit-205](https://github.com/open205/toolkit-205)(Python, XLSX↔JSON↔CBOR 변환·검증), [schema-205](https://github.com/open205/schema-205).
- **EnergyPlus가 직접 소비**: v22.2+의 `Chiller:Electric:ASHRAE205` 객체가 `.a205.cbor` 표현 파일을 그대로 읽는다
  (필드: `Representation File Name`, `Performance Interpolation Method` LINEAR/CUBIC).
- ⚠️ **제조사 실배포 사례는 거의 없다** — Bemcyclopedia가 "이 포맷 공개 데이터는 아직 거의 없고 BEM SW 채택도 제한적"이라 명시.
  → **형식은 205를 따르되 값은 제조사 성능표에서 채워야 하는 것이 현재 현실.**

## 1-3. 장비별 "시뮬레이션 가능 최소 데이터셋"

| 장비 | 전력 kW를 내려면 필요한 것 | 표준 근거 |
|---|---|---|
| 냉동기 | 정격용량 + 정격COP + **정격 조건 2온도**(출구냉수·입구응축수) + 양측 유량 + **CAPFT(6계수)·EIRFT(6)·EIRFPLR(3)** + Min/Max PLR | `Chiller:Electric:EIR` |
| 팬 | 풍량 + **정압** + 총효율 + 모터효율 + 기류내 설치비율 + **부분부하 계수 C₁~C₅** (근사: W/((m³/s)·Pa) 기본 1.66667) | `Fan:VariableVolume` / `Fan:SystemModel` |
| 펌프 | 유량 + **양정** + 정격전력(또는 모터효율) + **부분부하 계수 C₁~C₄** + 모터손실 유체환원율 | `Pump:VariableSpeed` |
| 냉각탑 | 설계 수량·풍량 + **팬동력** + **설계 습구·어프로치·레인지 3온도** + 팬동력~풍량비 곡선 + 최소풍량비 | `CoolingTower:VariableSpeed` |
| 보일러 | 정격용량 + 정격열효율 + **효율곡선**(PLR 1변수 또는 PLR+수온 2변수) | `Boiler:HotWater` |
| 냉수코일 (**온도 제어**) | 설계점 **공기·물 양측 입출구 온도·습도·유량** → UA 역산 → NTU-effectiveness로 오프디자인 계산 | `Coil:Cooling:Water` |
| 실(존) | 공기 열용량 C_z(부피×현열용량 배수) + 외피 UA + 침기 + 내부발열 → 시정수 τ≈C_z/UA | Zone 열평형 ODE |

**냉수코일이 특히 중요하다** — "냉방능력 kW" 하나로는 온도 제어를 시뮬레이션할 수 없다.
설계점의 공기·수 양측 상태 세트가 있어야 UA를 역산하고, 그래야 부하가 바뀔 때 출구온도가 계산된다.

## 1-4. Modelica는 요구가 다르다 — 이게 저장 형태를 정한다

- **냉동기**: `Buildings.Fluid.Chillers.ElectricEIR`의 데이터 레코드가 EnergyPlus와 사실상 동일
  (`capFunT[6]`, `EIRFunT[6]`, `EIRFunPLR[3]`, `PLRMin/MinUnl/Max`, `TEvaLvg_nominal`, `TConEnt_nominal` …)
  → **곡선계수 재사용 가능**.
- **팬·펌프**: `Buildings.Fluid.Movers`는 계수가 아니라 **전속 성능곡선 원자료**
  `per.pressure(V_flow={…}, dp={…})` 배열을 받아 상사법칙으로 임의 회전수를 스스로 계산한다.

> **저장 형태 결정**: 팬·펌프는 **곡선계수가 아니라 성능곡선 점 배열(P-Q 커브)** 을 원자료로 둔다.
> EnergyPlus용 계수는 점 데이터에서 회귀로 파생하면 되지만, 반대는 불가능하다.

## 1-5. 부분부하 표현 — IPLV로는 안 된다

- IPLV/NPLV (AHRI 550/590): `IPLV = 0.01A + 0.42B + 0.45C + 0.12D` (100/75/50/25% 부하 가중).
- **곡선 대체 불가**: biquadratic 6계수를 만들려면 온도 조합 최소 6점(실무는 수십 점)이 필요하다.
  AHRI 4점으로는 CAPFT/EIRFT를 만들 수 없다. **IPLV는 회귀 검증용으로만.**
- 회귀 도구: EnergyPlus 공식 부속 [HVAC Performance Curve Fit Tool](https://bigladdersoftware.com/epx/docs/9-5/auxiliary-programs/hvac-performance-curve-fit-tool.html).
- 205 방식은 회귀 없이 **성능 그리드를 그대로 담고 소비 측이 보간** → 손실이 없어 가장 미래지향적.

---

# 제2부 — 오브젝트 매핑 자동화

## 2-1. 결론: 완전 자동은 어느 제품에도 없다

Niagara·Metasys·Desigo·Distech·FIN을 전수 확인한 결과 **공통 패턴이 하나**다:

> **사람이 미리 만든 템플릿 재사용 → 실장비 결선(바인딩) → 검증 → 사람 확정**

| 제품 | 템플릿 단위 | 처리 방식 |
|---|---|---|
| **Niagara 4** (Honeywell WEBs·Distech EC-Net OEM 공통) | Template `.ntpl` — 디바이스·포인트·로직·그래픽·**태그**를 한 덩어리로 캡처 | 스테이션에 배포 후 실포인트에 바인딩. Provisioning으로 다수 스테이션 일괄. Tag Dictionary Service(Haystack 내장) |
| **JCI Metasys SCT** | Controller Template + Equipment Definition | **Rapid Archive Creation** — 템플릿 임포트 + Room Schedule로 사이트 DB 대량 생성. **Discover Equipment**로 발견 포인트를 기존 정의에 추가 |
| **Siemens Desigo** | 애플리케이션 라이브러리(LibSet) | AHU·VAV·FCU·열원 등 **사전 시험된 표준 애플리케이션**을 골라 엔지니어링 |
| **Distech Builder** | 클라우드 앱 빌더 | **장비 구성 선택 → 시퀀스·포인트리스트·도면·그래픽·코드까지 자동 생성** — 우리 목표에 가장 근접 |
| **J2 FIN Framework** | 태그 라이브러리 + Equipment Tree | 디스커버리 → **배치 에디터가 발견 포인트를 태그 라이브러리와 자동 매칭**(통신 설정 + Haystack 태그 동시) |

**자동 태깅 정확도(검증치)**: 상업 리테일 **85~90%**, 오피스 **70~75%** (NREL·BrainBox AI 논문, 포인트명+시계열 결합).
LLM 기반 최신 연구(Brick-DICL)도 **저신뢰 예측은 사람 리뷰로 회부**하는 2단계 구조다.
→ **무인 100% 자동화는 검증 사례가 없다.** 목표는 "자동 확정"이 아니라 **자동 제안 + 신뢰도 + 원클릭 확정**.

## 2-2. 표준 진영도 같은 것을 만들고 있다

- **Haystack 5 / Xeto**: "VAV **타입**을 필수 포인트·관계·의존성·기대 동작으로 기계가독 스키마화" → 자동 태깅·자동 모델 조립.
  **우리가 만들려는 모델 템플릿과 정확히 같은 개념.** (단 마케팅 기고 기반이라 성숙도는 보수적으로 볼 것.)
- **ASHRAE 223P**: RDF+SHACL 기반 시맨틱 모델(Type·Topology·Composition·Telemetry). BACnet 위원회·Haystack·Brick이
  **223P로 통합 수렴 중**. FY26 게시 목표, **2026-07 현재 최종 게시 여부 미확인**.

> 대응: 지금 정본은 **Haystack 태그**로 두고, 내부 포인트 역할 코드 ↔ 태그 매핑을 **별도 테이블로 격리**한다.
> 그러면 이후 223P/Xeto 전환 비용이 마이그레이션 테이블 1개로 국한된다.

## 2-3. 치명적 함정 — "모델 1개 = 포인트 리스트 1개"가 깨진다

| # | 원인 | 확인된 근거 |
|---|---|---|
| 1 | **게이트웨이 경로** | 같은 Modbus 장비군을 BASremote는 **하나의 BACnet 디바이스**로, BASgatewayLX는 **장비별 별도 디바이스**로 노출 |
| 2 | **통합 설정·디바이스 프로파일** | Intesis 게이트웨이는 장비 타입별 프로파일을 요구하고 통합 유형에 따라 파라미터를 수정 → 노출 포인트가 달라짐 |
| 3 | **이름이 자유 텍스트** | object-name/description은 시공사·벤더 임의. 벤더 표준 포인트명은 사실상 부재 |
| 4 | **오매핑은 운영 단계에 발견** | JCI 특허 US10564616이 이 문제를 명시하고 **단위 대조 검증**을 해법으로 제시 |
| 5 | **정확도 상한 70~90%** | 건물 유형에 따라 편차 |
| 6 | **펌웨어에 따른 포인트 변화** | BACnet 표준이 오브젝트 목록 변경 시 `Database-Revision` 갱신을 요구 — **목록은 변한다는 전제** (정량적 1차 출처는 **미확인**) |

> **설계 반영**: 프로파일 단위를 **모델**이 아니라 **(모델 × 펌웨어 범위 × 옵션 세트 × 게이트웨이 경로)의 변형(variant)** 으로 잡는다.

## 2-4. 권고 — 4단계 매칭 + 축적 루프

```
1단계  정확 일치        object-type + object-name
2단계  패턴·사전        프로파일의 이름 정규식 / 약어 사전
3단계  검증 게이트      단위·상태문자열 대조 — 안 맞으면 매핑 거부   ← JCI 특허 방식
4단계  AI 후보 제시     저신뢰 건만. 후보 축소 + 다중 판정 → 사람 리뷰 큐
```

- **EDE 파일을 1급 입력 경로로**: 장치 없이 오프라인 취입 가능 → 폐쇄망에 최적. ICT-022의
  CSV/XLSX 검증 미리보기 → 검증 토큰 확정 패턴을 그대로 재사용할 수 있다.
- **재동기화 감지**: 디바이스의 `Database-Revision`을 주기 확인해 변경 시 해당 장비 매핑을 "재검토 필요"로 전환.
- **축적 루프(핵심)**: 공개된 "모델별 포인트 DB"는 **존재하지 않는다**(이번 조사에서 미발견).
  따라서 현장에서 사람이 확정한 매핑을 **역으로 프로파일로 승격**시켜 카탈로그를 키운다.
  첫 현장 수동 60~70% → 이후 현장부터 자동률 상승. Niagara 템플릿 재사용·FIN 태그 라이브러리가 같은 모델이다.

---

# 제3부 — 글로벌 벤더 공개자료 실태

**결론: 상당히 공개돼 있다.** 아래는 전부 접근 검증된 것(HTTP 응답 + 내용 확인). 미확인은 명시.

## 3-1. 벤더별 공개 수준

| 벤더 | 수준 | 무엇이 공개되나 | 기계판독 |
|---|---|---|---|
| **Belimo** | **최고** | BACnet 인터페이스 PDF 23종+, Modbus 레지스터 PDF 21종+, **제품별 BACnet EDE CSV 실배포** | **CSV(EDE)** ✅ |
| **Trane** | 높음 | **컨트롤러별 Points List 독립 문서 시리즈**(BAS-PTS…), 통합가이드. `/public/` 경로 무로그인 | 텍스트 PDF |
| **Johnson Controls** | 높음 | Metasys PICS 전문(HTML), **York 칠러 BACnet/Modbus 데이터맵**(HTML) | HTML(스크레이핑 용이) |
| **Carrier** | 높음 | `shareddocs.com/hvac/docs` 공개 저장소 — BACnet 통합가이드·애플리케이션 가이드 | PDF |
| **Daikin** | 높음(북미) | BACnet 게이트웨이 **Design Guide(오브젝트 리스트 포함)** | PDF |
| **Danfoss** | 높음 | 드라이브 BACnet/Modbus **프로그래밍 가이드(레지스터·오브젝트 표)** 직링크 | PDF |
| **Grundfos** | 높음 | CIM/CIU 통신모듈별 **BACnet functional profile**(=포인트 정의서), PICS | 텍스트 PDF |
| **ABB** | 높음 | ACH580 펌웨어 매뉴얼(내장 BACnet·Modbus 장) 무로그인 | PDF (PICS 직링크는 404 **미확인**) |
| Siemens | 중간 | Desigo PICS, Desigo CC의 **EDE import/export** 도움말 | PDF. 딥링크 휘발성 큼 |
| Honeywell · Schneider · Delta · Distech · ALC | 중간 | PICS, 데이터시트 (상세 통합문서는 파트너 포털 추정 **미확인**) | PDF |
| **LG전자** | 낮음~중간 | ACP BACnet Gateway **submittal + 포인트 리스트**(미국 대리점 공개본). 국내 lghvac은 로그인 | 텍스트 PDF |
| **삼성전자** | 중간(미국법인) | MIM-B17BN **BACnet Gateway Submittal**, 무로그인 다운로드 허브 | 텍스트 PDF |

## 3-2. 두 가지 결정적 수확

**① EDE — 벤더 공통 기계판독 포맷은 사실상 이것뿐**
BIG-EU가 정의한 **세미콜론 구분 CSV** 세트(EDE.csv + StateTexts/ObjectTypes/Units.csv).
[EDE 2.3 템플릿 ZIP](https://www.big-eu.org/wp-content/uploads/sites/6/2022/08/big_ede_2_3.zip)이 **무로그인 다운로드**된다 → 취입 파서의 기준.
Belimo가 제품별 EDE CSV를 실제로 배포하고, 헤더 구조(`keyname;device obj.-instance;object-name;object-type;object-instance;…`)가 실물로 확인됐다.
**장비 제조사가 EDE를 배포하는 사례는 소수**(Belimo가 대표)이고 대부분은 현장 스캔 도구로 생성한다
→ **"벤더 배포 EDE 취입 + 현장 스캔 EDE 취입" 두 경로를 모두 설계**해야 한다.

**② PICS 코퍼스 — 크롤링으로 일괄 확보 가능**
[BTL Listing](https://www.bacnetinternational.net/btl/)이 **무로그인**으로 235개 제조사·1,633개 제품을 제공하고,
`bacnetinternational.net/catalog/manu/<제조사>/<파일>.pdf` 직링크가 그대로 열린다(7개사 실검증).
단 **PICS는 지원 오브젝트 타입·서비스 수준의 능력 선언이지 포인트 인스턴스 목록이 아니다**
→ 카탈로그의 **통신 능력 필드**를 채우는 용도.

## 3-3. 선정 소프트웨어는 기대 이하

Carrier HAP는 **시뮬레이션 결과** CSV export(스펙 카탈로그 export 아님), Trane TRACE 3D Plus는 TOPSS 성능 데이터 가져오기 지원(export 형식 **미확인**),
Grundfos Product Center는 접속 실패(**미확인**), Belimo SelectPro는 export 형식 **미확인**.
→ **카탈로그 시드는 문서(PDF/CSV) 경로가 확실하다.**

## 3-4. 지금 바로 받을 수 있는 문서 (접근 검증 완료)

**1순위 — 기계판독**
1. [BIG-EU EDE 2.3 템플릿 ZIP](https://www.big-eu.org/wp-content/uploads/sites/6/2022/08/big_ede_2_3.zip) — EDE 파서 설계의 기준
2. [Belimo BACnet EDE CSV (열량계)](https://www.belimo.com/mam/general-documents/system_integration/BACnet/belimo_BACnet_EDE_File_TEM.csv) — 실물 샘플 ⚠️ curl 403, 브라우저 필요
3. [Belimo File Archive](https://www.belimo.com/ch/en_GB/support-eu/support-services/file-history) — 인터페이스 문서 일괄

**2순위 — 모델별 포인트 리스트**
4. [Trane Symbio 800 Points List](https://elibrary.tranetechnologies.com/public/commercial-hvac/Literature/Points%20List/BAS-PTS026A-EN_12062024.pdf) *(확보 완료)*
5. [York YVAA/YVFA/YAGK BACnet·Modbus Data Map](https://docs.johnsoncontrols.com/chillers/v/u/YORK/en-US/YVAA-YVFA-YAGK-Native-BACnet-and-Modbus-N2-Data-Map/322) — HTML
6. [LG PQNFB17C1 ACP BACnet 포인트 리스트](https://rji-sales.com/wp-content/uploads/2014/03/LG_BacNet_Submittal_PointsList_PQNFB17C1.pdf) · [삼성 MIM-B17BN Submittal](https://s3.amazonaws.com/samsung-files/Tech_Files/Controls/Central+Control/Submittals/MIM-B17BN_MIM-B17BUN+SUBMITTAL_BAC2.5_092017A.PDF)
7. [Daikin DMS502B71 BACnet Design Guide](https://daikincomfort.com/docs/default-source/interface-for-use-bacnet-/eg-dms502b71bacnet-guide.pdf)
8. [Grundfos CIM/CIU BACnet Functional Profile](https://api.grundfos.com/literature/Grundfosliterature-6012933.pdf) *(부분 확보)*

**3순위 — PICS 코퍼스** [BTL 목록](https://www.bacnetinternational.net/btl/) 경유 크롤링
**4순위 — 통합가이드·레지스터 맵** [Carrier i-Vu](https://www.shareddocs.com/hvac/docs/1000/Public/03/11-808-357-01.pdf) · Danfoss `files.danfoss.com/download/Drives/` · [ABB ACH580](https://library.abb.com/r?cid=9AAC182825&lang=en)

---

# 제4부 — 카탈로그 스키마에 반영할 것

세 조사가 공통으로 가리키는 개정 사항이다.

| # | 개정 | 근거 |
|---|---|---|
| **R-1** | **성능곡선 계층 신설** — 원자료(성능표 그리드) + 파생물(엔진별 곡선계수) 2계층 | 1-1·1-5. 계수만 저장하면 되돌릴 수 없다 |
| **R-2** | **팬·펌프는 P-Q 곡선 점 배열**을 원자료로 | 1-4. Modelica는 계수를 안 받는다 |
| **R-3** | **정격값에 기계판독 조건 필드** — 지금은 사람이 읽는 문장 | 1-3. 조건 없는 용량은 시뮬레이션 시작 불가 |
| **R-4** | **모터·VFD를 장비에서 분리** | 1-2. ASHRAE 205 RS0003 = 팬 + 모터 + 구동 |
| **R-5** | 프로파일 단위를 **모델 → 변형(모델×펌웨어×옵션×게이트웨이)** 으로 | 2-3 |
| **R-6** | **EDE 취입 경로** 신설 (벤더 배포 + 현장 스캔 2경로) | 3-2① |
| **R-7** | **매핑 검증 게이트**(단위·상태문자열 대조) + 신뢰도 점수 + 사람 확정 | 2-1·2-4 |
| **R-8** | **통신 능력 필드**(PICS 유래) — 지원 오브젝트·서비스·COV·세그멘테이션 | 3-2② |
| **R-9** | 태그 ↔ 내부 역할코드 **분리 테이블** | 2-2. 223P 전환 대비 |
| **R-10** | **현장 확정 → 프로파일 승격** 루프 | 2-4. 공개 모델 DB가 없으므로 축적이 유일한 경로 |
| **R-11** | 존(실) 모델 파라미터를 **별도 엔티티**로 (열용량·UA·침기·내부발열) | 1-3. 온도 제어 시뮬레이션은 장비만으론 불가 |
| **R-12** | 운전 한계 필드(Min/Max PLR·최소풍량비·VFD 하한) | 1-3. 저부하 사이클링 계산에 필수 |

## 미확인으로 남은 것

ASHRAE 223P 최종 게시 여부(2026-07) · Brick-DICL 정확도 수치 · 펌웨어별 포인트 변화의 정량 출처 ·
Niagara Template 바인딩 세부 · Distech Builder 세부 · 선정 SW export 형식 ·
Siemens SID 딥링크 2건(문서 이동) · ABB ACH580 PICS 직링크(404) · LG 국내·삼성 국내 자료
