# Seed Brief

- 원문 입력: service-autopilot 자동제어 장비 spec, tag(haystack, brick) 데이터를 정리해서 DB화하고 싶다. NEUROS와 BMS/빌딩 자동제어 시뮬레이터 등에서 함께 사용한다.
- 솔루션 유형: 빌딩 자동제어 장비/포인트 표준 DB 및 태깅 표준화 기반
- 1차 목표: 장비/포인트 표준 대장, Haystack 중심 태깅 표준화
- 후속 목표: 현장 장비 자동 매핑, 제어 로직/AI 분석을 위한 의미 데이터 기반
- 대상 범위: 모든 자동제어 장비. 초기 검증 데이터는 서울캠퍼스 BIOT 포인트리스트 CSV.
- 데이터 출처 후보: 현장 포인트리스트, BACnet object list, 제조사 장비 매뉴얼/카탈로그, 제어 시퀀스 문서, ASHRAE/BACnet/Haystack/Brick 공식 문서.
- 제약: NEUROS 내부에서도 쓰고, 외부 service-autopilot/BMS 시뮬레이터에서도 재사용 가능한 독립 기준 데이터 모델이어야 한다.
- 조사 시점: 2026-07-23
