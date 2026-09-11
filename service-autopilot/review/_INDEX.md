<!-- review_index.py 가 만든다. 직접 고치지 마라 -->
# review/ — 무엇이 무엇인가

여기 있는 HTML 은 **오프라인 단일 파일**이다. 더블클릭하면 인터넷 없이 열린다.
파일마다 같은 이름의 `.md` 가 옆에 있으니 탐색기에서 바로 확인하면 된다.

## 지금 쓰는 것

| 화면 | 무엇 | 굽는 법 | 크기 |
|---|---|---|---|
| [`template-map.html`](template-map.html) | BMS 기본화면 템플릿 검사대 | `python template_map.py` | 753 KB |
| [`equip-catalog.html`](equip-catalog.html) | 전체 카탈로그 — 이 저장소의 대표 산출물 | `python build.py` | 15.6 MB |
| [`point-verify.html`](point-verify.html) | 취입 검사대 — 원문 쪽 그림과 나란히 본다 | `python verify_points.py` | 27.0 MB |
| [`data-map.html`](data-map.html) | 데이터 지도 — 원문이 어떤 층을 거쳐 BMS·시뮬레이터 모양이 되나 | `python schema_map.py` | 32 KB |
| [`jci-ingest.html`](jci-ingest.html) | JCI 문서 취입 검사대 | `python ingest_jci.py --export` | 58.7 MB |

## 물러난 것 — `_archive/`

지우지 않았다. **지우면 왜 있었는지가 함께 사라진다.** 사유는 각 파일 옆 `.md` 에 적혀 있다.

| 화면 | 왜 물러났나 |
|---|---|
| `_archive/spec-verify.html` | 2026-08-11 산출. `verify.py` 가 굽는 전 모델 정격 검사대다. |
| `_archive/req-verify-e5.rtu.html` | 2026-08-11 산출. 요구 프로파일 **하나**(e5.rtu)의 충족도 화면이다. |
| `_archive/jci-points.html` | 2026-08-12 산출. `vendor_jci_sceq.py` 의 SC-EQ 포인트 화면이다. |
| `_archive/lg-bacnet-verify.html` | 2026-09-04 산출. LG AC Smart BACnet 전용 검사대(`verify_lg.py`). |
| `_archive/implementation_plan.html` | 2026-09-03 파일이지만 **굽는 스크립트가 없다** — 손으로 만든 옛 기획 산출물이다. 지금 계획은 `NEXT.md` 와 `WORKLOG.md` 가 들고 있다. |

## 굽는 순서 (전부 다시 만들 때)

```bash
cd service-autopilot/pipeline
PYTHONIOENCODING=utf-8 python validate.py      # 먼저 오류 0 확인
PYTHONIOENCODING=utf-8 python datasets.py      # 데이터셋 먼저
PYTHONIOENCODING=utf-8 python build.py
PYTHONIOENCODING=utf-8 python template_map.py
PYTHONIOENCODING=utf-8 python schema_map.py
PYTHONIOENCODING=utf-8 python verify_points.py # 무겁다(수 분)
```
