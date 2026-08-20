<!-- NEXT-ACTION:START -->
## ▶ 지금 할 일 (새 세션은 이 블록부터 — SessionStart 훅이 자동 주입)

- **[다음]** YS 판 2개를 YN 모델에서 **YS 모델로 옮길지** 판단 — `YS Standard`·`YS SSS`
  목록이 YN 모델에 얹혀 있다(문서가 YS·YN 을 함께 덮어 주 제품을 YN 으로 잡은 탓).
  이제 판별로 제품이 갈렸으니 옮기는 것이 옳지만, 확정 판의 소유가 바뀌는 일이다.
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
| opendataloader-pdf 채택 여부 | 대조 완료(`parser-comparison.md`). 회수는 동률이라 급하지 않다. 20곳을 한 번에 바꾸지 말고 `crosscheck.py` 부터 붙여 보는 안 |
| e9 무형번 18모델 정격 카탈로그 | RTAC·RTWD/RTHD·CentraVac·Agility·AGZ-F·WME 등 — 통신 문서뿐이라 제품 카탈로그 수집 필요(짝 규칙) |
| 빈 계열 8개 채우기 | 냉각탑·보일러·열교환기·조명·방재·승강·보안·환경 — 벤더 발굴부터 |
| Liebert CRAC 정격 사양 | 통신 레퍼런스엔 없다. Vertiv 제품 카탈로그가 따로 필요 |
| 「기타」 99개 표 정리 | EMC 시험결과·파라미터 목록이 섞여 있다. 실을지 말지 판단 필요 |
| 용어 사전 보강 | `data/spec-terms.json` 87개. 실제 데이터에 나온 용어만 넣는다 |
| PostgreSQL 적재 | `07-api-contract.md` 의 `bes_*` 스키마. R-1~R-12 개정 반영 후 |
