<!-- review_index.py 가 만든다. 직접 고치지 마라 -->
# template-map.html

**BMS 기본화면 템플릿 검사대**

| | |
|---|---|
| 굽는 법 | `cd service-autopilot/pipeline && PYTHONIOENCODING=utf-8 python template_map.py` |
| 다시 굽는 때 | 템플릿 행을 고치거나 모델을 새로 취입한 뒤 |
| 크기 | 699 KB |
| 여는 법 | 더블클릭 (오프라인 단일 파일 · 인터넷 없이 열린다) |

## 무엇을 보나

- 계열별 템플릿 행 — 개념·종류·단위·등급·왜 필요한가·Haystack 근거·매칭 정규식
- **모델·판을 고르면** 각 행에 실제로 붙은 포인트 이름이 채워진다
- 모델 × 행 덮개 격자 — 아무 모델도 안 내주는 행을 찾는다

---

폴더 전체 안내는 [`_INDEX.md`](_INDEX.md) 에 있다.
