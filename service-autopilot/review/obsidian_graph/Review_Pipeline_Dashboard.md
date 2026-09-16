# Review Pipeline Dashboard

이 대시보드는 BMS 장비 모델 데이터 추출 파이프라인의 **인간 검증(Human-in-the-loop)** 단계 산출물들을 연결합니다.

## 핵심 검증 산출물 (HTML)
파이프라인의 종착지에는 기계가 추출한 데이터를 사람이 직관적으로 확인할 수 있도록 돕는 렌더링된 검사대(HTML)들이 존재합니다.

- [[Template_Map]] (\	emplate-map.html\): BMS 기본 화면과 장비 포인트 간의 매핑 검증
- [[Point_Verify]] (\point-verify.html\): 벤더 원문 PDF와 추출된 데이터 간의 신뢰성 검증

## 데이터 흐름 (Mermaid Graph)
\\\mermaid
graph TD
    A[Vendor Raw Manual PDF] -->|Extract| B(Extracted Models JSON)
    B -->|Crosscheck| C[[Point_Verify]]
    
    D[Equip Templates JSON] -->|Define UI Concepts| E(BMS UI Concept)
    B -->|Map| F[Model Mappings JSON]
    E -->|Combine| G[[Template_Map]]
    F -->|Combine| G
\\\

## Tags
#BMS #Pipeline #Review #DataVerification
