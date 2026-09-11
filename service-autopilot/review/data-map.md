<!-- review_index.py 가 만든다. 직접 고치지 마라 -->
# data-map.html

**데이터 지도 — 원문이 어떤 층을 거쳐 BMS·시뮬레이터 모양이 되나**

| | |
|---|---|
| 굽는 법 | `cd service-autopilot/pipeline && PYTHONIOENCODING=utf-8 python schema_map.py` |
| 다시 굽는 때 | 스키마(point-schema·unit-schema)를 고친 뒤 |
| 크기 | 32 KB |
| 여는 법 | 더블클릭 (오프라인 단일 파일 · 인터넷 없이 열린다) |

## 무엇을 보나

- 6개 층과 6개 조인 키(modelId·equipId·interfaceId·형번·feature·templateName)
- point-schema·unit-schema 를 실시간으로 읽어 표로 보여 준다
- LS H100 하나를 층마다 따라가는 표본

---

폴더 전체 안내는 [`_INDEX.md`](_INDEX.md) 에 있다.
