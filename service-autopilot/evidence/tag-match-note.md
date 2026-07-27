# 검증 노트 — 기존 포인트리스트 오브젝트 네임에 태그가 걸리는지

> 이 노트는 **표준 조사(`08-equip-spec-tag-catalog.md`)의 근거가 아니다.** 조사로 정리한 태그가
> 실제 현장 이름에 얼마나 걸리는지 나중에 확인하기 위한 **채점 결과**다.
> 대상 포인트리스트는 구버전 SI 형식이므로 컬럼 구조는 보지 않고 **`OBJ_NAME` 하나만** 썼다.

- 실행 2026-07-27 · `evidence/tag-match-test.py` → `evidence/tag-match-result.json`
- 알고리즘: NEUROS `HaystackTagService` 그대로 (토큰화 → 사전 코드/설명 가중 매칭)
- 대상: 고유 `OBJ_NAME` 30,597건

## 결과

| 측정 | 결과 |
|---|---|
| 태그 1개 이상 (설명문 매칭 포함) | 74.5% |
| **태그 코드가 실제 일치** | **56.4%** |
| **장비(equip) 태그가 걸림** | **27.0%** |
| 태그 0개 | 43.6% (13,327건) |

장비군별 코드일치 / equip 태그: VAV 76.8%/67.9% · FCU 76.9%/6.1% · AHU 68.7%/31.9% ·
펌프 62.3%/18.3% · 송풍기 49.0%/**5.0%** · 열교환 34.3%/12.5% · 인버터 21.9%/**1.0%** ·
보일러 11.2%/4.0% · 냉각탑 9.6%/**1.2%** · VRF 3.6%/2.6% · **냉동기 2.3%/2.3%**

## 걸린 것 중 오탐이 많다

| 실제 포인트 | 잘못 붙은 태그 | 원인 |
|---|---|---|
| `Zone Temperature` | `fire-zone` 3,308 · `smoke-zone` 3,300 | 토큰 `zone`이 화재·연기 구역 태그에도 걸린다 |
| `SF`(급기팬) | **`sf6`·`sf6-emission` 각 2,329** | `SF` 토큰이 육불화황에 걸린다 |
| `Op Mode` | `cooling-mode`·`heating-mode`·`fire-mode`·`summer-mode`·`winter-mode`·`economizer-mode`·`vacation-mode`·`earthquake-mode`·`eco-mode` 각 756~814 | 토큰 `mode`가 모든 `*-mode`에 걸린다 |
| `Analog Damper Output` | `fire-damper` 744 · `smoke-damper` 736 | 토큰 `damper`가 방화·방연 댐퍼에도 |
| 팬 이름 | `supply-fan`=`return-fan`=`exhaust-fan` 각 224 | 토큰 `fan` 하나가 셋 다에 |
| 펌프 이름 | `pump-motor`=`booster-pump`=`submersible-pump` 각 182 | 토큰 `pump` 하나가 셋 다에 |

부분 토큰 매칭(+2점)이 하이픈 조합 태그 전체에 무차별로 걸리기 때문이다.

## 이 결과가 말하는 것

**이름 문자열로 태그를 자동 부여하는 경로는 쓸 수 없다.** 절반만 걸리고, 걸린 것의 상당수가 오답이다.
따라서 태그는 **장비 종류 → 표준 포인트 프로파일 → 확정 태그** 경로로 와야 한다
(= `08-equip-spec-tag-catalog.md`가 정리한 표).

이름은 **장비 인스턴스 식별**에만 쓰고, 그러려면 국내 현장 약어를 표준 장비에 잇는 사전이 필요하다:
`SF`→`supply-fan`, `RF`→`return-fan`, `EF`·`KEF`→`exhaust-fan`, `CTCH`·`CT-`→`coolingTower`,
`HWG`→`boiler`, `WPC`→`pump`, `HV`·`HVU`→`heatExchanger`·`heat-recovery`, `INV`·`FC101`→`vfd`,
`UC-800`·`TRANE`·`터보`→`chiller`, `FC-`→`fcu`, `BIOT`·`AC_`→`vrf-indoorUnit-fcu`, `WFM`→`flow-meter`.
⚠ `FP`는 필드패널과 팬파워드 VAV 두 뜻으로 쓰이므로 문맥 규칙이 필요하다.
