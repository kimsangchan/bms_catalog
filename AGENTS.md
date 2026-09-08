# AGENTS.md — solution-planning

이 파일은 저장소 루트(`D:\_solutions\Neuros\solution-planning`)의 **크로스툴 단일 원본**이다.
Claude Code는 `CLAUDE.md`의 `@import`로, Codex·Antigravity·Cursor는 네이티브로 읽는다.
프로젝트 표준·네비게이션만 담고 얇게 유지한다(≤ ~4KB). **상태·다음할일은 여기 쓰지 않는다.**

> ⚠ 이 저장소는 형제 폴더 `NEUROS`(SCADA/BMS 본체)와 **별개의 git 저장소**다.
> NEUROS·ICT 작업 지침(`../CLAUDE.md`)은 여기 적용되지 않는다.

## 세션 시작 — 먼저 이것부터

1. `NEXT.md`의 `NEXT-ACTION` 마커 블록을 읽는다 — 그게 지금 할 일이다.
   (Claude Code는 SessionStart 훅이 자동 주입한다. 훅 없는 툴은 직접 연다.)
2. 지난 이력·현재 규모가 필요할 때만 `WORKLOG.md`를 본다.

## 무엇을 만들고 있나

**BMS 장비 스펙·태그 기준 DB** (`service-autopilot/`). 목적은 둘이다.

1. BMS에서 **장비 모델만 고르면 오브젝트 매핑이 자동으로** 되게 한다
2. **시뮬레이터가 전력 소모·온도를 계산**할 만큼 상세한 정격을 갖춘다

산출물은 벤더 공개 문서(PDF)에서 기계로 뽑은 **모델별 오브젝트 목록 + 정격 사양**이고,
보는 화면은 오프라인 단일 HTML(`service-autopilot/review/equip-catalog.html`)이다.

## 네비게이션 (무엇이 어디에)

| 문서 | 내용 |
|---|---|
| `NEXT.md` | **다음 할 일 — 단일 출처** |
| `WORKLOG.md` | 현재 상태·히스토리 (핸드오프 로그) |
| `service-autopilot/pipeline/README.md` | **필독.** 수집→추출→대조→검증→빌드 전 과정, 문서 두 종류의 차이, 벤더별 함정 |
| `service-autopilot/README.md` | 기획 산출물 인덱스와 스코프 정정 경위 |
| `service-autopilot/decision-log.md` | 결정과 기각 대안 (D-001~) |
| `service-autopilot/08-equip-spec-tag-catalog.md` | 장비 19계열 · Haystack 4 태그 기준 |

## 작업 위치

```
service-autopilot/
├─ pipeline/            수집·추출·검증 코드 (여기서 실행)
│  ├─ snapshot_jci.py   JCI 문서 포털 전수 열거 → data/haystack/_jci_docs.json
│  │                    (--probe 두드려 보기 · --run 재생성. 포털을 손으로 고르지 않는다)
│  ├─ sources.py        벤더 문서 소스 레지스트리
│  ├─ collect.py        열거·내려받기 → data/raw/ (git 제외)
│  ├─ extract.py        문서 → 오브젝트 목록
│  ├─ specs.py          문서 → 정격 사양 · 표 성격 분류
│  ├─ crosscheck.py     표 인식과 다른 경로로 재독해해 대조
│  ├─ validate.py       게이트 (오류 0 이어야 한다)
│  ├─ ingest_jci.py     JCI 문서 → 모델의 interfaces[] (--route·--apply·--refresh·--export[ --no-pages --only])
│  ├─ build.py          → review/equip-catalog.html
│  ├─ template_map.py   → review/template-map.html (BMS 기본화면 템플릿 검사대)
│  └─ data/models/      모델 1건 = JSON 1개  ★ 산출물 본체
├─ evidence/gen2.py     HTML 템플릿 (화면 손보려면 여기)
└─ review/
   ├─ data-map.html        **데이터 지도** (schema_map.py) — 원문이 어떤 층을 거쳐
   │                       시뮬레이터·BMS 모양이 되는지, 스키마와 조인 키를 한 화면에
   ├─ template-map.html    **템플릿 검사대** (template_map.py) — 계열별 BMS 기본화면
   │                       행에 **모델을 골라 붙여** 그 개념이 벤더마다 어떤 이름으로
   │                       오는지 본다. 정규식은 이름만으로 뜻을 못 가른다 — 여기서 눈으로 본다
   ├─ equip-catalog.html   전체 카탈로그 (build.py) — 더블클릭해서 본다
   └─ jci-ingest.html      JCI 취입 검사대 (--export — 원문 쪽 그림 포함이 기본, 47MB · gitignore 라 직접 만든다)
```

