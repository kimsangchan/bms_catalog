<!-- NEXT-ACTION:START -->
## ▶ 지금 할 일 (새 세션은 이 블록부터 — SessionStart 훅이 자동 주입)

- **[다음]** JCI 남은 사람 판단 2건 — "판 수와 덮는 제품 수가 같은데 문서가 짝을 안
  밝힌 것"(YCWS/YCRS · YS/YN). 대조는 `ingest_jci.py --export --with-pages --only <문서>`
  로 원문 쪽을 화면에 띄워서 한다(전 문서는 26MB 초과라 --only 필수). 가려지면 별칭
  모델을 그 판에 직접 잇고, 못 가리면 지금처럼 두는 것이 맞다.
- **[다음]** JCI 38제품군은 **정격이 없다** — BAS 포인트/IOM 문서만 있다. 시뮬레이터가
  쓰려면 York 냉동기·옥상형·자립형 제품 카탈로그(용량·COP·전류)를 따로 수집해야
  한다(짝 규칙).
- **[후보]** 옛 평면 포인트 24,423점(91모델)을 인터페이스로 이관 — `pointmap.py` 로 변환은
  되지만(유실 0) 검수 없이 밀면 추출 결함이 확정본 얼굴로 굳는다. 벤더 단위로 끊어서.
- **[후보]** 형번 클래스 편입 4계열 — e15 인버터(Danfoss FC101), e13 송풍기(ebm-papst),
  e19 전력(Schneider PM), e6/e16 Belimo. 절차: `units.py --propose-class` → classes 정의
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
