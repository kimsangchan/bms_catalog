# AGENTS.md — solution-planning

이 파일은 저장소 루트(`D:\_solutions\Neuros\solution-planning`)에 있어 **AGENTS.md 호환 에이전트
(Codex 등)가 세션마다 자동으로 읽는다.** 상세는 중복하지 않고 하위 문서를 가리킨다.

> ⚠ 이 저장소는 형제 폴더 `NEUROS`(SCADA/BMS 본체)와 **별개의 git 저장소**다.
> NEUROS·ICT 작업 지침(`../CLAUDE.md`)은 여기 적용되지 않는다.

## 무엇을 만들고 있나

**BMS 장비 스펙·태그 기준 DB** (`service-autopilot/`). 목적은 둘이다.

1. BMS에서 **장비 모델만 고르면 오브젝트 매핑이 자동으로** 되게 한다
2. **시뮬레이터가 전력 소모·온도를 계산**할 만큼 상세한 정격을 갖춘다

산출물은 벤더 공개 문서(PDF)에서 기계로 뽑은 **모델별 오브젝트 목록 + 정격 사양**이고,
보는 화면은 오프라인 단일 HTML(`service-autopilot/review/equip-catalog.html`)이다.

## 먼저 읽을 것

| 문서 | 내용 |
|---|---|
| `service-autopilot/pipeline/README.md` | **필독.** 수집→추출→대조→검증→빌드 전 과정, 문서 두 종류의 차이, 벤더별 함정 |
| `service-autopilot/README.md` | 기획 산출물 인덱스와 스코프 정정 경위 |
| `service-autopilot/decision-log.md` | 결정과 기각 대안 (D-001~) |
| `service-autopilot/08-equip-spec-tag-catalog.md` | 장비 19계열 · Haystack 4 태그 기준 |

## 작업 위치

```
service-autopilot/
├─ pipeline/            수집·추출·검증 코드 (여기서 실행)
│  ├─ sources.py        벤더 문서 소스 레지스트리
│  ├─ collect.py        열거·내려받기 → data/raw/ (git 제외)
│  ├─ extract.py        문서 → 오브젝트 목록
│  ├─ specs.py          문서 → 정격 사양 · 표 성격 분류
│  ├─ crosscheck.py     표 인식과 다른 경로로 재독해해 대조
│  ├─ validate.py       게이트 (오류 0 이어야 한다)
│  ├─ build.py          → review/equip-catalog.html
│  └─ data/models/      모델 1건 = JSON 1개  ★ 산출물 본체
├─ evidence/gen2.py     HTML 템플릿 (화면 손보려면 여기)
└─ review/equip-catalog.html   결과물 (더블클릭해서 본다)
```

## 자주 쓰는 명령

```bash
cd service-autopilot/pipeline
PYTHONIOENCODING=utf-8 python validate.py          # 검사 — 오류 0 확인
PYTHONIOENCODING=utf-8 python build.py             # HTML 다시 만들기
PYTHONIOENCODING=utf-8 python collect.py --list    # 소스 목록
PYTHONIOENCODING=utf-8 python collect.py --run <소스ID>
PYTHONIOENCODING=utf-8 python specs.py --kinds     # 사양 표 성격 분류
```

`PYTHONIOENCODING=utf-8` 를 빼면 한글 출력에서 `UnicodeEncodeError` 로 죽는다(Windows cp949).
큰 문서(1,000쪽 이상)는 표 인식이 느려 몇 분 걸린다 — 백그라운드로 돌린다.

## 반드시 지킬 것

1. **문서에 적힌 것만 적는다.** 값을 지어내지 않는다. 모르면 모른다고 `gap` 에 적는다.
   추측으로 채운 값은 시뮬레이터가 그대로 믿어 버린다.
2. **원문 바이너리를 저장소에 넣지 않는다** (D-008). `pipeline/data/raw/` 는 gitignore 되어 있다.
   경로·SHA-256·출처만 `data/collected.json` 에 남긴다.
3. **추출기를 고치면 회귀를 확인한다.** 기존 문서 몇 건을 다시 뽑아 포인트 수가 그대로인지 본다.
   열 이름 하나를 바꿨다가 다른 벤더 문서 550점이 통째로 사라진 적이 있다.
4. **교차 대조를 믿는다.** `crosscheck.py` 는 표 인식과 다른 경로로 원문을 한 번 더 읽는다.
   일치율이 낮으면 대개 추출기가 틀린 것이다 — 실제로 이름 자리에 벤더 코드가
   들어간 것을 이 대조가 잡아냈다(59.5% → 고친 뒤 99.8%).
5. **`validate.py` 오류 0 을 유지한다.** 경고는 남아도 되지만 사유가 설명돼야 한다.
6. 커밋 메시지는 **한글**. 제목에 `[기능]`·`[개선]`·`[수정]` 을 붙이고, 본문에
   **무엇이 왜 틀렸는지**를 적는다 (다음 사람이 같은 함정을 밟지 않도록).
7. push 는 지시받았을 때만 한다.

## 지금 상태 (2026-08-04)

- 모델 **92건** · 오브젝트 **22,366점** · 정격 사양 **73모델** · `validate.py` 오류 0 · 계열 10/19
- 글로벌 공조기 커버리지(e5 12모델): 리더 4사 전부(Trane·Daikin·JCI/York·**Carrier**) +
  미국 **AAON**(VCCX2 534점) + 유럽 **Swegon GOLD**(Modbus 3,362점)·IV Produkt.
  남은 후보: Lennox·Systemair·Mitsubishi — `pipeline/README.md` '새 벤더 추가 절차'
  체크리스트대로 진행할 것.
- 공조기(e5) 9모델(Trane 6 + Daikin MicroTech·JCI Simplicity SE·Siemens Climatix) —
  8모델 형번·정격 후보 완료(형번 133건·전기 특성 373행 — York 32·Rebel 13 포함,
  Envistar 만 미지원: 카탈로그 표 제목이 각주 조각). 신규 6모델 사진·근거 문서 연결 완료.
- 형번·정격 작업 화면이 **냉동기(e9)까지 확장** — Daikin AGZ 16·Trane CGAM 14×3·
  Ascend·Sintesis 등 형번 후보 118건(전체 251건). 게이트는 "형번이 실제로 뽑힌 모델".
- 냉동기(e9)에 Daikin MicroTech 3모델(AGZ·AWV·WME 계열 등) 추가
- 신규 6모델 전부 제품 카탈로그 정격 연결 완료(Trailblazer CAT624/635 · Rebel ED19116 ·
  York 기술가이드 2권 · Envistar 2024 · Magnitude CAT632/ED19135). ⚠ Daikin 신형
  카탈로그(CAT 261·639·641)는 표 없는 브로슈어라 ED/구판을 써야 한다.
- 마지막 커밋: 신규 6모델 정격 카탈로그 연결 (spec-map 9문서 추가)

### 다음에 할 만한 것

| 할 일 | 메모 |
|---|---|
| 빈 계열 8개 채우기 | 냉각탑·보일러·열교환기·조명·방재·승강·보안·환경 — 벤더 발굴부터 |
| Liebert CRAC 정격 사양 | 통신 레퍼런스엔 없다. Vertiv 제품 카탈로그가 따로 필요 |
| 「기타」 99개 표 정리 | EMC 시험결과·파라미터 목록이 섞여 있다. 실을지 말지 판단 필요 |
| 용어 사전 보강 | `data/spec-terms.json` 87개. 실제 데이터에 나온 용어만 넣는다 |
| PostgreSQL 적재 | `07-api-contract.md` 의 `bes_*` 스키마. R-1~R-12 개정 반영 후 |
