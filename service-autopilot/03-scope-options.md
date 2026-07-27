# Scope Options

## MVP

- CSV raw import
- `OBJ_NAME` 기반 장비 인스턴스/포인트 후보 분해
- Haystack tag 후보 자동 추천
- 표준 장비 분류와 표준 포인트 타입 사전
- raw point와 standard point mapping 수동 확정 UI/API
- NEUROS/시뮬레이터가 조회 가능한 기준 API

적합성: 현재 가진 포인트리스트만으로 시작 가능하다.

## Standard

- MVP 전체
- 제조사/모델/통신 맵 evidence 관리
- 장비 템플릿별 필수/선택/금지 포인트 정의
- 포인트 단위, enum, writable 여부, alarm class, trend 권장값 관리
- Haystack tag validation
- Brick class/relationship export 후보 생성
- 현장별 매핑 품질 점수

적합성: 장비 spec DB로 쓸 수 있는 최소 실무 수준이다.

## Enterprise

- Standard 전체
- BACnet live discovery 연동
- Modbus register import/검증
- 시퀀스 오브 오퍼레이션 모델링
- 시뮬레이터용 장비 동작 모델
- AI 매핑 추천/검수 워크플로
- 다중 현장 표준 편차 분석
- RDF/Brick graph export 또는 graph query

적합성: 자동 매핑과 시뮬레이터/AI 제어까지 본격적으로 연결하는 범위다.

## 추천

초기 목표는 Standard의 데이터 모델을 설계하되, 구현은 MVP import와 mapping부터 시작한다. DB 스키마를 MVP만 보고 만들면 장비 spec/evidence/시뮬레이터 요구를 나중에 억지로 붙이게 된다.
