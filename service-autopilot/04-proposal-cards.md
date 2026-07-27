# Proposal Cards

## D-001: 의미 모델 표준

후보:

- Haystack 우선
  - 근거: Project Haystack은 buildings, spaces, equipment, sensors 같은 공통 개념을 ontology/defs/tags로 모델링하고 HTTP API/file format까지 제공한다.
  - 적합도: 높음
  - 이유: 포인트리스트 기반 태깅 표준화와 운영 DB에 직접 적용하기 쉽다.
  - 트레이드오프: 관계 그래프 질의나 엄격한 ontology reasoning은 Brick보다 약할 수 있다.

- Brick 우선
  - 근거: Brick은 건물의 물리/논리/가상 자산과 관계를 표준화하고, equipment/point/location 관계를 명시적으로 표현한다.
  - 적합도: 중간
  - 이유: 분석/시뮬레이터/그래프 관계에는 강하지만, 현장 포인트리스트 태깅 DB의 1차 구현으로는 진입 비용이 높다.
  - 트레이드오프: RDF/graph 모델을 초기에 도입하면 운영 CRUD와 검수 UI가 복잡해진다.

추천: Haystack 우선 + Brick 매핑 레이어

## D-002: DB 모델 경계

후보:

- 단일 `points` 테이블 중심
  - 적합도: 낮음
  - 이유: 빠르게 적재 가능하지만 장비 spec, 표준 포인트, 현장 인스턴스, 원천 evidence가 섞인다.

- 표준 템플릿과 현장 인스턴스 분리
  - 적합도: 높음
  - 이유: 모든 자동제어 장비를 표준화하려면 `equipment_type`, `point_type`, `equipment_template`, `site_equipment`, `site_point`가 분리되어야 한다.
  - 트레이드오프: 초기 설계가 더 필요하다.

추천: 표준 템플릿과 현장 인스턴스 분리

## D-003: 원천 데이터 수집 전략

후보:

- 포인트리스트만 사용
  - 적합도: 낮음
  - 이유: 현장 매핑 시작은 가능하지만 장비 spec 정의가 빈약하다.

- 포인트리스트 + 제조사/통신 맵 + BACnet discovery + 시퀀스 문서
  - 적합도: 높음
  - 이유: 장비 spec, 포인트 의미, 쓰기 가능 여부, 제어 의도를 분리해서 검증할 수 있다.
  - 트레이드오프: 자료 수집/증거 관리 테이블이 필요하다.

추천: 다중 원천 evidence 기반

## D-004: 저장소/서비스 형태

후보:

- NEUROS 내부 전용 모듈
  - 적합도: 중간
  - 이유: NEUROS 연동은 쉽지만 시뮬레이터와 외부 service-autopilot 재사용성이 낮아진다.

- 독립 기준 DB/서비스 + NEUROS adapter
  - 적합도: 높음
  - 이유: NEUROS, BMS 시뮬레이터, 자동제어 시스템이 같은 기준 데이터를 공유할 수 있다.
  - 트레이드오프: 인증, API 버전, 배포 단위가 추가된다.

추천: 독립 기준 DB/서비스 + NEUROS adapter
