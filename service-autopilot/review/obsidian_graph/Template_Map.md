# Template Map (BMS 템플릿 검사대)

## 개요
\	emplate-map.html\은 BMS(빌딩 자동제어 시스템)의 기본 화면 템플릿 행(Row)에 각 장비 모델을 골라 붙였을 때, **UI 개념(Concept)이 벤더(Vendor)마다 실제 어떤 이름으로 매핑되는지**를 한눈에 비교하는 검사대입니다.

## 역할 및 목적
- **개념의 파편화 확인:** 정규식이나 이름만으로는 뜻을 완벽히 분리할 수 없습니다. (예: '전력 소모량'이 어떤 벤더는 'kWh Counter', 다른 벤더는 '누적 전력량'으로 표현됨)
- **시각적 검증:** 모델 원문에서 추출된 이름이 BMS UI 템플릿의 의도된 개념과 정확히 매칭되었는지 확인합니다.
- 오작동 및 매핑 누락(Missing concepts)을 방지합니다.

## 입력 데이터 (Sources)
- \data/equip-templates.json\ : BMS 화면에 표시되어야 할 표준 개념과 종류, 단위, 등급 정의
- \data/equip-requirements.json\ : 각 장비군(e.g., e5.rtu, e5.ahu)별 필수 요구사항
- \data/datasets/model-mappings.json\ : 실제 추출된 모델과 템플릿 간의 매핑 데이터

## 렌더러 스크립트
- \	emplate_map.py\

## 연결 문서
- 상위 대시보드: [[Review_Pipeline_Dashboard]]
- 비교 검증 도구: [[Point_Verify]]

## Tags
#Template #Mapping #BMS #UI #Concept
