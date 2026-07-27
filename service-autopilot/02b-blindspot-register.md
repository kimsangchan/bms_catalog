# 블라인드스팟 레지스터 — BMS 장비 스펙 기준 DB

- 작성: 2026-07-27 (A2 INTERROGATE 정본. `02-assumption-pack.md`는 07-23 선행 가정 메모)
- 스캔 범위: 공통 10축 + STRIDE 6범주 + 도메인 프로파일 **P3(관제·SCADA/BMS)** + **P6(데이터 파이프라인)**
- 프로파일 선정 근거: 서비스 유형이 "BMS 기준 데이터 서비스 + 대상 시스템 적용(쓰기)"이므로 P3 필수,
  카탈로그 취입·릴리스·대조가 배치성이므로 P6 적용. P1(엣지)·P4(모바일)·P5(LLM)는 해당 없음.

## 공통 10축

| 축 | 상태 | 처리 | 근거·출처 |
|---|---|---|---|
| 1. 기능 범위·행동 | Clear | — | 스코프 정정(07-27)으로 카탈로그+적용으로 확정. non-goal은 `05-prd.md` 범위 밖 절 |
| 2. 도메인·데이터 모델 | Clear | — | `07-api-contract.md` ERD. 표준/모델/현장/적용 4계층 분리 = D-002 확장 |
| 2a. 단위·정밀도 | Clear | — | 단위는 `bes_unit` FK + 별칭 사전. 실측 근거 O-02·O-03·O-04 (단위 공란 79.6%) |
| 2b. 식별자 정책 | Assumed: 내부 PK `seq`(bigint identity) + 외부 노출 `code`(사람이 읽는 유일키) | — | NEUROS 기존 컨벤션(`seq` + code)과 동형 → 어댑터 매핑 비용 0 |
| 3. 상호작용·UX 플로우 | Partial → Assumed | 관리자용 내부 화면 3개(카탈로그 편집·모델 스펙 편집·적용 계획/미리보기)로 한정. 현장 운영자 화면 없음 | 사용자는 기준 데이터 생산자(사내)다. 외부 사용자 여정 부재 |
| 4. 비기능 품질 | Partial → Assumed | 성능 목표는 카탈로그 조회 p95 < 300ms, 적용 미리보기 1,000포인트 < 5s. 관측성·보안은 A4/A7 | 내부 도구 규모(모델 수백·포인트 수만)이므로 대규모 트래픽 가정 불필요 |
| 5. 통합·외부 의존성 | Clear | — | NEUROS REST(적용), 시뮬레이터(파일 export), 사내 파일서버(evidence 경로). 각 장애 시 동작은 A4 |
| 6. 엣지케이스·실패 처리 | Clear | — | `05-prd.md` 엣지케이스 절 (부분 적용 실패·중복 실행·동결 카탈로그 수정 시도 등) |
| 7. 제약·트레이드오프 | Clear | — | 폐쇄망 현장, 기존 NEUROS 스택(Java 21·Spring Boot·MyBatis·React19), 팀 역량 재사용 |
| 8. 용어·일관성 | Partial → Assumed | 용어 사전을 `05-prd.md`에 고정: 분류/모델/포인트 타입/포인트 프로파일/현장 인스턴스/적용/릴리스 | 실측 O-12에서 "장비명"이 인스턴스·모델·태그번호로 혼용됨을 확인 → 용어 드리프트 위험 실존 |
| 9. 완료 신호 | Clear | — | SC-001~SC-010 전부 pass/fail 판정 가능 (`05-prd.md`) |
| 10. 비용·라이선스 | **Partial → Assumed(주의)** | Haystack(Project Haystack, 오픈) 태그 정의는 참조·재배포 조건 확인 필요. Brick은 BSD 계열. **ASHRAE Guideline 36 본문은 유료 표준 → 시퀀스 테이블에 조항 번호·요약만 저장, 본문 복제 금지** | ASHRAE G36-2024 유료 판매([ASHRAE Store](https://ashrae.org/G36)). 유료 표준 원문 DB 적재는 라이선스 위반 위험 |

## STRIDE 6범주 (요약 — 전수 검토는 `06-architecture.md` 위협모델)

| 범주 | 상태 | 처리 |
|---|---|---|
| S Spoofing | Clear | 대상 시스템별 전용 자격증명 + 등록은 관리자 권한, 오프라인 번들은 서명 검증 |
| T Tampering | Clear | **최상위 위협**: 잘못된 스펙이 현장 BMS에 기록됨 → preview→승인→execute 2단계 + 동결 릴리스 참조 |
| R Repudiation | Clear | `bes_apply_result` 불변 기록 + 적용 시점 카탈로그 릴리스 해시 고정 |
| I Information Disclosure | Clear | evidence 파일 경로는 권한자만, 목록 API는 title/publisher만 노출 |
| D Denial of Service | Clear | 적용 배치 크기 상한 + 대상 시스템 호출 스로틀 + 취소 |
| E Elevation of Privilege | Clear | 스코프 분리 `bes:apply:preview` ≠ `bes:apply:execute`, 릴리스 동결은 별도 스코프 |

## P3. 관제·SCADA/BMS 프로파일

| 항목 | 상태 | 처리 | 근거 |
|---|---|---|---|
| 폐쇄망 | Missing → **Assumed** | 기준 DB는 사내 중앙 1곳. 현장에는 **서명된 오프라인 카탈로그 번들(zip: JSON export + SHA-256 + 서명)** 반입 → NEUROS가 import. 외부 CDN·폰트 의존 0 | NEUROS 자체가 폐쇄망 단일 JAR 배포(프로젝트 CLAUDE.md). 현장에 신규 DB 엔진을 심지 않는 편이 운영비가 낮다 |
| 실시간성 | Clear(해당없음 — 근거) | 기준 DB는 실시간 데이터 경로에 없다. 적용은 배치성 프로비저닝 | 스펙 카탈로그는 설계 시점 데이터. 값 수집은 NEUROS 담당 |
| 알람 폭주 | Partial → **Assumed** | 카탈로그가 **알람 기본값(등급·상하한·데드밴드)** 을 공급하되, 적용 시 폭주 방지 위해 "알람 활성화"는 기본 off, 명시 승인 시만 on | 실측 O-07: 현장 export의 `ALARM_LV` 비영값 0건 → 현장에 알람 설정이 사실상 없다. 대량 주입 시 폭주 위험 |
| 프로토콜 | Clear | BACnet(IP/MSTP) · Modbus TCP/RTU · LonWorks · 전용 · OPC-UA를 `bes_model_protocol`로 모델링. **BACnet 오브젝트 타입 enum은 NEUROS 코드와 불일치** → 매핑 테이블 필수 | BACnet 표준 enum: AI=0, AO=1, AV=2, BI=3, BO=4, BV=5, **MSI=13, MSO=14, MSV=19** ([Chipkin BACnet Object Types](https://docs.chipkin.com/articles/bacnet-object-types-properties-reference/), [OPC UA for BACnet ObjectTypeEnum](https://reference.opcfoundation.org/BACnet/v200/docs/10.4.21)). NEUROS는 6/7/8=MSI/MSO/MSV (`HAYSTACK_RECOMMEND_SPEC.md`) → 0~5만 일치 |
| 이력 증가 | Clear(해당없음 — 근거) | 시계열 값을 저장하지 않는다. 스펙·카탈로그·적용 이력만 (행 수 만 단위) | 값 이력은 NEUROS의 책임 경계 |
| 무중단 | Partial → **Assumed** | 기준 DB 정지는 현장 관제에 영향 없음(설계 시점 도구). 적용 실행 중 중단은 재개 가능한 멱등 배치로 처리 | 적용은 Idempotency-Key + 항목별 결과 기록 → 중단 후 재실행 안전 |

## P6. 데이터 파이프라인 프로파일

| 항목 | 상태 | 처리 | 근거 |
|---|---|---|---|
| 멱등성 | Clear | 적용 실행은 `Idempotency-Key` 필수 + `bes_apply_result` 대상 참조 유일 제약. 취입은 (batch, file, row) upsert | Stripe 멱등성 방식(스킬 A5 규약). SC-005로 검증 |
| 재처리·백필 | Clear | 카탈로그는 릴리스 버전별 동결 → 과거 버전으로 재적용 가능. 취입 배치는 배치 단위 재실행 | 릴리스 동결은 ICT 모듈의 "확정 후 불변, 정정은 새 revision" 패턴과 동형 (프로젝트 CLAUDE.md) |
| 지연 데이터 | Clear(해당없음 — 근거) | 마감·정산 개념 없음. 스냅샷은 라벨로 구분 | 실측 O-11: 스냅샷 축이 이미 데이터에 존재(월별/기존·추가) |
| 스키마 진화 | Partial → **Assumed** | 취입기는 **헤더 서명(header signature)** 으로 포맷을 판별하고, 미등록 서명은 중단 후 알림 | 실측: 헤더 서명 2종(셔블 37열 898파일 / Niagara 12열 129파일)로 정확히 갈린다 |
| 정합성 검증 | Clear | 취입 후 파일 행수 ↔ 적재 행수 대사, 적용 후 대상 시스템 오브젝트 수 ↔ preview 예측 수 대사 | SC-004(preview=실제 차이 0) |
| 알림 실패 | Partial → **Assumed** | 적용·릴리스·취입 실패는 사내 알림 채널 1곳으로 발송, 미발송 감지는 A7에서 설계 | 내부 도구이므로 데드맨 스위치는 A7로 이연 |

## 도메인 고유 항목 (프로파일 미수록 — 임시 프로파일)

기존 프로파일에 없는 "장비 스펙 카탈로그" 고유 함정. 2회 이상 재등장하면 체크리스트에 승격한다.

| 항목 | 상태 | 처리 | 근거 |
|---|---|---|---|
| 스펙 출처 부재 | Clear | 모델 스펙 속성·모델 포인트는 `evidence_seq` 또는 명시적 `unverified` 플래그 필수 (SC-007) | 실측 5절: 이름에서 모델을 확정할 수 없음(`AH-114`=태그번호 vs `UC-800`=모델) |
| 표준 vs 현장 오염 | Clear | 표준 계층(`bes_*` 카탈로그)과 현장 인스턴스를 물리적으로 분리 (D-002) | 실측 O-12: 현장 이름 규칙이 원천마다 다름 → 표준에 섞이면 회복 불가 |
| 태그 사전 결손 | **Missing → Assumed** | NEUROS `haystack-tags.json`(equip 178/property 368/role 8 = 554)을 승격 시딩하되 **결손 보강 필수** | 실물 확인: `pump`·`fan`·`damper`·`valve`는 equip에 **없고** property에만 있음. 실제 존재 형태는 `pump-motor`·`supply-fan`·`return-fan`·`exhaust-fan`·`elec-meter`·`flow-meter`·`two-way-valve`·`airTerminalUnit`. `entering`/`leaving`(입·출수 온도)은 **아예 없음** |
| 유료 표준 복제 | **Missing → Assumed(주의)** | 제어 시퀀스는 **조항 참조 + 자체 요약 + 파라미터**만 저장. 원문·표 복제 금지 | ASHRAE Guideline 36은 유료 표준(현행 **G36-2024**, 2021판 대비 addenda 23건, 2026-02 Addendum a) ([ANSI Webstore](https://webstore.ansi.org/standards/ashrae/ashraeguideline362024)) |
| 온톨로지 버전 드리프트 | Partial → Assumed | `bes_tag.source`에 표준명+버전을 기록하고 릴리스마다 고정. Brick은 semver·약 6개월 주기 minor 릴리스라 버전 명시 없이는 재현 불가 | [Brick 공식 문서](https://docs.brickschema.org/brick/concepts.html) / [Brick GitHub](https://github.com/BrickSchema/Brick) — 공개 문서 기준 v1.1 계열이 참조본. **최신 릴리스는 릴리스 페이지에서 확인 후 확정할 것**(본 조사에서 2026년 릴리스 확증 못 함) |
| 적용 후 되돌리기 | **Missing → Assumed** | 적용은 생성 대상 목록을 결과에 남기고, 롤백은 "생성분 삭제" 계획을 역산해 제공. 단 현장에서 값이 쓰인 오브젝트는 삭제 대신 비활성 | 잘못된 대량 적용은 현장 관제 화면을 오염시킨다. 되돌릴 수 없으면 아무도 실행 버튼을 못 누른다 |
| 장비 1대 = 포인트 N개 폭 | Clear | 프로파일에 required/recommended/optional 등급 → 적용 시 등급 선택 | 실측: 장비 인스턴스 955종 대비 포인트 22,502 → 인스턴스당 평균 23.6점, 최대 356점 |

## 질문 배치 (최대 5) — 2026-07-27 제시, 4문항

### Q1. 표준 장비 분류 체계의 폭
| 옵션 | 내용 | 근거·트레이드오프 |
|---|---|---|
| A (추천) | 넓은 8대 분류로 시작 | 실측 장비군 분포를 바로 수용, 하위 세분류는 뒤에 |
| B | Haystack equip 태그 계층을 분류로 사용 | 이중 정의 없음, 국내 현장 용어와 어긋남 |
| C | ICT 법정 34분류와 정렬 | 유지보수 업무엔 맞으나 자동제어 스펙엔 입도 불일치 |

→ 답: **A 변형 채택** — "모델별 spec까지 필요하므로 상당히 디테일한 분류가 필요. **공조/HVAC부터** 하자"
→ 반영: 도메인은 HVAC로 좁히고 **분류 깊이는 3레벨 + 모델 계층**까지 (D-005·D-006)

### Q2. 문자열 보정 사전을 DB에 둘 것인가
| 옵션 | 내용 | 근거·트레이드오프 |
|---|---|---|
| A (추천) | DB 테이블로 포함 | 매핑 근거 추적 가능, raw는 원본 보존 |
| B | 코드 상수·설정 파일 | 단순하나 현장별 신규 오타마다 배포 필요 |

→ 답: **A** → 반영: `bes_unit_alias` + `bes_normalization_dict` (D-007)

### Q3. 제조사 원천 문서 저장 범위
| 옵션 | 내용 | 근거·트레이드오프 |
|---|---|---|
| A (추천) | 경로+해시+출처 메타만 | 저작권·용량 회피, 무결성은 해시로 |
| B | 원본 파일 보관 | 오프라인 열람 편하나 재배포 문제 |
| C | 추출 텍스트/표만 | 검색 유리하나 원본 대조 불가 |

→ 답: **A** → 반영: `bes_evidence`(원본 바이너리 미보관) (D-008)

### Q4. 다음 산출물
→ 답: **PRD + ERD/스키마 설계** → 반영: A3~A5 즉시 작성 (본 배치 이후 진행)

### 무응답·미질문 처리
승격 후보였으나 5문항 한도·배치 1회 규칙으로 묻지 않고 가정 채택한 항목: **A-06(PostgreSQL 단일·중앙 1인스턴스)**,
**A-07(NEUROS REST 경유 적용)**, **A-08(preview→승인→execute 2단계)**. 세 항목은 `README.md`에
"사용자 확인이 필요한 최상위 가정"으로 명시했다.

## 반영 기록

| 질문 | 영향받은 산출물 | decision-log |
|---|---|---|
| 스코프 정정(사용자 지시) | `README.md`, `05-prd.md` 전체, `03-scope-options.md` 대체 | D-005 |
| Q1 | `05-prd.md` 범위·분류 깊이, ERD `bes_equip_category`·`bes_equip_model` | D-005, D-006 |
| Q2 | ERD `bes_unit_alias`·`bes_normalization_dict` | D-007 |
| Q3 | ERD `bes_evidence`, SC-007 | D-008 |
| Q4 | A3~A5 착수 | — |
| 미질문 가정 | `06-architecture.md` 배포·적용 경로 | D-009, D-010, D-011 |
