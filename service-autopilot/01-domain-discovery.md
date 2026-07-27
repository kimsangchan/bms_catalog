# Domain Discovery

## 로컬 데이터 관찰

- 입력 경로:
  - `D:\DB\서울캠퍼스\포인트리스트_자동제어\셔블_자동제어_1캠퍼스_04월_기존`
  - `D:\DB\서울캠퍼스\포인트리스트_자동제어\셔블_자동제어_2캠퍼스_02월_기존`
- CSV 파일 수: 161개
- 총 포인트 수: 25,205개
- 공통 컬럼: `SERVER_ID`, `SYSTEM_ID`, `DEVICE_ID`, `OBJ_TYPE`, `DEVICE_SEQ`, `SYSTEM_PT_ID`, `OBJ_NAME`, `OBJ_UNIT_NUM`, `OBJ_DECIMAL`, `OBJ_DESC`, 알람/상하한/보안/메모 계열 컬럼.
- 주요 구조:
  - 다수 행의 `OBJ_NAME`이 `장비인스턴스.points.포인트명` 형태다.
  - 파일명에는 판넬/컨트롤러/NC/BACnet 서버 단서가 포함된다.
  - `OBJ_TYPE` 분포는 3, 0, 2, 4, 5, 1, 7, 8 순으로 많다. BACnet object type 매핑 확인이 필요하다.
- 반복 포인트 후보:
  - VAV/공조: `AirFlow`, `Op Mode`, `Analog Damper Output`, `Zone Temperature`, `Control Mode Config`, `AirFlow Setpoint`, `Occupied Cool Setpoint`, `Occupied Heat Setpoint`
  - 인버터/VFD: `INV_OUT_CURRENT`, `INV_OUT_PWR`, `DCLINK_VOLTAGE`, `INV_ACCUM_PWR`, `INV_OUT_VOLTAGE`, `INV_SPEED_FC101`, `INV_RUN_TIME`, `INV_HEATsink TEMP`
  - BIOT/실내기: `AC_RoomTemp`, `AC_Error_Code`, `AC_DisCurrentTemp`, `AC_Temp_Set`, `AC_Power`, `AC_FilterSign`, `AC_Vacancy`

## 가장 디테일한 원천 우선순위

1. 장비 제조사/벤더 매뉴얼과 통신 맵
   - 장비별 실제 보유 포인트, 단위, enum, 알람 코드, 쓰기 가능 여부, 범위, register/object 의미를 가장 구체적으로 제공한다.
   - 예: VFD 매뉴얼, 냉동기 BACnet/Modbus gateway point map, DDC controller data sheet, 실내기 gateway object map.

2. BACnet discovery/object list
   - 실제 설치 장비가 노출하는 object, instance, present value, units, object name, description, writable property를 확인할 수 있다.
   - 포인트리스트보다 최신 현장 상태에 가깝지만, semantic tag는 보통 부족하다.

3. 현장 포인트리스트
   - 현재 받은 CSV처럼 `장비명.points.포인트명` 패턴이 있으면 자동 분해/태깅 후보 생성에 유용하다.
   - 단점은 단위 누락, 한글/영문 혼재, 장비 모델명 부재, 포인트 의미 중복/오타 가능성이다.

4. 제어 시퀀스/설계도서
   - 어떤 포인트가 실제 제어에 필수인지, 감시 전용인지, interlock/스케줄/알람과 어떻게 연결되는지 판단하는 데 필요하다.
   - 자동제어 시뮬레이터와 AI 제어를 하려면 이 문서가 포인트리스트보다 중요해진다.

5. 공통 표준/온톨로지
   - Project Haystack: 건물, 공간, 설비, 센서 등 공통 개념을 ontology, defs, tags, file/API 형식으로 모델링한다.
   - Brick Schema: 건물 안의 물리/논리/가상 자산과 관계를 표준화하는 open-source ontology다.
   - ASHRAE BACnet Standard 135: 건물 자동제어 네트워크의 통신 서비스, 프로토콜, 객체 지향 정보 표현을 정의한다.

## 결론

포인트리스트만으로도 “현장 인스턴스와 포인트 타입 후보”는 만들 수 있다. 하지만 “장비 spec 표준”은 포인트리스트에서 역추론하면 품질이 낮다. 초기 DB는 현장 포인트리스트를 수용하되, 표준 장비 템플릿은 제조사/프로토콜/시퀀스 문서를 evidence로 연결하는 구조가 필요하다.

