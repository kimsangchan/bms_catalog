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

SOURCES = [
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
                "CAT 261(Rebel DPS 옥상형 3~31톤)·ED 19116(Rebel 물리 데이터 시트). "
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
        "vendor": "Johnson Controls / York",
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
        ],
        # dA 해시 경로라 파일명이 문서번호뿐이다 — 표지 문서번호·제품명으로 바꿔 적는다
        "rename": {
            "508112-02a.pdf": "Lennox_CORE_BACnet_SetupGuide_508112-02.pdf",
            "ehb_lgt_abox_2411.pdf": "Lennox_Enlight_LGT_EHB_210977.pdf",
            "37J51_Enlight+Brochure+454B.pdf": "Lennox_Enlight_Brochure_37J51.pdf",
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
