# -*- coding: utf-8 -*-
"""소스 레지스트리 — 벤더별로 '문서를 어떻게 찾아내는가'를 규칙으로 적는다.

벤더 하나를 추가한다는 것은 여기에 항목 하나를 넣는 일이다.
수집기(collect.py)가 이 규칙을 읽어 문서를 열거·내려받는다.

enumerate 방식
  series   번호×날짜 조합을 훑는다 (Trane 포인트리스트처럼 문서번호가 연속인 경우)
  list     URL을 직접 나열 (소수의 문서)
  page     웹페이지를 열어 링크를 긁는다 (Belimo File Archive처럼)
"""

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

# Trane 공개 문서 저장소 — 포인트 리스트와 제품 카탈로그가 같은 곳에 있다.
ELIB = "https://elibrary.tranetechnologies.com/public/commercial-hvac/Literature/"
ELIB_CATALOG = ELIB + "Product%20Catalog/"

# JCI/York BAS 포인트 리스트 56건 — docs.johnsoncontrols.com khub.
# 목록의 출처는 문서 카탈로그 스냅샷(data/haystack/_jci_docs.json, 9,142건)에서
# 포인트 리스트 계통만 고른 것이다. khub URL 은 끝이 전부 'content' 라 원 이름
# 기준 rename 이 성립하지 않는다 → collect.local_name 이 **URL 전체**도 열쇠로 받는다.
# (문서ID, 사이트, 저장 이름) 한 줄 = 문서 하나.
JCI_BAS_POINTS = [
    ("ZVOgU4MVClTr1wstBh3m2A", "chillers",
     "JCI_AWHP-AirWaterHeatPump.pdf"),   # AWHP Air Water Heat Pump E-Link (Rev C) Non-OptiView Based Equipment
    ("OQCjzS3A0ZVQ9QBqSlanSQ", "chillers",
     "JCI_BasildonRecipMicroPanel-II-(RevJ-01).pdf"),   # Basildon Recip II E-Link (Rev_J_01) Non-OptiView Based Equipment
    ("BIOPM0nRZnUk75tsUSvUTA", "chillers",
     "JCI_CR-BAS-SC-EQ-Rev1.3.pdf"),   # CR Points List SC-EQ (Rev 1.3) OptiView Based Equipment
    ("bu7Kg~7kuuMB61HkthX_2A", "chillers",
     "JCI_ECO2-IPU-LONandN2verJ-03.pdf"),   # YPAL (ECO2) LON and N2 E-Link Point Maps. The ECO2 product has Native BACnet M
    ("q6LHnNOzMSDLOmZUbI44Ug", "chillers",
     "JCI_ECO2-IPU-NativeBACnetModbus.pdf"),   # Series 100 ​IPU 1 Native BACnet and Modbus
    ("5wtWGe_rjmetBNFyP2PvFQ", "chillers",
     "JCI_Frick-LS-RWBScrew(RevJ-01).pdf"),   # Frick LS Screw E-Link (Rev_J_01) RWB Microboard only. For the latest points ma
    ("Mw_EYd3yJkMrpOG1qLIzGw", "chillers",
     "JCI_FrickQuantum3-4(RevJ-01).pdf"),   # Frick Quantum E-Link (Rev_J_01) For pre 2000 Quantum panels only. For later ve
    ("4BMl7oBe1jFhGRpk35DAvQ", "chillers",
     "JCI_RecipChillers(RevJ-02).pdf"),   # YCAJ, YCAZ, YCWZ, YCWJ, YCRJ, YCWK, YCRR Reciprocating Chiller E-Link (Rev_J_0
    ("47mW1GA_AXbFLIz2QICYeQ", "chillers",
     "JCI_Scroll-BAS-SC-EQRev2.4.pdf"),   # Scroll BAS SC-EQ (Rev 2.4​) Non-OptiView Based Equipment
    ("oBPJz4ijvAYm6msOUI4wyg", "chillers",
     "JCI_ScrollBAS.pdf"),   # YCRL, YCUL, YCAL, YLAA, YLPA, YLUA, YCWL Scroll BAS E-Link Non-OptiView Based 
    ("PqH6~F3kNniq~6xHrGxQAQ", "chillers",
     "JCI_ScrollNative.pdf"),   # YCAL, YCUL, YCWL, YLAA, YLUA Scroll Data Map Native BACnet and N2 Modbus
    ("38yjzoNRyJnOMntX63dCBA", "ductedsystems",
     "JCI_Sunline3000(RevJ-01).pdf"),   # Sunline 3000 Rooftop E-Link (Rev_J_01) Non-OptiView Based Equipment
    ("7Lqu5MKCH2OtvX7jbB1SnQ", "chillers",
     "JCI_YCARAirCooledRecip(RevJ-01).pdf"),   # YCAR Air Cooled Reciprocating E-Link (Rev_J_01) Non-OptiView Based Equipment
    ("CBGzdc1y3fiy~RrOPBYfjQ", "chillers",
     "JCI_YCASAir-CooledScrew(RevJ-03).pdf"),   # YCAS Air Cooled Screw E-Link (Rev_J_03) Non-OptiView Based Equipment
    ("F5MxE~19WRFrMvSKgqKvYA", "chillers",
     "JCI_YCAV-YCIV-BAS-(RevK-03g).pdf"),   # YCAV and YCIV 1/2 and 3/4 Compressor Models E-Link (Rev K _03g) Non-OptiView B
    ("DsvsbvlZNgkCrndB1NvZpg", "chillers",
     "JCI_YCAV-YCIVNative.pdf"),   # YCAV, YCIV Native BACnet, Modbus, N2 Data Map
    ("VJ52N97ZFmW0I2WpA8dC3A", "chillers",
     "JCI_YCWS-YCRS-Water-CooledScrew-F(RevJ-01).pdf"),   # YCWS and YCRS Water Cooled Screw E-Link (Rev_J_01) Non-OptiView Based Equipmen
    ("ryVLb5Rnf89iVUfsCgygZw", "chillers",
     "JCI_YD-BAS-SC-EQ-Rev2.4.pdf"),   # YD Points List SC-EQ (Rev 2.4)​ OptiView Based Equipment
    ("l7pWhFILYevobk9HZKrdBw", "chillers",
     "JCI_YD-OptiviewBAS(RevK-06f).pdf"),   # YD OptiView E-Link (Rev K_06f) OptiView Based Equipment
    ("z3TBb3eYKkbj5mmf9_7e1w", "chillers",
     "JCI_YGED-YB-MicroPanel-II-(RevJ-01).pdf"),   # YG and YB Micropanel with 1065 Boards E-Link (Rev_J_01) Non-OptiView Based Equ
    ("MgPyIEusbCBvjQ2NPPH0uw", "chillers",
     "JCI_YIA-BAS-SC-EQ-Rev1.1.pdf"),   # YIA Points List SC-EQ (Rev 1.1) OptiView Based Equipment
    ("9LF9qQ7NhF9Hi4mdLkiTHg", "chillers",
     "JCI_YK-BAS-SC-EQ-Rev2.9.pdf"),   # YK Points List SC-EQ (Rev 2.9) OptiView Based Equipment
    ("eGZ6QFSLFZ_wTujNgwRGEA", "chillers",
     "JCI_YK-MicroPanel-II-(RevJ-01).pdf"),   # YK Micropanel II with 1065 Boards NOT OptiView E-Link (Rev_J_01) Non-OptiView 
    ("9K1_I8TTfuZWaiBiiZxM8w", "chillers",
     "JCI_YK-OptiviewBAS(RevK-04d)EM-SSS.pdf"),   # YK OptiView BAS E-Link (Rev K_04d) EM and SSS Data Maps OptiView Based Equipme
    ("Fgue2zdfR4thfSDzUfAyHQ", "chillers",
     "JCI_YK-OptiviewBAS(RevK-04d)VSD.pdf"),   # YK OptiView BAS E-Link (Rev K_04d) VSD Data Maps​ OptiView Based Equipment
    ("WBwYCBJ~KihreRSMUxcxcQ", "chillers",
     "JCI_YKEP-BAS-SC-EQ-Rev2.9.pdf"),   # YKEP Points List SC-EQ (Rev 2.9​) OptiView Based Equipment
    ("dYgzQbcqoLyEPCfcDOnVUA", "chillers",
     "JCI_YKEP-OptiviewBASEM-SSS.pdf"),   # YKEP OptiView BAS EM and SSS E-Link (Rev K_01) OptiView Based Equipment
    ("Aa7Qo2V_pQ9Etr5UT7EJ4Q", "chillers",
     "JCI_YKEP-OptiviewBASVSD(RevK-01).pdf"),   # YKEP OptiView BAS VSD E-Link (Rev K_01) OptiView Based Equipment
    ("cCyKNapISIvyShxh1Z~l5g", "chillers",
     "JCI_YMAE_2_Pipe_Equipment_Modbus_Bacnet_Points_list_Rev1.0.pdf"),   # YMAE Points List Two-Pipe Equipment
    ("DAKAK2ryzuHrZbBA1Ny6_A", "chillers",
     "JCI_YMAE_4_Pipe_Equipment_Model_Modbus_YMAEQ_Rev1.1.pdf"),   # YMAE Points List Four-Pipe Equipment
    ("5I6BffzkZybYzhNWLkSq1w", "chillers",
     "JCI_YMC2-BAS-SC-EQ-Rev2.11.pdf"),   # YMC2 Points List SC-EQ (Rev 2.11) OptiView Based Equipment
    ("gk4oFkQpP27Gpe5ruu31kA", "chillers",
     "JCI_YMC2-OptiviewBAS(RevK-05b).pdf"),   # YMC2 OptiView E-Link (Rev K_05b) OptiView Based Equipment
    ("ISru5gO~hseNJRaG8uHiHg", "chillers",
     "JCI_YR-(OptiView)-BAS-SC-EQ-Rev1.2.pdf"),   # YR (OptiView) Points List SE-EQ (Rev 1.2) OptiView Based Equipment
    ("qYwF7xrXqmQnYAS5BD78MA", "chillers",
     "JCI_YR-OptiView(RevK-03).pdf"),   # YR OptiView E-Link (Rev_K_03) OptiView Based Equipment
    ("S3FYA_47fO460A0f3Oha9w", "chillers",
     "JCI_YS-RotaryScrew(RevJ-02).pdf"),   # YS Rotary Screw with 'older' 940 or 1065 board E-Link (Rev_J_02) Non-OptiView 
    ("ozVCeJT3qZBg4EZG7eobIQ", "chillers",
     "JCI_YS-UnifiedOptiView(RevK-03)BETA.pdf"),   # YS with Heat Pump option using Unified Screw firmware. OptiView Based Equipmen
    ("hSI0v36JJxo5NkdS0gNL0w", "chillers",
     "JCI_YS-YN-BAS-SC-EQ-Rev2.3.pdf"),   # YS and YN Points List SC-EQ (Rev 2.3) OptiView Based Equipment
    ("eJKAA5RbxwVvTPF__h2dHA", "chillers",
     "JCI_YS-YN-OptiView(RevK-03).pdf"),   # YS and YN OptiView E-Link (Rev_K_03) OptiView Based Equipment
    ("xvSi0e3Kwnf7B~5daaWaOw", "chillers",
     "JCI_YSAA-BAS.pdf"),   # YSAA BAS (ISN) E-Link Non-OptiView Based Equipment
    ("p4EqvB3xJO6bhqQzS114Tw", "chillers",
     "JCI_YSAANative.pdf"),   # YSAA Native BACnet MS/TP, Modbus, N2 Data Map
    ("xdkEW8x~Tlf_XJgFpLpcbA", "chillers",
     "JCI_YST-BAS-SC-EQ-Rev1.2.pdf"),   # YST Points List SC-EQ (Rev 1.2) OptiView Based Equipment
    ("gb8ypitRHG4X5jrdL35ABQ", "chillers",
     "JCI_YST-Optiview(RevK-03).pdf"),   # YST OptiView E-Link (Rev_K_03) OptiView Based Equipment
    ("qySCXKFcGaJK93xZ8jJBmA", "chillers",
     "JCI_YT-BAS-SC-EQ-Rev2.5.pdf"),   # YT Points List SC-EQ (Rev 2.5) OptiView Based Equipment
    ("4hfGvwkP0RBfYstZASUP3Q", "chillers",
     "JCI_YT-MicroPanel-I-II-(RevJ-01).pdf"),   # YT Micropanel I and II with 776,940 and 1065 Boards E-Link (Rev_J_01) Non-Opti
    ("p2OiyENC3XS2iIF4~nNx7Q", "chillers",
     "JCI_YT-OptiView(RevK-03b).pdf"),   # YT OptiView E-Link (Rev K_03b) OptiView Based Equipment
    ("Cxf1tNmYudSglP~8DcXK7g", "chillers",
     "JCI_YVAA-StyleB-BAS-SC-EQ-Rev1.8.pdf"),   # YVAA Style B BAS SC-EQ (Rev 1.8) Non-OptiView Based Equipment
    ("nHwkT9FiUp_csGrw6Q~_wA", "chillers",
     "JCI_YVAA-YVFA-YAGK(YT3)BAS-SC-EQRev1.8.pdf"),   # YVAA, YVFA, YAGK (YT3) BAS SC-EQ (Rev1.8) Non-OptiView Based Equipment
    ("HryI9wyjlbuFpbuVIk9XrA", "chillers",
     "JCI_YVAA-YVFA-YAGK-BAS-E-Link2021-04-16.pdf"),   # YVAA, YVFA, YAGK BAS E-Link Non-OptiView Based Equipment
    ("v3G3YemU0Ic3bTVhJD0MOw", "chillers",
     "JCI_YVAA-YVFA-YAGK-BAS-SC-EQ-Rev2.16.pdf"),   # YVAA, YVFA, YAGK BAS SC-EQ (Rev 2.16)​​ Non-OptiView Based Equipment
    ("Ul95oD3_Tkawi3qW9DkIug", "chillers",
     "JCI_YVAA-YVFA-YAGKNative.pdf"),   # YVAA, YVFA, YAGK Native BACnet and Modbus N2 Data Map
    ("QO052Dm251t6v1FTiH8_iQ", "chillers",
     "JCI_YVAM-BAS-SC-EQ-Rev1.5.pdf"),   # YVAM Points List SC-EQ (Rev 1.5) OptiView Based Equipment
    ("GBppk5iQWBiKzUyxqfeOFA", "chillers",
     "JCI_YVWA-BAS-SC-EQ-Rev2.1.pdf"),   # YVWA BAS SC-EQ (Rev 2.1)​ Non-OptiView Based Equipment
    ("zbueaePe6Wu3YKVBu~fp3A", "chillers",
     "JCI_YVWA-BAS.pdf"),   # YVWA BAS E-Link Non-OptiView Based Equipment
    ("TWAOtmjMD~xxMBlTMLA2QQ", "chillers",
     "JCI_YVWH-YVWE-YGWH-BAS-SC-EQ-Rev1.0.pdf"),   # YVWH, YVWE, YGWH BAS SC-EQ (Rev 1.0) Non-OptiView Based Equipment
    ("ZAyi0nhZO6~_x09W4LLALw", "chillers",
     "JCI_YZ-BAS-SC-EQ-Rev1.7.pdf"),   # YZ Points List SC-EQ (Rev 1.7) OptiView Based Equipment
    ("RNezPwBMi1SWkNtA2cBRwg", "chillers",
     "JCI_YZD-BAS-HMI-Rev1.4.pdf"),   # YZD BAS Protocol List Rev 1.4
    # ── 9번째 계통: 게이트웨이 (2026-08-21 추가) ──────────────────────────────
    # 앞의 56건은 전부 '장비가 직접 내보내는' 목록이다. 이것은 장비의 N2 를
    # BACnet/IP·Modbus TCP 로 **바꿔 주는 액세서리 키트**(FieldServer QuickServer)라
    # 표가 게이트웨이 설정표 모양이고, 그래서 파서 넷이 다 못 잡았다.
    # ⚠ 같은 문서의 번역본 6건(pt·es·de·nl·it·fr)이 포털에 함께 있다 — 내용이
    #   같아 등록하지 않는다. 문서ID 는 ingest_jci.TRANSLATIONS 에 근거로 남겼다.
    ("bdk7s53yQ5tftUD6MrJq9g", "chillers",
     "JCI_YKN2Open-BMS-Gateway.pdf"),   # YKN2Open BMS BACnet/IP and Modbus TCP/IP Installation and User Guide
    # ── 10번째 계통: 통신 카드 자신의 설정 포인트 (2026-08-31 추가) ────────────
    # 위 20건의 'SC-EQ' 문서는 **냉동기가 SC-EQ 카드를 통해 내보내는** 목록이다.
    # 이 문서(SI0371)는 다르다 — 표에 담긴 6점이 **카드 자신의 설정값**이다
    # (BACnet 장치 이름·인스턴스 ID·문자 인코딩·단위계·붙어 있는 냉동기 기종).
    # 머리글이 'Point name | BACnet | Modbus | N2 | Description' 으로 통째로 달라
    # 기존 파서 아홉이 다 못 잡았다. 파서는 vendor_jci_sceq_config.py.
    # ⚠ 같은 6점이 'SC-EQ Communication Card Installation Instructions'
    #   (2P~o78Hw6Zd~F~_z12AEMg, 60쪽 매뉴얼의 46쪽 Table 8)에도 있다. 값 표(44종)를
    #   가진 이쪽만 판으로 삼는다 — 그쪽은 "Refer to SI0371." 로 값 표를 여기 넘긴다.
    #   대조 결과와 문서ID 는 ingest_jci.CORROBORATED 에 근거로 남겼다.
    # ⚠ khub 카탈로그의 prodname 이 냉동기 11종이라 첫 값('YCAL Scroll Chiller')을
    #   제품으로 삼으면 카드의 설정 포인트가 YCAL 냉동기 목록으로 들어간다 —
    #   ingest_jci.PROD_OF 가 문서가 밝히는 제품으로 되돌린다.
    ("9cg6yK~zvn2rx75l2aehJA", "chillers",
     "JCI_SC-EQ-Firmware-3.0.0.1114-SI0371.pdf"),   # YVAA, YVFA, YVWA, YCAV, YCIV, YCAL, YCUL, YCRL, YLAA, YLAE, YLUA SC-EQ Firmware 3.0.0.1114, Control Panel
]
_JCI_KHUB = "https://docs.johnsoncontrols.com/%s/api/khub/documents/%s/content"

