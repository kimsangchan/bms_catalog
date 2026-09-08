<!-- review_index.py 가 만든다. 직접 고치지 마라 -->
# jci-ingest.html

**JCI 문서 취입 검사대**

| | |
|---|---|
| 굽는 법 | `cd service-autopilot/pipeline && PYTHONIOENCODING=utf-8 python ingest_jci.py --export` |
| 다시 굽는 때 | JCI 문서를 다시 취입한 뒤. 아주 무겁다(60 MB 안팎) |
| 크기 | 58.7 MB |
| 여는 법 | 더블클릭 (오프라인 단일 파일 · 인터넷 없이 열린다) |

## 무엇을 보나

- JCI 포털 문서에서 뽑은 판·포인트를 원문 쪽 그림과 대조
- `--no-pages` 로 그림 없이 가볍게 굽을 수 있다

---

폴더 전체 안내는 [`_INDEX.md`](_INDEX.md) 에 있다.