---

# 정정 및 보강 — 2026-07-27 전수 실측

> 위 07-23 조사는 **표본 2폴더**만 열어본 결과다. 전수 프로파일링으로 규모·포맷·전제가 바뀌었다.
> 상세는 **`evidence/pointlist-profile-summary.md`**(스크립트·원자료 동봉). 여기에는 위 본문을 뒤집는 항목만 적는다.

## 규모 정정

| 항목 | 위 본문 기재 | 전수 실측 |
|---|---|---|
| CSV 파일 | 161 | **1,027** |
| 총 포인트 | 25,205 | **114,962** |
| 원천 포맷 | 1종(셔블) | **2종** — 셔블 898파일/93,235행 + **Niagara BACnet export 129파일/21,727행** |

## 본문 전제 중 틀린 것

1. **“다수 행의 `OBJ_NAME`이 `장비인스턴스.points.포인트명` 형태다”** → 전수 기준 **24.1%뿐**이다
   (flat 67,657행 = 72.6%, 기타 dot 3,076행). **이름 파싱에 의존하는 설계는 성립하지 않는다.**
2. **“`OBJ_TYPE` 매핑 확인이 필요하다”** → 확인 완료. NEUROS 코드와 BACnet 표준 enum은 **0~5만 일치**하고
   6번부터 어긋난다 (BACnet MSI=13·MSO=14·MSV=19 vs NEUROS 6·7·8). 실측에서 NEUROS 6(MSI)은 **0건**.
   → 단일 canonical + 체계별 매핑 테이블이 필요하다(`bes_object_type_code`).
3. **“단위 누락”** → 누락 정도가 결정적이다. `OBJ_UNIT_NUM` **공란 79.6%**, 표기 변형 병존(`℃`/`°C`,
   `CMH`/`m³/hr`), 단위 칸에 숫자 오염(`129`,`73`). → 단위는 현장에서 얻을 수 없고 **카탈로그가 공급**해야 한다.
4. **“BACnet object list는 수집 필요”** → **이미 보유**하고 있었다. `2025/나이아가라_9월·10월` 91파일이
   Niagara BACnet export이며 `Object Type`·`Inst Num`·`BACnet Writable`(우선순위 슬롯)·`Value`(단위+상태)를 담고 있다.

## 새로 드러난 것 (설계에 반영됨)

- 알람 등급 비영값 **0건**, 트렌드 주기 **전부 공란**, 상태 enum 사실상 미사용 → **알람·트렌드·enum 기본값도
  카탈로그가 공급**해야 한다. (이 사실이 D-005 스코프 정정의 실증 근거다)
- `(SERVER_ID, SYSTEM_ID, DEVICE_ID)` 조합이 **161종** = 한 스냅샷 파일 수와 일치 → **1파일 = 1컨트롤러**.
- `(…, SYSTEM_PT_ID)` 4키는 스냅샷 내에서만 유일(29,329키 중 26,098키가 중복 등장, 동일 `OBJ_NAME`이 최대 104파일).
  → 취입 PK에 **스냅샷 축 필수**.
- 인코딩 3종 혼재(UTF-8 BOM 498 / CP949 396 / ASCII 133)이나 **손실 디코딩 0** → “깨진 인코딩”이 아니라
  디코더 선택 문제. BOM→CP949 폴백으로 무손실 처리된다.
- 포인트명에 Modbus 레지스터 주소가 박혀 있다(`환수온도40036`, `유량값40002`) → 통신맵 정보가 이름으로 샌 것.
- 모델명 자동 확정은 불가. `UC-800`·`FC-101`(실모델)과 `AH-114`·`CT-103`(현장 태그번호)이 같은 패턴에 걸린다.
  → **후보 추천 + 사람 확정**만 안전. 가정 A-05·결정 D-003 재확인.

## 조사 방법 (재현 절차)

```bash
PYTHONUTF8=1 python evidence/profile-pointlists.py     # → evidence/pointlist-profile.json
```
대상 경로는 스크립트 상단 `ROOT` 상수. 인코딩은 BOM → UTF-8 → CP949 순 폴백으로 판별한다.
