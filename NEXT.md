<!-- NEXT-ACTION:START -->
## ▶ 지금 할 일 (새 세션은 이 블록부터 — SessionStart 훅이 자동 주입)

- **[다음]** 형번 클래스 편입 후보 4계열 — e15 인버터(Danfoss FC101 정격표 44+flat 17 — 파워사이즈별),
  e13 송풍기(ebm-papst 정격표 39 — 시리즈별), e19 전력(Schneider PM 정격표 71),
  e6/e16 Belimo(variants 48 — 항목/값 구조라 사다리 확장 필요).
  절차: `units.py --propose-class` → `unit-schema.json` classes 정의 → 사다리/벤더 파서
- **[후보]** e5 기존 모델 심화 — 실외기 데이터북·대용량 EHB 등 (수집 대기열은 완료 상태)
<!-- NEXT-ACTION:END -->

<!--
규칙:
- 이 마커 사이는 "지금/다음 할 일" 1~3건만. 짧게(화면 한 판).
- 완료된 항목은 여기 두지 말고 WORKLOG.md 의 ## History 로 옮긴다 (단일 출처·비대 방지).
- 훅(tools/hooks/print_next_action.py)은 이 마커 사이만 세션에 주입한다.
-->

## 백로그 (착수 전 후보 — 순서 무관)

| 할 일 | 메모 |
|---|---|
| e9 무형번 18모델 정격 카탈로그 | RTAC·RTWD/RTHD·CentraVac·Agility·AGZ-F·WME 등 — 통신 문서뿐이라 제품 카탈로그 수집 필요(짝 규칙) |
| 빈 계열 8개 채우기 | 냉각탑·보일러·열교환기·조명·방재·승강·보안·환경 — 벤더 발굴부터 |
| Liebert CRAC 정격 사양 | 통신 레퍼런스엔 없다. Vertiv 제품 카탈로그가 따로 필요 |
| 「기타」 99개 표 정리 | EMC 시험결과·파라미터 목록이 섞여 있다. 실을지 말지 판단 필요 |
| 용어 사전 보강 | `data/spec-terms.json` 87개. 실제 데이터에 나온 용어만 넣는다 |
| PostgreSQL 적재 | `07-api-contract.md` 의 `bes_*` 스키마. R-1~R-12 개정 반영 후 |