## 자주 쓰는 명령

```bash
cd service-autopilot/pipeline
PYTHONIOENCODING=utf-8 python validate.py          # 검사 — 오류 0 확인
PYTHONIOENCODING=utf-8 python build.py             # HTML 다시 만들기
PYTHONIOENCODING=utf-8 python collect.py --list    # 소스 목록
PYTHONIOENCODING=utf-8 python collect.py --run <소스ID>
PYTHONIOENCODING=utf-8 python specs.py --kinds     # 사양 표 성격 분류
PYTHONIOENCODING=utf-8 python snapshot_jci.py --probe   # JCI 포털 열거 (담는 것·빼는 것)
```

`PYTHONIOENCODING=utf-8` 를 빼면 한글 출력에서 `UnicodeEncodeError` 로 죽는다(Windows cp949).
큰 문서(1,000쪽 이상)는 표 인식이 느려 몇 분 걸린다 — 백그라운드로 돌린다.

## 반드시 지킬 것

0. **요구 항목을 먼저 정하고 문서를 연다** (`data/equip-requirements.json`, `requirements.py`).
   설비 하위형식마다 "무엇을 왜 뽑는지"와 계산식을 적은 프로파일이 없으면 수집을 시작하지
   않는다. 순서를 어겨서 RTU 를 **냉수코일 AHU 체크리스트로 채점**한 사고가 있었다
   (기외정압 0%·난방 2% 인데 치수 표만 수백 개). 목록은 `haystack.py --diff <설비>` 로
   Haystack protos 와 대조해 근거를 남긴다 — 단 정격은 표준에 없어 계산식으로 정한다.
   상세는 pipeline/README 「규칙 0」.
1. **문서에 적힌 것만 적는다.** 값을 지어내지 않는다. 모르면 모른다고 `gap` 에 적는다.
   추측으로 채운 값은 시뮬레이터가 그대로 믿어 버린다.
2. **원문 바이너리를 저장소에 넣지 않는다** (D-008). `pipeline/data/raw/` 는 gitignore 되어 있다.
   경로·SHA-256·출처만 `data/collected.json` 에 남긴다.
3. **추출기를 고치면 회귀를 확인한다.** 기존 문서 몇 건을 다시 뽑아 포인트 수가 그대로인지 본다.
   열 이름 하나를 바꿨다가 다른 벤더 문서 550점이 통째로 사라진 적이 있다.
4. **교차 대조를 믿는다.** `crosscheck.py` 는 표 인식과 다른 경로로 원문을 한 번 더 읽는다.
   일치율이 낮으면 대개 추출기가 틀린 것이다 — 실제로 이름 자리에 벤더 코드가
   들어간 것을 이 대조가 잡아냈다(59.5% → 고친 뒤 99.8%).
   **고친 것을 만든 방법으로 검증하지 않는다** — 같은 맹점을 그대로 통과한다.
   좌표로 고쳤으면 픽셀로 본다(`ingest_jci.py --audit-pages`). 실제로 도형 좌표로
   고치고 같은 좌표로 "0쪽 잘림"을 확인했는데, 회전된 쪽 135개가 잘려 있었다.
5. **`validate.py` 오류 0 을 유지한다.** 경고는 남아도 되지만 사유가 설명돼야 한다.
5.5 **진척률엔 범위를 앞에 붙인다.** `[JCI 냉동기 포털] 97%` 처럼. 범위 없는 `97%` 는
   전체로 읽혀 남은 일을 숨긴다 — 실제로 그렇게 보고했다가 지적받았다. 분모를 안 세어 본
   구간은 **"미산출"** 이라고 적고, 세는 것 자체를 할 일로 올린다. **후보 수는 분모가
   아니다** — 제목 힌트로 고른 87건 중 진짜는 59건이었다(D-017).
6. 커밋 메시지는 **한글**. 제목에 `[기능]`·`[개선]`·`[수정]` 을 붙이고, 본문에
   **무엇이 왜 틀렸는지**를 적는다 (다음 사람이 같은 함정을 밟지 않도록).
7. push 는 지시받았을 때만 한다.