# JCI Roomtop RTC/RTH 기술 가이드 2건 — **정격이 실린 유일한 JCI 문서**다.
# 포털 제목은 스페인어인데 본문은 영문이고, 냉동기 포털의 'Rooftop Packaged Unit'
# 분류에 들어 있다. 같은 제품을 YKN2Open 게이트웨이가 BAS 로 내보낸다(짝 규칙).
JCI_RTH_SPECS = [
    ("xBWNamFiscpTTg0ZZWTl1A", "chillers",
     "JCI_RTH-K_TechnicalGuide.pdf"),   # Bombas de calor horizontales compactas RTH-07K a 30K Guía técnica
    ("GqRBmNpcEJwNdfo7VQqTEg", "chillers",
     "JCI_RTH-L_TechnicalGuide.pdf"),   # Bombas de calor horizontales compactas RTH 07L a 30L
]

# JCI 옥상형·자립형 IOM 16건 — 포인트 표가 **매뉴얼 본문**(대개 p110~190대)에 묻혀 있다.
# 제목에는 낌새가 없어 제목 스캔으로는 못 찾는다. 본문 전수 스캔(scan_jci.py)이
# 1,492건에서 골라낸 것이다 — 근거는 data/jci-body-scan.json.
JCI_IOM_POINTS = [
    ("xLE48mA5godfHZjcnWpzXg", "ductedsystems",
     "JCI_IOM_100.50-NOM3.pdf"),
    ("~6kOXz2TlqNoTDiKhe4N5w", "ductedsystems",
     "JCI_IOM_100.50-NOM10.pdf"),
    ("NM9Ffc7gf1w9ZMGJ4IEBhQ", "ductedsystems",
     "JCI_IOM_100.50-NOM11.pdf"),
    ("jHl7DLBfzBwL8EpKbeMhag", "ductedsystems",
     "JCI_IOM_100.50-NOM8.pdf"),
    ("2DuEps2tmbiJza~RoblMpQ", "ductedsystems",
     "JCI_IOM_100.50-NOM4.pdf"),
    ("PzyUqnwmpibAZ5RrpmdAQA", "ductedsystems",
     "JCI_IOM_100.50-SU8.pdf"),
    ("PwDHFbfBgQxp4HQ4ucu1fw", "ductedsystems",
     "JCI_IOM_100.50-NOM5.pdf"),
    ("SGq_ET2snQgUpiWEkwLe9Q", "ductedsystems",
     "JCI_IOM_100.50-NOM9.pdf"),
    ("_~G86KWmcNAwaza1eWuLog", "ductedsystems",
     "JCI_IOM_100.50-NOM12.pdf"),
    ("BpB59IccLWhzwcdWvOEhIg", "ductedsystems",
     "JCI_IOM_145.05-FA2.pdf"),
    ("rnPJfvwHD2q52d5PbSnh6w", "ductedsystems",
     "JCI_IOM_5276178-jim-e-0119.pdf"),
    ("ZgIshwasfGQR32HXAn9ytQ", "ductedsystems",
     "JCI_IOM_TPM3-NOM1.pdf"),
    ("Ck5Q_ooGFgSVlyjx31b2hg", "ductedsystems",
     "JCI_IOM_TPM2-NOM1.pdf"),
    ("hxRGm93wCa~o8RhAHCHuMg", "ductedsystems",
     "JCI_IOM_TPM2-NOM2.pdf"),
    ("3AypYHL6KoR916FxgB5XVQ", "ductedsystems",
     "JCI_IOM_145.05-NOM3.pdf"),
    ("~kxYAglMx7q8o4OKJTy5DA", "ductedsystems",
     "JCI_IOM_YRK3-NOM1.pdf"),
    # L-Series 수냉 자립형(LSWU/LSWD/LSWF) IPU2 — 본문 스캔이 뒤늦게 골라냈다.
    # Table 42(p172~181) 165행. 근거는 data/jci-duct-verdict.json.
    ("2clxIXbzWLHpg~aPscPCsA", "ductedsystems",
     "JCI_IOM_145.05-NOM7.pdf"),
]

# JCI 공조기(airhandling) 포털 — 유닛 제어반 Modbus 레지스터 표를 품은 문서.
# 236건을 본문까지 전수로 훑어 고른 것이다(data/_air_verdict.json).
# ⚠ 본 스캔은 이 표를 **못 찾았었다** — 아는 열 이름이 'REGISTER ADDRESS' 하나뿐이라
#   옛 문턱(한 쪽에 표식 2종)을 못 넘었다. scan_jci.page_is_table 을 고치고서야 잡혔다.
# YKH 와 YKL 은 제품이 다른데 157행이 글자까지 똑같다(같은 제어반). 같은 목록을 제품
# 수만큼 복제하지 않는다 — 주 제품에 붙이고 나머지는 interfaces[].appliesTo 로 밝힌다.
JCI_AIR_POINTS = [
    ("K38KiK3JQojXa44D3dskiA", "airhandling",
     "JCI_AIR_YKL-lowprofile-ahu.pdf"),
    ("E7QAAqUX0MgQa81lO5NROg", "airhandling",
     "JCI_AIR_YKH-heat-recovery.pdf"),
]


# JCI 공조기 포털의 Siemens APOGEE P1/FLN 포인트 데이터베이스.
# AYK550(YORK 브랜드 ABB 인버터) 매뉴얼 한 권에 표가 셋 섞여 있다 —
#   9열 FLN 포인트 목록(이것) · 4열 리포트 7종(부분집합) · Modbus 4xxxx 표.
# 리포트를 포인트로 세면 안 된다. 고유 번호 85개가 전부 9열 목록 안에 있다.
# 1-150 HP 판은 이 판과 185/185 행 전문 일치라 담지 않는다(appliesTo 로 밝힌다).
JCI_FLN_POINTS = [
    ("oth6dFMk01VNpCVxNTvXJQ", "airhandling",
     "JCI_AIR_AYK550-fln.pdf"),
]


# 취입하지 않고 **대조에만** 쓰는 원문. 판으로 삼지 않지만 재현은 돼야 한다 —
# 시험이 스캔 임시 폴더의 파일을 읽고 있다가 재훑기가 그것을 지우자 조용히
# skip 으로 바뀌었다(실패가 아니라 커버리지가 준 것이라 총계로는 안 보인다).
# 근거 관계는 ingest_jci.CORROBORATED 에 적혀 있다.
JCI_CORROBORATION = [
    ("2P~o78Hw6Zd~F~_z12AEMg", "chillers",
     "JCI_SC-EQ-Card-Install-450.50-N1.pdf"),
]


