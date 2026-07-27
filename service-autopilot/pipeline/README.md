# 카탈로그 파이프라인

모델을 수백 배로 늘리려면 손으로 채울 수 없다. 수집·추출·검증·빌드를 자동화하고
**사람은 검증이 걸러낸 것만** 본다.

```
sources.py ──► collect.py ──► extract.py ──► normalize.py ──► validate.py ──► build.py
 소스 규칙      열거·수집       문서→포인트      다듬기          게이트          HTML
                   │                                              │
              data/raw/                                     검수 큐(경고)
              data/collected.json                           적재 차단(오류)
```

## 실행

```bash
python collect.py --list                     # 소스 목록
python collect.py --probe trane-points-list  # 열거만 (내려받지 않음)
python collect.py --run   trane-points-list --limit 400
python extract.py data/raw/<파일>.pdf --out data/tmp.json
python normalize.py && python validate.py && python build.py
```

## 데이터 저장소 — 여기가 유일한 원본

```
data/
├─ equips/<id>.json     장비 계열 19건 (공통 사양·표준 포인트)
├─ models/<id>.json     모델 (정격·통신·오브젝트 목록)
├─ docs.json            문서 메타 (출처·상태)
├─ known-good.json      ★ 정답 대조셋 — 모델마다 4~6쌍 필수
├─ l3-status.json       계열별 확보 현황
├─ collected.json       수집 대장 (URL·해시·크기·실패 기록)
└─ raw/                 내려받은 원문
```

마크다운(`08-…md`)과 파이썬 딕셔너리는 더 이상 데이터 저장소가 아니다.
`migrate.py`가 1회성으로 옮겼다. HTML은 **생성물**이며 폐쇄망 배포용으로 유지한다.

## 검증 게이트가 하는 일

만든 이유: 자동 추출 결과가 **90% 그럴듯해 보이는데 틀린** 적이 있다.
수백 건을 눈으로 볼 수 없으므로 기계가 대조한다.

| 검사 | 등급 | 무엇을 잡나 |
|---|---|---|
| `dup-instance` | 오류 | 같은 (타입,인스턴스) 중복 — 실내기·실외기가 한 모델에 섞인 경우 |
| `bad-type` | 오류 | 표준 밖 오브젝트 타입 |
| **`known-good`** | **오류** | **원문에서 확인한 정답과 불일치 — 열 밀림을 잡는 최후 방어선** |
| `name-bleed` | 오류/경고 | 이름에 설명·머리글 조각이 섞임 |
| `unit-unknown` | 경고 | 단위 정규화 실패 |
| `name-repeat` | 경고 | 같은 이름이 여러 인스턴스에 (열 밀림 징후) |
| `no-known-good` | 경고 | 정답 대조셋이 없음 = 정확도를 확인할 방법이 없음 |

**오류가 있으면 적재하지 않는다.**

## 실제로 잡아낸 것 (2026-07-27 전환 시점)

| 발견 | 내용 |
|---|---|
| 인스턴스 중복 | JCI VRF에 실내기(4~35)와 실외기(3~30)가 한 모델에 섞여 있었다 → 2개 모델로 분리 |
| 추출기 품질 | 냉동기 3종이 열등한 추출기로 만들어져 **60~70%를 잃고 있었다** (ACSA 98→341점, CTV 206→524점) |
| 인스턴스 오독 | 30000번대 숫자를 BACnet 인스턴스로 읽었으나 **실제로는 Modbus 레지스터**였다 |
| 표 구조물 혼입 | `(continued)`·머리글 행이 포인트로 섞여 있었다 |
| 프로토콜 오판 | BAS-PTS 시리즈에 **LonTalk 문서가 섞여 있다** — BACnet 추출기는 0점을 냈고(옳음), LonTalk 추출기를 따로 붙였다 |

## 소스 추가 방법

`sources.py`에 항목 하나를 넣는다. 열거 방식 3가지:

- `series` — 번호×날짜 조합을 훑는다 (Trane: 220회 조회로 8건 발견)
- `list` — URL 직접 나열
- `page` — 웹페이지 링크 수집 (Belimo·BTL. 봇 차단이 있으면 브라우저 필요)

## 아직 안 한 것

- `page` 방식 자동화 (Belimo·BTL은 봇 차단 — 브라우저 자동화 필요)
- 수집한 LonTalk 문서 5건(655점)을 모델로 등록 — 장비 종류 판정이 필요
- PostgreSQL 적재 (`07-api-contract.md`의 `bes_*` 스키마) — 스키마 개정 12건 반영 후