# Verasys VEC100 Generic RTU Controller 응용 노트 5종.
# 덕트 포털을 **고친 문턱으로 다시 훑어** 나왔다 — 옛 문턱은 이 표를 버렸다.
# 다섯이 재수록이 아니다: 쌍별 겹침 64~96%, 총 1,141행 → 고유 359 (조사 실측).
# 하드웨어는 다섯 다 같은 LC-VEC100-0 이고 응용(난방·냉방 조합)만 다르므로
# 모델 하나에 판 다섯으로 담는다.
# ⚠ 이 표에는 **주소 열이 없다** — 매핑에 바로 못 쓰는 목록이다(계통 note 참조).
JCI_VEC100_POINTS = [
    ("HRkXqkar~UGfQYaDLNyt9g", "ductedsystems",
     "JCI_VEC100_ModHeat-StgCool.pdf"),
    ("X8u4VJtz2FVqimqlA0aeAg", "ductedsystems",
     "JCI_VEC100_StgHeat-StgCool.pdf"),
    ("lQwfdioPna0dkLOWucNrrg", "ductedsystems",
     "JCI_VEC100_HeatPump.pdf"),
    ("giiRvbxi0uOPF9g9oiwdGg", "ductedsystems",
     "JCI_VEC100_StgHeat-ModCool.pdf"),
    ("LzKJ8ISx2qUGoVkew3V_Dg", "ductedsystems",
     "JCI_VEC100_ModHeat-ModCool.pdf"),
]


SOURCES = [
    {
        "id": "gastron-gas-detector",
        "vendor": "가스트론(GASTRON)",
        "kind": "매뉴얼(Modbus 레지스터)",
        "note": "현장 가스감지기 32대가 쓰는 다채널 수신반 GTC-200A. 공식 자료실 게시판"
                "(board_data/manual)에 국문 매뉴얼이 직접 걸려 있다. 8.1 RS485 MODBUS 절에 "
                "농도값(3xxxx)·상태비트(1xxxx) 레지스터가 있는데 **행이 아니라 식**이다 — "
                "'Channel-n 농도값 = 30000+n', 상태 = 10001+((n-1)*8). 채널 수만큼 펼쳐 "
                "저장할 일이 아니라 식으로 저장한다(Daikin DMS502B71 과 같은 부류).",
        "enumerate": "list",
        "urls": [
            "https://gastron.com/home/download.php?ps_db=manual&ps_boid=73&ps_file=1&fname_text=board_data/manual/GTC_200A_%B1%B9%B9%AE%B8%C5%B4%BA%BE%F3_R1.0.pdf",
        ],
        # 원 이름이 EUC-KR 한글이라 그대로 두면 파일명이 깨진다. 열쇠는 URL 전체다
        # (이 URL 은 질의문자열 안에 '/' 가 있어 마지막 조각이 파일명이 된다).
        "rename": {
            "https://gastron.com/home/download.php?ps_db=manual&ps_boid=73&ps_file=1&fname_text=board_data/manual/GTC_200A_%B1%B9%B9%AE%B8%C5%B4%BA%BE%F3_R1.0.pdf":
                "Gastron_GTC-200A_Manual_KR_R1.0.pdf",
        },
        "insecure": True,
        "extractor": "auto",
        "access": "무로그인",
    },
    {
        "id": "trane-points-list",
        "vendor": "Trane",
        "kind": "포인트리스트",
        "note": "컨트롤러·기종별 BACnet/Modbus 통합 포인트 리스트. 문서번호가 BAS-PTS### 연속이라 열거 가능. "
                "실측: 13개 시험 중 9개 적중(날짜 5종 대입).",
        "enumerate": "series",
        "url": "https://elibrary.tranetechnologies.com/public/commercial-hvac/"
               "Literature/Points%20List/BAS-PTS{num:03d}{rev}-EN_{date}.pdf",
        "num": range(1, 61),
        "rev": ["A", "B"],
        "date": ["11082024", "11152024", "12042024", "12062024", "08302024",
                 "12032022", "10152024", "09182024", "01152025", "03202025"],
        "extractor": "auto",
        "access": "무로그인",
    },
    {
        "id": "belimo-system-integration",
        "vendor": "Belimo",
        "kind": "인터페이스·레지스터",
        "note": "BACnet 인터페이스 설명서 + Modbus 레지스터 표. 밸브·댐퍼 액추에이터·VAV·"
                "에너지밸브·센서 등 Belimo 전 제품군. 목록은 File Archive 페이지에서 한 번 "
                "긁어 왔고(아래 page), 같은 제품의 옛 판은 걸러 최신판만 남겼다. "
                "Akamai 봇 차단이 있어 Referer·Sec-Fetch 헤더가 필요하다 (headers 참고).",
        "enumerate": "list",
        "page": "https://www.belimo.com/ch/en_GB/support-eu/support-services/file-history",
        "headers": {
            "Referer": "https://www.belimo.com/ch/en_GB/support-eu/support-services/file-history",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-GB,en;q=0.9",
            "Sec-Fetch-Dest": "document", "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin", "Upgrade-Insecure-Requests": "1",
        },
        "urls": [
            "https://www.belimo.com/mam/general-documents/system_integration/BACnet/"
            + n for n in [
                "belimo_BACnet_Interface-description_AirWater_V3_4_en-gb.pdf",
                "belimo_BACnet_Interface-description_Damper_actuator_V3_4_en-gb.pdf",
                "belimo_BACnet_Interface-description_VAV_V3_4_en-gb.pdf",
                "belimo_BACnet_Interface-description_VRU_V1_4_en-gb.pdf",
                "belimo_BACnet_Interface-description_Energy-Valve_V4_1_en-gb.pdf",
                "belimo_BACnet_Interface-description_2way-EPIV_V4_0_en-gb.pdf",
                "belimo_BACnet_Interface-description_6way-EPIV_en-gb.pdf",
                "belimo_BACnet_Interface-description_PR_V3_4_en-gb.pdf",
                "belimo_BACnet_Interface-description_CQ24A-BAC_en-gb.pdf",
                "belimo_BACnet_Interface-description_IoT_product_range_en-gb.pdf",
                "belimo_BACnet_Interface-description_22PF_V4_0_en-gb.pdf",
                "belimo_BACnet_Interface-description_Sensors_V4_1_en-gb.pdf",
                "belimo_BACnet_Interface-description_TEM_V4_1_en-gb.pdf",
            ]] + [
            "https://www.belimo.com/mam/general-documents/system_integration/Modbus/"
            + n for n in [
                "belimo_Modbus-Register_AirWater_V3_4_en-gb.pdf",
                "belimo_Modbus-Register_Damper_actuator_V3_4_en-gb.pdf",
                "belimo_Modbus-Register_VAV_V3_4_en-gb.pdf",
                "belimo_Modbus-Register_VRU_V1_4_en-gb.pdf",
                "belimo_Modbus-Register_Energy-Valve_V4_1_en-gb.pdf",
                "belimo_Modbus-Register_2way-EPIV_V4_0_en-gb.pdf",
                "belimo_Modbus-Register_6way-EPIV_en-gb.pdf",
                "belimo_Modbus-Register_PR_V3_4_en-gb.pdf",
                "belimo_Modbus-Register_CQ24A-BAC_en-gb.pdf",
                "belimo_Modbus-Register_IoT_Product_Range_en-gb.pdf",
                "belimo_Modbus-Register_22PF_V4_0_en-gb.pdf",
                "belimo_Modbus-Register_Sensors_V4_2_en-gb.pdf",
                "belimo_Modbus-Register_TEM_V4_1_en-gb.pdf",
            ]],
        "extractor": "auto",
        "access": "헤더 필요",
        # Modbus 문서는 '개요표(주소→짧은 이름)'와 '상세표(주소→설명)'가 따로 있어
        # 표 인식은 상세표를, 줄 읽기는 개요표를 읽는다. 둘 다 원문 그대로지만
        # 서로 다른 열이라 교차 대조로는 검증할 수 없다 — 사람 표본이 필요하다.
        "crosscheck_unreliable": r"Modbus-Register",
    },
    {
        "id": "btl-pics",
        "vendor": "(전 벤더)",
        "kind": "PICS",
        "note": "BACnet Testing Laboratories 제품 목록 — 235개사 1,633제품. "
                "카탈로그 직링크가 그대로 열린다. 포인트 목록이 아니라 **통신 능력 선언**이다.",
        "enumerate": "page",
        "page": "https://www.bacnetinternational.net/btl/",
        "link_pattern": r"/catalog/manu/[^\"']+\.(pdf|PDF)",
        "extractor": "pics",
        "access": "무로그인",
    },
    {
        "id": "danfoss-drives",
        "vendor": "Danfoss",
        "kind": "매뉴얼·프로그래밍 가이드",
        "note": "드라이브 문서가 files.danfoss.com 직링크로 공개. 문서번호 MG#####.",
        "enumerate": "list",
        "urls": [
            "https://files.danfoss.com/download/Drives/MG17N102.pdf",
            "https://files.danfoss.com/download/Drives/MG10S202.pdf",
            "https://files.danfoss.com/download/Drives/MG92L103.pdf",
            "https://files.danfoss.com/download/Drives/DKDDPFP100A402_HVAC_Basic.pdf",
            "https://assets.danfoss.com/documents/latest/514925/AJ275648114271en-001201.pdf",
            # 소프트스타터 MCD 500 — 형번별 정격전류·기동 특성
            "https://files.danfoss.com/download/Drives/DKDDPFP550A228_MCD500_Lores.pdf",
            "https://files.danfoss.com/download/Drives/MG17K802.pdf",
        ],
        "extractor": "layout",
        "access": "무로그인",
        # MG17N102 는 레지스터 한 칸 안에 비트 구간별 하위 행이 들어 있어
        # (40001 Command / 비트 0–7 / 비트 8–14 Reserved …) 줄 읽기가 번호와 이름을
        # 어긋나게 짝짓는다. 표 인식 결과가 맞고 줄 경로가 틀리므로 대조 대상에서 뺀다.
        "crosscheck_unreliable": r"MG17N102",
    },
    {
        "id": "grundfos-literature",
        "vendor": "Grundfos",
        "kind": "Functional profile",
        "note": "CIM/CIU 통신모듈별 BACnet·Modbus 프로파일. api.grundfos.com/literature 직링크.",
        "enumerate": "list",
        "urls": [
            "https://api.grundfos.com/literature/Grundfosliterature-6012933.pdf",
            "https://api.grundfos.com/literature/Grundfosliterature-6012947.pdf",
        ],
        "extractor": "auto",
        "access": "무로그인",
    },
    {
        "id": "daikin-bacnet",
        "vendor": "Daikin",
        "kind": "게이트웨이 Design Guide",
        "note": "VRV BACnet 인터페이스. 오브젝트 ID가 계산식으로 정의된다.",
        "enumerate": "list",
        "urls": [
            "https://daikincomfort.com/docs/default-source/interface-for-use-bacnet-/"
            "eg-dms502b71bacnet-guide.pdf",
            "https://www.daikinac.com/docs/default-source/itm-bacnet-server-gateway-option/"
            "eg-itm_bacnetgatewayguide_v2-0.pdf",
        ],
        "extractor": "layout",
        "access": "무로그인",
    },
    {
        "id": "carrier-shareddocs",
        "vendor": "Carrier",
        "kind": "통합가이드",
        "note": "shareddocs.com/hvac/docs 공개 저장소. ⚠ HEAD 가 Content-Length 를 안 줘서 "
                "collect.py 가 1바이트 GET 으로 크기를 확인한다.",
        "enumerate": "list",
        "urls": [
            "https://www.shareddocs.com/hvac/docs/1000/Public/03/11-808-357-01.pdf",
            "https://www.shareddocs.com/hvac/docs/1000/Public/0E/11-808-535-01.pdf",
            "https://www.shareddocs.com/hvac/docs/1001/Public/00/40VM-52ASI-R1.pdf",
        ],
        "extractor": "auto",
        "access": "무로그인",
    },
    {
        "id": "carrier-48-50n",
        "vendor": "Carrier",
        "kind": "포인트리스트",
        "note": "WeatherExpert 48/50N 옥상형(75~150톤, ComfortLink 컨트롤러) — 컨트롤 매뉴얼 "
                "48/50N-7T 의 APPENDIX F 'BACNET COMMUNICATION OPTION · NETWORK POINTS LIST' 가 "
                "포인트 정본이고, Product Data 48/50N-6PD 가 정격 카탈로그다. "
                "Carrier 는 포인트 리스트를 별도 문서로 내지 않고 컨트롤 매뉴얼 부록에 싣는다.",
        "enumerate": "list",
        "urls": [
            "https://www.shareddocs.com/hvac/docs/1005/Public/02/48-50N-7T.pdf",
            "https://www.shareddocs.com/hvac/docs/1005/Public/05/48-50N-6PD.pdf",
        ],
        "rename": {
            "48-50N-7T.pdf": "Carrier_48-50N-7T_WeatherExpert_Controls.pdf",
            "48-50N-6PD.pdf": "Carrier_48-50N-6PD_WeatherExpert_ProductData.pdf",
        },
        "extractor": "auto",
        "access": "무로그인",
        # APPENDIX F 표가 설명·CCN 코드·BACnet 이름 3열이라 줄 읽기가 일부 행에서
        # 옆 열(CCN 코드 'a404 1 _')을 짚는다 — 표 인식 결과(사람용 설명)가 정본.
        "crosscheck_unreliable": r"48-50N-7T",
    },
    # ── 사양 문서 (kind="카탈로그·데이터시트") ─────────────────────────────
    # 통합 포인트 리스트에는 정격이 실리지 않는다. 시뮬레이터가 쓸 전압·전류·
    # 소비전력·용량은 카탈로그와 데이터시트에만 있어 따로 모은다.
    {
        "id": "trane-product-catalog",
        "vendor": "Trane",
        "kind": "카탈로그·데이터시트",
        "note": "냉동기 제품 카탈로그. 형번별 냉동능력(ton·kW)·소비전력·kW/ton·IPLV·"
                "전기 정격이 실린다 — 냉동기 26모델의 정격 공백을 메운다. "
                "포인트 리스트와 같은 elibrary 저장소이고 문서번호는 <계열>-PRC###<개정>-EN.",
        "enumerate": "list",
        "urls": [
            # 원심(CenTraVac) · 마그네틱 원심(Agility)
            "https://elibrary.tranetechnologies.com/public/commercial-hvac/Literature/"
            "Product%20Catalog/CTV-PRC021G-EN_12202024.pdf",
            "https://www.tranehk.com/files/Products/CTV-PRC021B-EN_06302022.pdf",
            # 공랭 스크류(RTAC) · 수랭 스크류(RTHD·RTAG)
            "https://www.trane.com/content/dam/Trane/Commercial/lar/Peru/Manuales/"
            "Chiller_RTAC/RLC-PRC006M-EN_Catalog.pdf",
            "https://www.tranehk.com/files/Products/RLC-PRC039C-EN.pdf",
            "https://www.trane.com/content/dam/Trane/Commercial/global/products-systems/"
            "equipment/chillers/water-cooled/helical-rotary/optimus-rthd/"
            "RLC-PRC020J-EN_03112020.pdf",
            "https://www.tranehk.com/files/Products/RTHD_Catalog__AUG2018.pdf",
            "https://www.trane.com/content/dam/Trane/Commercial/lar/es/product-systems/"
            "catalog/RTAG-PRC001E-EN.pdf",
            # 공랭 스크류(Sintesis RTAF)
            "https://www.trane.com/content/dam/Trane/Commercial/lar/literatura/products/"
            "chillers/air-cooled-chillers/sintesis-air-cooled-chiller/english/brochure/"
            "PROD-SLB038-EN_06162020.pdf",
            "https://www.trane.com/content/dam/Trane/Commercial/global/products-systems/"
            "equipment/chillers/air-cooled/ascend/AC-PRC001G-EN_01302022.pdf",
            "https://www.trane.com/content/dam/Trane/Commercial/global/products-systems/"
            "equipment/chillers/water-cooled/helical-rotary/RLC-PRC040F-EN_08302021.pdf",
            # Agility(HDWA) 는 elibrary 에 없고 trane.com 에만 있다 (실측: elibrary 404)
            "https://www.trane.com/content/dam/Trane/Commercial/global/products-systems/"
            "equipment/chillers/water-cooled/Agility/HDWA-PRC004A-EN_05132021.pdf",
        ] + [
            # 나머지 계열 — elibrary 직링크. 문서번호는 <계열>-PRC###<개정>-EN_<날짜>
            ELIB_CATALOG + n for n in [
                "RLC-PRC029P-EN_10312025.pdf",    # Series R RTWD 수랭 스크류
                "RLC-PRC020M-EN_06012025.pdf",    # Series R 수랭 (RTHD 최신판)
                "CG-PRC017AA-EN_04302026.pdf",    # CGAM 공랭 스크롤
                "AC-PRC002K-EN_05162025.pdf",     # Ascend ACS/ACX 공랭
                "AC-PRC002G-EN_06022023.pdf",     # Ascend ACS/ACX (구판)
                "AC-PRC005C-EN_12132024.pdf",     # Ascend ACR
                "RLC-PRC049K-EN_04022022.pdf",    # Sintesis RTAF 공랭 스크류
            ]],
        "extractor": "spec",
        "access": "무로그인",
    },
    {
        "id": "trane-airside-catalog",
        "vendor": "Trane",
        "kind": "카탈로그·데이터시트",
        "note": "공기측 제품 카탈로그 — 지붕형 패키지(Precedent·IntelliPak)·스플릿(Odyssey·"
                "IntelliCore RAUK). 형번별 냉방능력·풍량·압축기/팬 전동기 정격이 실린다. "
                "문서번호 계열이 냉동기와 달라 따로 둔다 (RT-PRC·PKGP-PRC·SS-PRC·ACDS-PRC).",
        "enumerate": "list",
        "urls": [
            ELIB_CATALOG + n for n in [
                "RT-PRC023AY-EN_12202022.pdf",    # Precedent 3~10톤
                "PKGP-PRC019D-EN_09302023.pdf",   # Precedent 히트펌프
                "RT-PRC103C-EN_01312025.pdf",     # IntelliPak
                "RT-PRC112B-EN_11152025.pdf",     # IntelliPak 차세대
                "SS-PRC050C-EN_03142026.pdf",     # Odyssey 히트펌프 6~25톤
                "SS-PRC058B-EN_05082025.pdf",     # IntelliCore 스플릿 (RAUK)
                "ACDS-PRC005B-EN_05082025.pdf",   # IntelliCore 공랭 응축기
            ]] + [
            "https://www.trane.com/content/dam/Trane/Commercial/global/products-systems/"
            "equipment/unitary/rooftop-systems/precedent-12-5-to-25-tons/"
            "PKGP-PRC021C-EN_07152023.pdf",
            "https://www.trane.com/content/dam/Trane/Commercial/global/products-systems/"
            "equipment/unitary/rooftop-systems/intellipak-with-symbio-800/"
            "RT-PRC086F-EN_05282020.pdf",
            "https://www.trane.com/content/dam/Trane/Commercial/global/products-systems/"
            "equipment/unitary/split-systems/odyssey-6-to-25-tons/"
            "SS-PRC028AA-EN_06262022.pdf",
            "https://www.trane.com/content/dam/Trane/Commercial/global/products-systems/"
            "equipment/unitary/split-systems/rauj-cauj-20-to-120-tons/"
            "SS-PRC030L-EN_07092021.pdf",
        ],
        "extractor": "spec",
        "access": "무로그인",
    },
    {
        "id": "ebmpapst-catalog",
        "vendor": "ebm-papst",
        "kind": "카탈로그·데이터시트",
        "note": "EC 원심팬 제품 카탈로그. 형번별 정격전압·입력전류·소비전력·회전수·"
                "풍량·정압이 표로 실린다 — 송풍기 시뮬레이션의 근거값이다.",
        "enumerate": "list",
        "urls": [
            "https://www.ebmpapst.com/content/dam/ebm-papst/media/catalogs/products/"
            "Product_Catalog_EC_centrifugal_fans_RadiPac_2_RadiFit_Edition_2023_10_.pdf",
            "https://www.ebmpapst.com/content/dam/ebm-papst/media/catalogs/products/"
            "Catalog_Centrifugalfans_EC-RadiCal_EN.pdf",
            "https://www.ebmpapst.com/content/dam/ebm-papst/loc/apac/singapur/brochures/"
            "RadiPac-630-1000-EC-centrifugal-fan-ebmpapst.pdf",
        ],
        "extractor": "spec",
        "access": "무로그인",
    },
    {
        "id": "belimo-datasheets",
        "vendor": "Belimo",
        "kind": "카탈로그·데이터시트",
        "note": "액추에이터 형번별 기술 데이터시트. 전원·운전/유지 소비전력·토크·"
                "구동시간이 실린다. URL 패턴이 규칙적이라 형번만 넣으면 열거된다. "
                "봇 차단이 있어 belimo-system-integration 과 같은 headers 가 필요하다.",
        "enumerate": "list",
        "headers": {
            "Referer": "https://www.belimo.com/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Sec-Fetch-Dest": "document", "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin", "Upgrade-Insecure-Requests": "1",
        },
        "urls": [
            "https://www.belimo.com/mam/general-documents/datasheets/en-us/"
            "belimo_%s_datasheet_en-us.pdf" % n
            for n in [
                # 댐퍼 구동기 (비스프링)
                "LMB24-3", "LMB24-SR", "LMB24-3-T", "NMQB24-MFT", "GMB24-3",
                "AMB24-3", "NMB24-3", "GMX24-MFT", "AMX24-MFT", "NMX24-MFT",
                "LMX24-MFT",
                # 스프링리턴 (방화·비상 복귀)
                "TFB24-S", "FSAF24A", "LF24-S_US", "AFB24-SR", "NFB24-SR",
                "AFX24-MFT", "NFX24-MFT",
                # 밸브 구동기
                "LRB24-3", "ARB24-3", "AFRB24-SR", "LVKB24-3",
                # VAV 컴팩트 — 통신형 유량제어
                "LMV-D3-MOD", "NMV-D3-MOD",
            ]
        ],
        "extractor": "spec",
        "access": "헤더 필요",
    },
    {
        "id": "belimo-datasheets-family",
        "vendor": "Belimo",
        "kind": "카탈로그·데이터시트",
        "note": "계열 데이터시트 — 형번 자리에 '..' 를 쓰는 제품군 단위 문서. "
                "규칙을 실측으로 알아냈다: 주문코드의 '+' 가 URL 에서는 '_' 가 되고, "
                "계열 문서는 en-gb, 구체 형번은 en-us 에 있다 (belimo_EV..R2_BAC_...). "
                "에너지밸브·EPIV·열량계처럼 형번 조합이 많은 제품은 이쪽에만 있다. 버터플라이는 구동기(PR)가 아니라 **밸브 형번**(D6..)으로 문서가 난다.",
        "enumerate": "list",
        "headers": {
            "Referer": "https://www.belimo.com/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-GB,en;q=0.9",
            "Sec-Fetch-Dest": "document", "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin", "Upgrade-Insecure-Requests": "1",
        },
        "urls": [
            "https://www.belimo.com/mam/general-documents/datasheets/en-gb/"
            "belimo_%s_datasheet_en-gb.pdf" % n
            for n in ["EV..R2_BAC", "EV..R2_KBAC", "EV..F_BAC", "EV..R3_BAC",
                      "EP..R2_BAC"]
        ] + [
            "https://www.belimo.com/mam/general-documents/datasheets/en-us/"
            "belimo_%s_datasheet_en-us.pdf" % n
            for n in ["EV050_ARX-E_N4HT", "EP050_LRX-E",
                      "22DTM-56", "22DTH-56M", "22UTH-560X", "VRU-D3-BAC",
                      "22PE-5U..", "D6..N"]
        ] + [
            "https://www.belimo.com/mam/general-documents/datasheets/en-gb/"
            "belimo_%s_datasheet_en-gb.pdf" % n
            for n in [
                "22PEM-1U..",    # 열량계 (MID 인증)
                "22PE-1U..",     # 열량계 (비인증)
                "G-22PEM-A01",   # 열량계 조합품
                "22PF-1U..",     # 유량센서
                "CQ24A-BAC",     # 존 회전 구동기
                "D6..BL", "D6..N",   # 버터플라이 밸브 (PR 구동기 조합)
                # Air Water 계열 — 구동기 형번은 MOD 접미사로 개별 문서다
                "LR24A-MOD", "NR24A-MOD", "GK24A-MOD", "SR24A-MOD", "LM24A-MOD",
            ]
        ],
        "extractor": "spec",
        "access": "헤더 필요",
    },
    {
        "id": "ebmpapst-modbus",
        "vendor": "ebm-papst",
        "kind": "Modbus 파라미터 명세",
        "note": "EC 팬 전 시리즈의 Modbus 홀딩 레지스터 명세. 송풍기 계열(e13)을 채운다. "
                "회전수는 D010(상대값 0~64000)×D119(최대 rpm)로 계산한다.",
        "enumerate": "list",
        "urls": [
            "https://www.ebmpapst.com/content/dam/ebm-papst/loc/europe/gb/"
            "modbus-parameter-specifications/MODBUS%20Lite%20Basic%20Functionality%20V5_01.pdf",
            "https://www.ebmpapst.com/content/dam/ebm-papst/loc/europe/gb/"
            "modbus-parameter-specifications/MODBUS_ACE_RadiCal%20in%20Scroll%20V1_0.pdf",
            "https://ebmpapst.se/sv/dat/site_common/upload/"
            "MODBUS_parameter_specifications_V5.00.pdf",
            "https://stepimassets.blob.core.windows.net/dsassetsprod/MODBUS_6_4_EXCERPT_EN.PDF",
        ],
        "extractor": "auto",
        "access": "무로그인",
    },
    {
        "id": "vertiv-liebert",
        "vendor": "Vertiv",
        "kind": "프로토콜 레퍼런스",
        "note": "IntelliSlot 통신카드의 Modbus·BACnet 데이터포인트. 항온항습기(CRAC)·"
                "UPS가 붙는다 — 계열 e7(FCU·CRAC)·e19(전력)를 채운다. "
                "⚠ 1,748쪽 통합 레퍼런스라 제품 수십 개가 한 문서에 있고 제품끼리 "
                "인스턴스 번호가 겹친다. 통째로 뽑으면 뒤 제품이 앞 제품을 덮으므로 "
                "제품별 쪽 범위로 나눠 뽑는다 (extract_tables(pages=...)). "
                "쪽 범위는 제품별 표 제목 '<제품>—Binary Data'…'—Glossary' 로 정했다.",
        "enumerate": "list",
        "urls": [
            "https://www.vertiv.com/4a1e3e/globalassets/shared/"
            "vertiv-liebert-intellislot-modbus-and-bacnet-protocols-reference-guide-sl-28170.pdf",
            "https://www.ccontrols.com/support/dp/LiebertIntelliSlot.pdf",
            "https://www.vertiv.com/48eb8d/globalassets/products/"
            "monitoring-control-and-management/software/"
            "liebert-sitescan-web-centralized-monitoring-and-control/"
            "liebert-sitescan-web-modbus-and-bacnet-protocols-user-guide-sl-27431.pdf",
        ],
        "extractor": "auto",
        "access": "무로그인",
    },
    {
        "id": "wilo-if-module",
        "vendor": "Wilo",
        "kind": "IF-모듈 데이터포인트",
        "note": "펌프용 Modbus·BACnet IF-모듈의 데이터포인트 목록. 계열 e14(펌프)를 채운다.",
        "enumerate": "list",
        "urls": [
            "https://cms.media.wilo.com/cdndoc/wilo110050/794169/wilo110050.pdf",
            "https://cms.media.wilo.com/cdndoc/"
            "wilo_f_020000290002833f00010092/871915/"
            "wilo_f_020000290002833f00010092.pdf",
            "https://wilo.cdn.mediamid.com/cdndoc/wilo54872/350003/wilo54872.pdf",
        ],
        "extractor": "auto",
        "access": "무로그인",
    },
    {
        "id": "schneider-powerlogic",
        "vendor": "Schneider Electric",
        "kind": "전력계측기 매뉴얼",
        "note": "PowerLogic PM5000 계열 전력 계측기. 계열 e19(전력 설비)를 채운다. "
                "⚠ 레지스터 목록 정본은 xls/xlsx 라 별도 취입이 필요하고, 여기 URL 은 "
                "사용자 매뉴얼(레지스터 표 일부 포함)이다.",
        "enumerate": "list",
        "urls": [
            "https://productinfo.se.com/pm5300/5be97f3b347bdf0001d99c87/"
            "PM5300%20User%20Manual/English/EAV15107-EN11.pdf",
            "https://docs.rs-online.com/fd45/0900766b815685bf.pdf",
        ],
        "extractor": "auto",
        "access": "무로그인",
    },
    {
        "id": "jci-york-datamap",
        "vendor": "Johnson Controls / York",
        "kind": "데이터맵 (HTML)",
        "note": "York 냉동기 BACnet·Modbus 데이터맵이 HTML이라 스크레이핑이 쉽다. "
                "VRF Smart Gateway 포인트 표도 같은 사이트.",
        "enumerate": "list",
        "urls": [
            "https://docs.johnsoncontrols.com/chillers/v/u/YORK/en-US/"
            "YVAA-YVFA-YAGK-Native-BACnet-and-Modbus-N2-Data-Map/322",
            "https://docs.johnsoncontrols.com/bas/r/Metasys/en-US/"
            "VRF-Smart-Gateway-Installation-Instructions/E/BACnet-Points",
        ],
        "extractor": "html",
        "access": "무로그인",
    },
    {
        "id": "daikin-applied-protocol",
        "vendor": "Daikin",
        "kind": "포인트리스트",
        "note": "Daikin Applied MicroTech III/4 유닛 컨트롤러 프로토콜 정보(ED 시리즈) — "
                "BACnet·LonWorks·Modbus 데이터포인트 정본. ED 15112 는 옥상형·자냉식"
                "(Rebel DPS/DPH·RoofPak RPE/RPS·Maverick II MPS·Self-Contained SWT/SWP), "
                "ED 15120·19131·19111 은 냉동기(AGZ·AMZ·ADS·AWV Pathfinder·WME Magnitude·"
                "WWV Navigator·AGZ-F·WMT·WMC-E). tahoeweb API 직링크가 무로그인으로 열린다. "
                "⚠ HEAD 는 405 — collect.py 가 1바이트 GET 으로 폴백한다.",
        "enumerate": "list",
        "urls": [
            "https://tahoeweb.daikinapplied.com/api/general/DownloadDocumentByName/media/"
            "ED%2015112-21%20MicroTech%20AHU%20Unit%20Controller%20Protocol%20Document.pdf/",
            "https://tahoeweb.daikinapplied.com/api/general/DownloadDocumentByName/media/"
            "ED%2015120-12.pdf/",
            "https://tahoeweb.daikinapplied.com/api/general/DownloadDocumentByName/media/"
            "ED%2019131-1.pdf/",
            "https://tahoeweb.daikinapplied.com/api/general/DownloadDocumentByName/media/"
            "ED19111-3.pdf/",
        ],
        "rename": {
            "ED 15112-21 MicroTech AHU Unit Controller Protocol Document.pdf":
                "Daikin_ED-15112-21_MicroTech_Rooftop-AHU_Protocol.pdf",
            "ED 15120-12.pdf": "Daikin_ED-15120-12_MicroTech_Chiller_Protocol.pdf",
            "ED 19131-1.pdf": "Daikin_ED-19131-1_MicroTech_AGZ-F-WMT_Protocol.pdf",
            "ED19111-3.pdf": "Daikin_ED-19111-3_MicroTech_WME-CD_Protocol.pdf",
        },
        "extractor": "auto",
        "access": "무로그인 (HEAD 405)",
        # 15112·15120 은 설명 셀이 여러 줄로 감겨 줄 읽기 경로가 (ID, 이름) 짝을
        # 복원하지 못한다 — 표 인식 결과가 정본이고 대조는 불가.
        # (19131·19111 은 짧은 셀이라 대조가 되고 실제 98% 이상 일치)
        "crosscheck_unreliable": r"ED-15112|ED-15120",
    },
    {
        "id": "daikin-applied-catalog",
        "vendor": "Daikin",
        "kind": "카탈로그·데이터시트",
        "note": "Daikin Applied 제품 카탈로그 — 신규 등록한 통신 맵 모델의 정격 공백을 메운다. "
                "CAT 624(Trailblazer AGZ-E 30~241톤)·CAT 635(AGZ-F R-32 30~230톤)·"
                "CAT 261(Rebel DPS 옥상형 3~31톤)·ED 19116(Rebel 물리 데이터 시트)·"
                "CAT 262(Maverick II MPS)·CAT 861(Self-Contained SWP)·"
                "CAT 218-4(RoofPak Air Handler). "
                "tahoeweb 직링크 — HEAD 405 는 collect.py 가 GET 으로 폴백.",
        "enumerate": "list",
        "urls": [
            "https://tahoeweb.daikinapplied.com/api/general/DownloadDocumentByName/media/"
            "CAT624.pdf/",
            "https://tahoeweb.daikinapplied.com/api/general/DownloadDocumentByName/media/"
            "CAT635-4.pdf/",
            "https://tahoeweb.daikinapplied.com/api/general/DownloadDocumentByName/media/"
            "Rebel%20-%20CAT%20261.pdf/",
            "https://tahoeweb.daikinapplied.com/api/general/DownloadDocumentByName/media/"
            "Rebel%20Physical%20Data%20Sheet.pdf/",
            "https://tahoeweb.daikinapplied.com/api/general/DownloadDocumentByName/media/"
            "Maverick%20II%20-%20CAT%20262.pdf/",
            "https://tahoeweb.daikinapplied.com/api/general/DownloadDocumentByName/media/"
            "Self-Contained%20SWP%20-%20CAT%20861%20(pub%203-3-25).pdf/",
            "https://tahoeweb.daikinapplied.com/api/general/DownloadDocumentByName/media/"
            "RoofPak%20Air%20Handler%20-%20CAT%20218-4%20(published%201-23-22).pdf/",
            # WME 는 신형 카탈로그(CAT 639·641)가 표 없는 브로슈어라 쓸모가 없었다 —
            # 표가 있는 구판 카탈로그(CAT 632)와 엔지니어링 데이터(ED 19135)를 쓴다.
            "https://tahoeweb.daikinapplied.com/api/general/DownloadDocumentByName/media/"
            "CAT632.pdf/",
            "https://tahoeweb.daikinapplied.com/api/general/DownloadDocumentByName/media/"
            "ED19135.pdf/",
        ],
        "rename": {
            "CAT624.pdf": "Daikin_CAT624-23_Trailblazer_AGZ-E_Catalog.pdf",
            "CAT635-4.pdf": "Daikin_CAT635-4_Trailblazer_AGZ-F_Catalog.pdf",
            "Rebel - CAT 261.pdf": "Daikin_CAT261_Rebel_DPS_Catalog.pdf",
            "Rebel Physical Data Sheet.pdf": "Daikin_ED-19116_Rebel_Physical_Data.pdf",
            "Maverick II - CAT 262.pdf": "Daikin_CAT262_Maverick-II_MPS_Catalog.pdf",
            "Self-Contained SWP - CAT 861 (pub 3-3-25).pdf":
                "Daikin_CAT861_Self-Contained_SWP_Catalog.pdf",
            "RoofPak Air Handler - CAT 218-4 (published 1-23-22).pdf":
                "Daikin_CAT218-4_RoofPak_AirHandler_Catalog.pdf",
            "CAT632.pdf": "Daikin_CAT632-5_Magnitude_WME-C_Catalog.pdf",
            "ED19135.pdf": "Daikin_ED-19135_Magnitude_WME-D_EngData.pdf",
        },
        "extractor": "spec",
        "access": "무로그인 (HEAD 405)",
    },
    # York 기술 가이드 — khub URL 은 끝이 전부 'content' 라 파일명이 겹친다.
    # rename 이 원 이름 기준이라 문서 하나당 소스 하나로 가른다.
    {
        "id": "jci-york-techguide-small",
        "vendor": "Johnson Controls / York",
        "kind": "카탈로그·데이터시트",
        "note": "York ZF/ZJ/ZR 3~12.5톤 옥상형 기술 가이드(6046560-YTG-B-0921) — "
                "Simplicity SE 가 올라가는 유닛의 형번별 냉방능력·EER·풍량·코일·전기 데이터. "
                "khub content API 가 원본 PDF 를 준다 (JS 페이지 아님).",
        "enumerate": "list",
        "urls": [
            "https://docs.johnsoncontrols.com/ductedsystems/api/khub/documents/"
            "8FNScx_sQaKMcRktYOaTHQ/content",
        ],
        "rename": {
            "content": "York_ZF-ZJ-ZR_3-12.5t_TechGuide_6046560-YTG-B-0921.pdf",
        },
        "extractor": "spec",
        "access": "무로그인",
    },
    {
        "id": "jci-york-techguide-large",
        "vendor": "Johnson Controls / York",
        "kind": "카탈로그·데이터시트",
        "note": "York ZJ/ZR/ZF 15~25톤(180-300 MBh) 옥상형 기술 가이드(5168277-YTG-K-0119).",
        "enumerate": "list",
        "urls": [
            "https://docs.johnsoncontrols.com/ductedsystems/api/khub/documents/"
            "acP22u5ozd07h~ghOynw6g/content",
        ],
        "rename": {
            "content": "York_ZJ-ZR-ZF_15-25t_TechGuide_5168277-YTG-K-0119.pdf",
        },
        "extractor": "spec",
        "access": "무로그인",
    },
    {
        "id": "ivprodukt-envistar-catalog",
        "vendor": "Siemens",
        "kind": "카탈로그·데이터시트",
        "note": "IV Produkt Envistar 공조기 카탈로그(2024) — Climatix 모델의 유닛 쪽 정격. "
                "크기별 풍량(m³/s)·냉방능력(kW)·SFPv·퓨즈·중량 표가 실린다. "
                "공식 브로슈어의 배포 미러(enawent) — ivprodukt.com 은 파일 번호가 불투명해 "
                "문서 정체가 파일명에 남는 미러 URL 을 쓴다.",
        "enumerate": "list",
        "urls": [
            "https://www.enawent.pl/files/14/2024_3_Envistar_en.pdf",
        ],
        "rename": {
            "2024_3_Envistar_en.pdf": "IVProdukt_Envistar_Catalog_2024-3_en.pdf",
        },
        "extractor": "spec",
        "access": "무로그인",
    },
    {
        "id": "jci-simplicity-se",
        "vendor": "Johnson Controls / YORK",
        "kind": "포인트리스트",
        "note": "York 옥상형(RTU) Smart Equipment(Simplicity SE) 포인트 매핑 기술 부록 — "
                "BACnet OID 와 Modbus 레지스터가 한 표에 병기된다(펌웨어 v1072, 문서 "
                "5177447-UTS-A-1215). docs.johnsoncontrols.com 본문은 JS 렌더링이라 못 긁지만 "
                "khub content API 는 원본 PDF 를 그대로 준다.",
        "enumerate": "list",
        "urls": [
            "https://docs.johnsoncontrols.com/ductedsystems/api/khub/documents/"
            "gdWRBs86kDYxV_EHhOCGbw/content",
        ],
        "rename": {
            "content": "JCI_Simplicity-SE_Point-Mapping_5177447-uts-a-1215.pdf",
        },
        "extractor": "auto",
        "access": "무로그인",
        # 표의 ID 열(BACOid)에 타입이 없어 Modbus 주소를 포인트 번호로 쓴다 —
        # 줄 읽기 경로는 BACOid 를 집어 짝이 어긋나므로 대조 불가.
        "crosscheck_unreliable": r"JCI_Simplicity-SE",
    },
    {
        "id": "siemens-climatix-ahu",
        "vendor": "Siemens",
        "kind": "포인트리스트",
        "note": "Climatix POL908 표준 AHU 애플리케이션의 BACnet/IP 오브젝트 주소 목록. "
                "지멘스 원본 오브젝트 문서(CB1Y3963en)는 OEM 채널 배포라, Climatix 를 쓰는 "
                "AHU 제조사 IV Produkt 가 공개한 적용판을 쓴다 — 컨트롤러는 Siemens Climatix "
                "POL908, 유닛은 IV Produkt AHU. 오브젝트 구조는 표준 AHU 애플리케이션 v3.x 기준.",
        "enumerate": "list",
        "urls": [
            "https://www.ivprodukt.com/file/2572",
        ],
        "rename": {
            "2572": "IVProdukt_Siemens-Climatix-POL908_AHU_BACnet_Objects_V1.pdf",
        },
        "extractor": "auto",
        "access": "무로그인",
        # 이름이 1열, 인스턴스가 2열이라 줄 읽기 경로가 ID 를 먼저 못 찾는다 —
        # 표 인식 결과가 정본이고 대조는 불가.
        "crosscheck_unreliable": r"IVProdukt",
    },
    {
        "id": "swegon-gold",
        "vendor": "Swegon",
        "kind": "포인트리스트",
        "note": "GOLD RX/PX/CX/SD(E/F세대) 공조기 — 유럽 AHU 중 통합 문서 공개가 가장 성실한 "
                "벤더다. Modbus RTU/TCP 레지스터 정본(0x/1x/3x/4x 참조 표기) + 치수 카탈로그"
                "(크기 004~120 풍량·모터·전기) + AHU 퀵가이드(크기별 요약표). 컨트롤러는 IQlogic. "
                "BACnet 목록 정본은 xls/zip 배포라 PDF 는 Modbus 를 정본으로 쓴다.",
        "enumerate": "list",
        "urls": [
            "https://www.swegon.com/globalassets/digizuite/9313-en-gold_e_modbus_other_en.pdf",
            "https://www.swegon.com/globalassets/digizuite/8415-en-goldrx_f_dimensioning_productcatalogue_en.pdf",
            "https://www.swegon.com/globalassets/digizuite/6770-en-ahu_quick-guide_en.pdf",
            "https://www.bacnetinternational.net/catalog/manu/swegon%20operations%20ab/GOLD_E_BACnet_PICS_PV1.11_140429.pdf",
            # 정비 매뉴얼 — 전기 데이터(크기별 전원·퓨즈)와 표지의 제품 실물 사진용
            "https://www.swegon.com/globalassets/digizuite/16498-en-goldskfrx_maintenance_en.pdf",
        ],
        "rename": {
            "9313-en-gold_e_modbus_other_en.pdf": "Swegon_GOLD-EF_Modbus_RTU-TCP.pdf",
            "8415-en-goldrx_f_dimensioning_productcatalogue_en.pdf": "Swegon_GOLD-RX_Dimensioning_Catalogue.pdf",
            "6770-en-ahu_quick-guide_en.pdf": "Swegon_AHU_QuickGuide.pdf",
            "GOLD_E_BACnet_PICS_PV1.11_140429.pdf": "Swegon_GOLD-E_BACnet_PICS.pdf",
            "16498-en-goldskfrx_maintenance_en.pdf": "Swegon_GOLD-RX_Maintenance.pdf",
        },
        "extractor": "auto",
        "access": "무로그인",
        # 레지스터가 '1x0501' 참조 표기 + 여러 줄 설명 셀이라 줄 읽기가 짝을 못 만든다 —
        # 표 인식 결과가 정본이고 대조는 불가.
        "crosscheck_unreliable": r"Swegon_GOLD-EF_Modbus",
    },
    {
        "id": "aaon-vccx2",
        "vendor": "AAON",
        "kind": "포인트리스트",
        "note": "RN/RQ 옥상형의 VCCX2 유닛 컨트롤러 — 기술 가이드 APPENDIX C 'BACnet Guide' 가 "
                "포인트 정본(AI p72·AV p80·BI p86). 정격은 RN 브로슈어(캐비닛 A~E, RN-006~140 "
                "공칭 CFM·IEER/EER)와 IOM(난방 용량·전기 표)에서. aaon.com hubfs 직링크 무로그인.",
        "enumerate": "list",
        "urls": [
            "https://www.aaon.com/hubfs/G039840-VCCX2-T.pdf",
            "https://www.aaon.com/hubfs/260619_RN_Brochure.pdf",
            "https://www.aaon.com/hubfs/RN%20Series%20IOM%2020251210.pdf",
        ],
        "rename": {
            "G039840-VCCX2-T.pdf": "AAON_VCCX2_Technical_Guide.pdf",
            "260619_RN_Brochure.pdf": "AAON_RN_Series_Brochure.pdf",
            "RN Series IOM 20251210.pdf": "AAON_RN_Series_IOM_R454B.pdf",
        },
        "extractor": "auto",
        "access": "무로그인",
        # 기술 가이드 본문(배선 절)과 부록이 같은 AI 번호를 다른 뜻으로 쓴다 —
        # 줄 읽기가 본문 쪽을 짚어 어긋난다(원문 확인: AI:2=Control Mode 가 정답).
        "crosscheck_unreliable": r"AAON_VCCX2",
    },
    {
        "id": "jci-vrf-gateway",
        "vendor": "Johnson Controls / York",
        "kind": "게이트웨이 설치설명서 · 제출자료",
        "note": "VRF Smart Gateway (SI-VRFCBN02-0Sx). 실내기(IDU)·실외기(ODU) BACnet "
                "포인트 표가 설치설명서 11~14쪽에 있다. "
                "⚠ 정본 사이트 docs.johnsoncontrols.com 은 본문을 JS 로 그리고 "
                "딥링크가 다른 문서로 전환돼 긁을 수 없다 — 같은 문서의 PDF 배포본을 쓴다. "
                "제출자료(submittal)는 전원·통신·환경 정격이 들어 있다.",
        "enumerate": "list",
        "urls": [
            "https://files.hvacnavigator.com/p/installation%20instructions%20rev%20b.pdf",
            "https://files.hvacnavigator.com/p/cbn02%20submittal%20sheet%20v2.pdf",
            "https://files.hvacnavigator.com/p/user%20guide.pdf",
        ],
        # 벤더가 'user guide.pdf' 처럼 제품명 없는 이름으로 올려 둬서 그대로 두면
        # 다른 벤더 문서와 부딪힌다. 문서 표지의 코드(LIT-·Part No.)로 바꿔 적는다.
        "rename": {
            "installation instructions rev b.pdf":
                "JCI_VRF-Smart-Gateway_Install_24-10143-1183-B.pdf",
            "cbn02 submittal sheet v2.pdf":
                "JCI_VRF-Smart-Gateway_Submittal_CBN02-v2.pdf",
            "user guide.pdf":
                "JCI_VRF-Smart-Gateway_UserGuide_LIT-12012385.pdf",
        },
        "extractor": "auto",
        "access": "무로그인",
    },
    {
        "id": "lennox-core-enlight",
        "vendor": "Lennox",
        "kind": "포인트리스트",
        "note": "Enlight/Model L 옥상형 표준 탑재 CORE Unit Controller — BACnet 셋업 가이드 "
                "508112-02(05/2026)의 Object Definitions(7절, AO/AV/BV/MSV 표)가 포인트 정본. "
                "MS/TP·BACnet IP 내장. 정격은 Enlight LGT(가스/전기 3~6톤) EHB 210977 — "
                "General Data(형번 LGT036H4E~072H4E·톤수·풍량·EER/IEER)와 전기 데이터. "
                "lennox.com dA 직링크 무로그인.",
        "enumerate": "list",
        "urls": [
            "https://www.lennox.com/dA/bfb1627cbc/508112-02a.pdf",
            "https://www.lennox.com/dA/c72228c74f/ehb_lgt_abox_2411.pdf",
            # 제품 실물 사진용 — EHB 는 그라데이션·코일 일러스트뿐이라 브로슈어에서 딴다
            "https://www.lennox.com/dA/ec2cbef5a8/37J51_Enlight+Brochure+454B.pdf",
            # 대용량 히트펌프 13~20톤 EHB — LHT156/180/240 형번·난방 성능(COP)
            "https://www.lennox.com/dA/3b7b5ae321/ehb_lht_cbox_2411.pdf",
        ],
        # dA 해시 경로라 파일명이 문서번호뿐이다 — 표지 문서번호·제품명으로 바꿔 적는다
        "rename": {
            "508112-02a.pdf": "Lennox_CORE_BACnet_SetupGuide_508112-02.pdf",
            "ehb_lgt_abox_2411.pdf": "Lennox_Enlight_LGT_EHB_210977.pdf",
            "37J51_Enlight+Brochure+454B.pdf": "Lennox_Enlight_Brochure_37J51.pdf",
            "ehb_lht_cbox_2411.pdf": "Lennox_Enlight_LHT_EHB_2411.pdf",
        },
        "extractor": "auto",
        "access": "무로그인",
    },
    {
        "id": "systemair-access-geniox",
        "vendor": "Systemair",
        "kind": "포인트리스트",
        "note": "Geniox/Geniox GO 공조기의 Access 컨트롤러 — 통신 매뉴얼 153831 A011 의 "
                "'Access variable list'(EXOL·Modbus·BACnet 신호 전체)가 포인트 정본. "
                "Modbus 타입 열(0x/1x/3x/4x)과 주소 열이 갈라져 있어 절대 참조로 편다. "
                "정격은 Geniox 카탈로그(서술형)+퀵가이드(크기 10~31 치수표) — 크기별 "
                "풍량은 SystemairCAD 선정 SW 라 공개 표가 없다(AAON 부류). "
                "⚠ shop.systemair.com 구링크는 'Sales Channel Not Found' 로 죽었다 — "
                "Azure CDN(stepimassets)과 storyblok 이 현행 배포처.",
        "enumerate": "list",
        "urls": [
            "https://stepimassets.blob.core.windows.net/dsassetsprod/ACCESS_MANUAL_COMMUNICATION_153831_A011.PDF",
            "https://a.storyblok.com/f/108972/x/bba9a53ffb/unit_geniox_catalogue_global_09_2022.pdf",
            "https://a.storyblok.com/f/108972/x/202a778fcc/geniox_geniox_go_quickguide.pdf",
        ],
        "rename": {
            "ACCESS_MANUAL_COMMUNICATION_153831_A011.PDF":
                "Systemair_Access_Communication_153831-A011.pdf",
            "unit_geniox_catalogue_global_09_2022.pdf":
                "Systemair_Geniox_Catalogue_2022.pdf",
            "geniox_geniox_go_quickguide.pdf": "Systemair_Geniox_QuickGuide.pdf",
        },
        "extractor": "auto",
        "access": "무로그인",
        # EXOL 경로명이 셀 줄바꿈으로 갈라져 줄 읽기가 짝을 못 만든다 —
        # 표 인식 결과(공백 제거 후)가 정본이고 대조는 불가.
        "crosscheck_unreliable": r"Systemair_Access",
    },
    {
        "id": "mitsubishi-pac-if013",
        "vendor": "Mitsubishi Electric",
        "kind": "포인트리스트",
        "note": "Mr.Slim 실외기 연동 AHU 인터페이스 PAC-IF013B-E/PAC-SIF013B-E — "
                "Modbus 매뉴얼의 코일/입력(30001~)/홀딩(40001~) 레지스터가 포인트 정본"
                "(Modicon 절대 표기 열을 ID 로 쓴다 — 상대 Address 열을 집으면 겹친다). "
                "AHU 설계 가이드라인 13쪽에 실외기 용량 사이즈(ZRP/P/SHW/ZM 35~250)별 "
                "AHU 표준 풍량 최소/최대(m³/h) 표가 있다 — 형번급 근거. "
                "library.mitsubishielectric.co.uk download_full 직링크(번호 경로라 rename 필수).",
        "enumerate": "list",
        "urls": [
            "https://library.mitsubishielectric.co.uk/pdf/download_full/3004",
            "https://library.mitsubishielectric.co.uk/pdf/download_full/3879",
        ],
        "rename": {
            "3004": "Mitsubishi_PAC-IF013_Modbus_Manual.pdf",
            "3879": "Mitsubishi_PAC-IF013_AHU_Design_Guideline.pdf",
        },
        "extractor": "auto",
        "access": "무로그인",
    },
    {
        "id": "lg-ahu-comm-kit",
        "vendor": "LG",
        "kind": "포인트리스트",
        "note": "MULTI V/싱글 실외기 연동 AHU 통신 킷 0CAA0-02M — PDB 10절의 "
                "'Modbus points of PAHCMR000/PAHCMS000' 맵이 포인트 정본"
                "(환기 RA 제어 킷과 급기 SA 제어 킷이 같은 번호를 재사용 — "
                "번호 재사용 자동 분리로 두 모델). 'Reserved' 행은 자리표시라 뺀다. "
                "국내 현장 조우 확률 최상위 벤더. lg.com dam 직링크 무로그인 — "
                "기본 UA 는 403 이라 브라우저 형태 헤더가 필요하다(Belimo 전례).",
        "enumerate": "list",
        "headers": {
            "Referer": "https://www.lg.com/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en,ko;q=0.9",
            "Sec-Fetch-Dest": "document", "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin", "Upgrade-Insecure-Requests": "1",
        },
        "urls": [
            "https://www.lg.com/content/dam/channel/wcms/br/business/download/airsolution/202407_Kit%20de%20Comunica__o_AHU_PDB_20240924_030002_.pdf",
        ],
        "rename": {
            "202407_Kit de Comunica__o_AHU_PDB_20240924_030002_.pdf":
                "LG_AHU_CommKit_0CAA0-02M_PDB.pdf",
        },
        "extractor": "auto",
        "access": "무로그인",
    },
    {
        "id": "jci-york-bas-points",
        "vendor": "Johnson Controls / YORK",
        "kind": "포인트리스트",
        "note": "York 냉동기·루프탑 BAS 포인트 리스트 56건. 한 제품이 계통별로 여러 판을 갖는다 "
                "— YK 하나가 SC-EQ·OptiView E-Link(EM/SSS·VSD)·Micropanel II 로 4건이다. "
                "계통마다 표 구조와 함정이 달라 파서를 vendor_jci_sceq·_elink·_native·_yzd "
                "넷으로 갈랐다. 취입은 ingest_jci.py.",
        "enumerate": "list",
        "urls": [_JCI_KHUB % (site, i) for i, site, _n in JCI_BAS_POINTS],
        "rename": {_JCI_KHUB % (site, i): n for i, site, n in JCI_BAS_POINTS},
        "extractor": "vendor",
        "access": "무로그인",
        # 계통 대부분이 Modbus·N2·LON 주소만 주거나(BACnet 타입 열이 없거나) 한 행에 네
        # 프로토콜을 함께 실어, 줄 읽기 경로가 (타입, 인스턴스) 짝을 만들 수 없다.
        "crosscheck_unreliable": r"JCI_",
    },
    {
        "id": "jci-york-iom-points",
        "vendor": "Johnson Controls / YORK",
        "kind": "포인트리스트",
        "note": "York 옥상형(YPAL Series 100·Millenium·TempMaster OmniElite)·자립형(Versecon) "
                "설치·운전 매뉴얼. 포인트 표가 본문 후반에 묻혀 있다 — 냉동기처럼 별도 "
                "포인트 리스트로 발행되지 않는다. 표는 BACnet NAME|USER INTERFACE NAME|"
                "READ/WRITE|OBJECT TYPE AND INSTANCE|(MODBUS REGISTER|ENG UNITS|N2 ADDRESS)|"
                "POINTS LIST DESCRIPTION. 파서는 vendor_jci_ipu.py.",
        "enumerate": "list",
        "urls": [_JCI_KHUB % (site, i) for i, site, _n in JCI_IOM_POINTS],
        "rename": {_JCI_KHUB % (site, i): n for i, site, n in JCI_IOM_POINTS},
        "extractor": "vendor",
        "access": "무로그인",
        # 200쪽 매뉴얼이라 줄 읽기 경로가 표를 못 따라간다 — 교차 대조 불가
        "crosscheck_unreliable": r"JCI_IOM_",
    },
    {
        "id": "jci-york-rth-tech-guide",
        "vendor": "Johnson Controls / YORK",
        "kind": "제품 카탈로그",
        "note": "Roomtop RTC/RTH 컴팩트 수평형 공기-공기 히트펌프 기술 가이드 2건(K판·L판). "
                "**이 저장소 JCI 문서 중 정격이 실린 유일한 것**이다 — 나머지는 전부 BAS "
                "포인트/IOM 이라 용량·소비전력이 없었다(짝 규칙의 짝). 같은 제품의 BAS "
                "포인트는 YKN2Open 게이트웨이 판에 있다. "
                "⚠ 포털 제목은 스페인어인데 본문은 영문이다. "
                "⚠ 임베드 폰트(Gen_*)의 ToUnicode 가 1 밀려 있어 도면·배선도 글자가 "
                "'MPT DPNQPOFOUFT'(=LOS COMPONENTES)로 나온다 — 정격 표는 깨끗한 "
                "폰트라 무사하지만 파서가 폰트로 갈라 되돌린다. 파서는 vendor_jci_rth.py.",
        "enumerate": "list",
        "urls": [_JCI_KHUB % (site, i) for i, site, _n in JCI_RTH_SPECS],
        "rename": {_JCI_KHUB % (site, i): n for i, site, n in JCI_RTH_SPECS},
        "extractor": "vendor",
        "access": "무로그인",
    },
    {
        "id": "jci-airhandling-points",
        "vendor": "Johnson Controls / YORK",
        "kind": "포인트리스트",
        "note": "YORK 공조기 포털의 유닛 제어반 Modbus 레지스터 표. 열은 PLC register "
                "Address|Parameter number|Name|Range|Details 로, BACnet 이름도 오브젝트 "
                "타입도 없다 — 기존 8계통과 열이 하나도 안 겹쳐 어댑터를 따로 뒀다"
                "(vendor_jci_air.py). YKH·YKL 은 157행이 글자까지 같다(같은 제어반).",
        "enumerate": "list",
        "urls": [_JCI_KHUB % (site, i) for i, site, _n in JCI_AIR_POINTS],
        "rename": {_JCI_KHUB % (site, i): n for i, site, n in JCI_AIR_POINTS},
        "extractor": "vendor",
        "access": "무로그인",
        # 40쪽 매뉴얼 본문에 묻힌 표라 줄 읽기 경로가 표를 못 따라간다
        "crosscheck_unreliable": r"JCI_AIR_",
    },
    {
        "id": "jci-airhandling-fln",
        "vendor": "Johnson Controls / YORK",
        "kind": "포인트리스트",
        "note": "AYK550 Air Modulator(인버터)의 APOGEE P1/FLN 포인트 "
                "데이터베이스. 열은 Point #|Type|Subpoint Name|Factory Default|"
                "Engr. Units|Slope|Intercept|On Text|Off Text. ⚠ 원문이 Type 코드 "
                "풀이도, On/Off Text 의 코드 대응도, slope 변환 방향도 주지 않는다 "
                "— 보존만 하고 해석은 gaps 로 남긴다. 파서는 vendor_jci_fln.py.",
        "enumerate": "list",
        "urls": [_JCI_KHUB % (site, i) for i, site, _n in JCI_FLN_POINTS],
        "rename": {_JCI_KHUB % (site, i): n for i, site, n in JCI_FLN_POINTS},
        "extractor": "vendor",
        "access": "무로그인",
        # 280쪽 매뉴얼 본문에 묻힌 표라 줄 읽기 경로가 표를 못 따라간다
        "crosscheck_unreliable": r"JCI_AIR_AYK550",
    },
    {
        "id": "jci-corroboration",
        "vendor": "Johnson Controls / YORK",
        "kind": "대조용",
        "note": "판으로 삼지 않고 **다른 문서의 값을 대조**하는 데만 쓰는 원문. "
                "450.50-N1 46쪽 Table 8 이 SI0371 과 같은 6점을 담고 있어 서로 "
                "맞춰 본다(근거는 ingest_jci.CORROBORATED). 취입 경로는 이 소스를 "
                "읽지 않는다 — 받아 두는 것은 시험이 재현되게 하기 위해서다.",
        "enumerate": "list",
        "urls": [_JCI_KHUB % (site, i) for i, site, _n in JCI_CORROBORATION],
        "rename": {_JCI_KHUB % (site, i): n for i, site, n in JCI_CORROBORATION},
        "extractor": "none",
        "access": "무로그인",
    },
    {
        "id": "jci-vec100-points",
        "vendor": "Johnson Controls",
        "kind": "포인트리스트",
        "note": "Verasys VEC100 컨트롤러가 SBH 화면에 내보이는 메뉴 항목. 열은 "
                "Object or parameter|Description|Adjustable|Defaults|"
                "Enum set or range 다섯이고 **주소 열이 없다**. 표가 메뉴별 소표 "
                "43~47개로 쪼개져 실리며 캡션의 메뉴 경로가 행 정체성의 절반이다 "
                "— 같은 이름이 메뉴 여럿에 되풀이된다. 파서는 vendor_jci_vec100.py.",
        "enumerate": "list",
        "urls": [_JCI_KHUB % (site, i) for i, site, _n in JCI_VEC100_POINTS],
        "rename": {_JCI_KHUB % (site, i): n for i, site, n in JCI_VEC100_POINTS},
        "extractor": "vendor",
        "access": "무로그인",
        # 주소가 없어 줄 읽기 경로가 짝을 만들 열쇠가 없다 — 계통 전용 대조를 쓴다
        "crosscheck_unreliable": r"JCI_VEC100_",
    },
    {
        "id": "lg-bacnet-gateway",
        "vendor": "LG",
        "kind": "포인트리스트",
        "note": "LG BACnet 게이트웨이(AC Smart BACnet)의 오브젝트 목록. 88쪽 설치 매뉴얼 "
                "34~49쪽에 기기군별 포인트 표 13개가 실려 있다 — 실내기·환기·AHU·"
                "실외기(ODU)·AWHP. 실측 165점(고유 이름 133종). "
                "Object Type(BO/BI/MO/MI/AO/AI/AV/BV)·Object Name·상태값(Text-0~5)까지 준다. "
                "⚠ **표가 전치돼 있다** — 행이 속성(Object Type·Object Name·Point No.)이고 "
                "열이 포인트다. 세로로 세면 15점짜리 표가 10행으로 읽힌다. "
                "✅ 인스턴스 번호는 표에는 없지만 **규칙이 문서 안에 있다**(50쪽): "
                "'(XXX : Unit address)' · 'Product Type(Indoor:0, Vent:1, AHU:2, "
                "ODU:3, AWHP:4, GENERAL:5)' · 'Device : Group of Product units(16EA)'. "
                "따라서 instance = 유형×0x10000 + Device×0x1000 + Product×0x100 + Point 이고 "
                "XXX = Device×16 + Product 다. 원문 예시 42행에 맞춰 **42/42 일치**했다. "
                "그래서 VEC100(진짜로 주소가 없는 목록)과 **같은 자리가 아니다** — 취입하면 "
                "주소 있는 165점이 된다. (앞서 '주소 없는 목록'이라 적었던 것은 틀렸다.) "
                "⚠ 같은 포털의 PQNFB17C0 게이트웨이 설치 매뉴얼"
                "(fileId=UACH2Z0fWvXvJBf6PlVQ, 17쪽)은 **열어 봤고 포인트 표가 없다** "
                "— 다시 두드리지 마라.",
        "enumerate": "list",
        "urls": [
            "https://gscs-b2c.lge.com/open/downloadFile?fileId=hMQE1OFTwB7RNB2fQRA8Q",
        ],
        # URL 끝이 'downloadFile' 이라 원 이름으로는 못 가른다 — URL 전체를 열쇠로 쓴다
        "rename": {
            "https://gscs-b2c.lge.com/open/downloadFile?fileId=hMQE1OFTwB7RNB2fQRA8Q":
                "LG_ACSmart_BACnet_MFL69023101.pdf",
        },
        "extractor": "auto",
        "access": "무로그인",
    },
    {
        "id": "samsung-dms25-bacnet",
        "vendor": "Samsung",
        "kind": "포인트리스트",
        "note": "삼성 **MIM-B17BN BACnet 게이트웨이 / DMS2.5** 매뉴얼. 현장 DVM 계통의 "
                "오브젝트 목록이 나올 유일한 경로다 — 이미 받아 둔 "
                "Samsung_SEC_SpecGuide_KR_2017-03.pdf 는 라인업·용량·COP 만 주는 "
                "**정격 카탈로그**라 오브젝트가 0건이다(BACnet 1회·Object 0회·Modbus 0회, "
                "2026-09-04 본문 실측). "
                "MIM-B17BN 과 MIM-B17BUN 은 같은 장치이고 전원 코드만 북미형으로 다르다. "
                "두 문서를 함께 받는다. ⚠ **포인트는 18MB 사용설명서가 아니라 1.3MB "
                "설치설명서에 있다** — 받기 전에 반대로 짐작했다가 열어 보고 뒤집혔다"
                "(규칙 0: 표를 뽑기 전에 표지·목차를 센다). 본문 실측 2026-09-04 — "
                "UserManual 192쪽은 Object **0회**·Point List 0회·SNVT 0회로 DMS2.5 "
                "웹화면 조작 설명서다(포인트가 없다, 다시 열지 마라). InstallGuide "
                "104쪽은 Object 111회·Point List 25회·SNVT 124회·Instance 21회이고 "
                "BACnet 포인트 표가 **E-62~73**, LonWorks SNVT 표가 E-88~100 이다. "
                "BACnet 표는 기기군별로 갈린다 — 실내기(E-62·63) · AHU(E-65·66) · "
                "Hydro/EHS(E-68·69) · ERV/ERV Plus(E-70) · DVM CHILLER(E-71·72) · "
                "제어감시(E-73). LG AC Smart 와 같은 짜임이다(판 = 기기군). "
                "머리글은 Instance Number | Object | Object Type | Object Name | Unit | "
                "Status value(Inactive · Active · Text-1~Text-5) 다. "
                "⚠ LG 와 달리 **인스턴스 번호가 표에 있다**. 대신 이름에 자리표시가 "
                "있다(AC_RoomTemp_xx_xxxxxx) — 그 xx 가 무엇인지는 E-61 의 device ID "
                "규칙을 함께 읽어야 한다. "
                "⚠ **이름을 표 인식에서 바로 꺼내면 안 된다** — 밑줄이 조각으로 떨어져 "
                "'ACRoomTempxxxxxxxx _ _' 로 나온다. 쪽 글자 흐름에서 이름을 다시 "
                "읽어야 한다(LG 에서 겪은 것과 같은 조판 아티팩트, "
                "point-schema artifactCleanupFirst). "
                "⚠ 공식 경로로만 받는다. manualslib·all-guides 같은 제3자 호스트는 쓰지 "
                "않는다 — 재현이 안 되고 개정판 추적이 끊긴다(aiibook 을 뺀 것과 같은 이유). "
                "여기 URL 은 삼성 자체 다운로드센터(org.downloadcenter.samsung.com)다. "
                "⚠ 영국(UNI_UK) 판이다. 한국 판이 따로 있으면 그쪽이 낫다 — 다만 "
                "BACnet 오브젝트 목록은 지역별로 갈리지 않는 것이 보통이라 우선 이것으로 "
                "시작하고, 국내 판을 찾으면 대체한다.",
        "enumerate": "list",
        "urls": [
            'https://org.downloadcenter.samsung.com/downloadfile/ContentsFile.aspx?CDSite=UNI_UK&OriginYN=N&ModelType=N&ModelName=MIM-B17BN&CttFileID=7996541&CDCttType=UM&VPath=UM%2F202103%2F20210310164931477%2FSOL_NASA_DMS2_5_BAC_LW_IB_EN_DB68-06098A-12_web.pdf',
            'https://org.downloadcenter.samsung.com/downloadfile/ContentsFile.aspx?CDSite=UNI_UK&OriginYN=N&ModelType=N&ModelName=MIM-B17BN&CttFileID=9111650&CDCttType=UM&VPath=UM%2F202303%2F20230330094513360%2FDB68-06095A-05_IBIM_NASA_DMS2.5_BACnet_LW_EU_EN_221128-D01.pdf',
        ],
        # URL 끝이 'ContentsFile.aspx' 라 원 이름으로는 못 가른다 — URL 전체를 열쇠로 쓴다
        "rename": {
            'https://org.downloadcenter.samsung.com/downloadfile/ContentsFile.aspx?CDSite=UNI_UK&OriginYN=N&ModelType=N&ModelName=MIM-B17BN&CttFileID=7996541&CDCttType=UM&VPath=UM%2F202103%2F20210310164931477%2FSOL_NASA_DMS2_5_BAC_LW_IB_EN_DB68-06098A-12_web.pdf':
                "Samsung_DMS25_BACnet_LonWorks_UserManual_EN_DB68-06098A-12.pdf",
            'https://org.downloadcenter.samsung.com/downloadfile/ContentsFile.aspx?CDSite=UNI_UK&OriginYN=N&ModelType=N&ModelName=MIM-B17BN&CttFileID=9111650&CDCttType=UM&VPath=UM%2F202303%2F20230330094513360%2FDB68-06095A-05_IBIM_NASA_DMS2.5_BACnet_LW_EU_EN_221128-D01.pdf':
                "Samsung_DMS25_BACnet_LonWorks_InstallGuide_EN_DB68-06095A-05.pdf",
        },
        "extractor": "auto",
        "access": "무로그인",
    },
    {
        "id": "ls-electric-h100",
        "vendor": "LS ELECTRIC",
        "kind": "인터페이스·레지스터",
        "note": "H100 은 LS ELECTRIC 의 **팬·펌프 전용 드라이브**다. 현장 조사에서 삼성 캠퍼스의 "
                "통신 장치 1위가 인버터(222대·1,722점)였고 그중 215대가 똑같은 7점"
                "(DCLINK_VOLTAGE·INV_OUT_VOLTAGE/CURRENT/PWR·INV_ACCUM_PWR·INV_RUN_TIME·"
                "INV_SPEED·INV_HEATsink TEMP)을 쓴다 — 용도가 정확히 겹친다. "
                "⚠ **현장 인버터의 제조사는 확인되지 않았다.** 포인트 이름이 어느 인버터나 "
                "쓰는 일반 어휘라 데이터로는 못 가린다(장치 이름·설명·나이아가라 내보내기 모두 "
                "제조사를 안 밝힌다). H100 을 먼저 넣는 이유는 **용도가 같고 국내 최다이며 "
                "카탈로그의 VFD 가 4모델뿐**이라 어느 쪽이든 필요하기 때문이다. "
                "브랜드가 확인되면 그때 해당 벤더를 더한다. "
                "두 문서를 함께 받는다 — 본체 매뉴얼(7장 통신·8장 기능표 = 레지스터 맵)과 "
                "BACnet/IP 옵션 매뉴얼(오브젝트 목록).",
        "enumerate": "list",
        "urls": [
            "https://www.ls-electric.com/upload/customer/download/"
            "a0f00312-4c52-4ccf-a8b8-f8930f4e2199/H100%20English%20Manual_190621.pdf",
            "https://ssq.ls-electric.com/uploads/document/16835073153340/"
            "1+H100+BACNET+IP_Ethernet_User+Manual_EN_V1.0_210526.pdf",
        ],
        "rename": {
            "H100 English Manual_190621.pdf": "LS_H100_UserManual_EN_190621.pdf",
            "1+H100+BACNET+IP_Ethernet_User+Manual_EN_V1.0_210526.pdf":
                "LS_H100_BACnetIP_EN_V1.0_210526.pdf",
        },
        "extractor": "auto",
        "access": "무로그인",
    },
    {
        "id": "samsung-sec-spec-guide",
        "vendor": "Samsung",
        "kind": "정격 카탈로그",
        "note": "삼성전자 **국내(SEC)** 스펙 가이드 64쪽. 표 233개가 62쪽에 걸쳐 있고 "
                "DVM S 국내 라인업(프리미엄·고효율 한랭지형·한랭지형·동시냉난방·표준형·공장전원 / "
                "kW 23~45…)과 소비전력·COP 를 준다. AHU 도 44회 나온다. "
                "⚠ 이 문서가 필요한 이유 — 기존에 들어와 있던 Samsung_DVM_S_Data_Book.pdf 는 "
                "표지가 'DVM S **Desert for ME** (R410A, **50Hz**)' 인 중동 사막 사양이라 "
                "한국(60Hz) 현장 계산에 쓰면 틀린다(대장의 unfit 참고). 이쪽이 국내판이다. "
                "⚠ 2017년 3월 제작이라 최신 형번은 없을 수 있다 — 형번별 정격을 쓸 때 제작일을 함께 본다. "
                "⚠ 같은 내용의 종합 카탈로그(48MB)가 samsung.aiibook.net 에도 있으나 "
                "**제3자 호스트라 넣지 않았다** — 공식 도메인(images.samsung.com/.../sec/)만 쓴다.",
        "enumerate": "list",
        "urls": [
            "https://images.samsung.com/is/content/samsung/p5/sec/"
            "business/business-insights/SP00-0-0.pdf",
        ],
        "rename": {
            "SP00-0-0.pdf": "Samsung_SEC_SpecGuide_KR_2017-03.pdf",
        },
        "extractor": "auto",
        "access": "무로그인",
    },
]


def by_id(sid):
    for s in SOURCES:
        if s["id"] == sid:
            return s
    raise KeyError(sid)
