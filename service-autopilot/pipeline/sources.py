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
        "note": "shareddocs.com/hvac/docs 공개 저장소.",
        "enumerate": "list",
        "urls": [
            "https://www.shareddocs.com/hvac/docs/1000/Public/03/11-808-357-01.pdf",
            "https://www.shareddocs.com/hvac/docs/1000/Public/0E/11-808-535-01.pdf",
            "https://www.shareddocs.com/hvac/docs/1001/Public/00/40VM-52ASI-R1.pdf",
        ],
        "extractor": "auto",
        "access": "무로그인",
    },
    # ── 사양 문서 (kind="카탈로그·데이터시트") ─────────────────────────────
    # 통합 포인트 리스트에는 정격이 실리지 않는다. 시뮬레이터가 쓸 전압·전류·
    # 소비전력·용량은 카탈로그와 데이터시트에만 있어 따로 모은다.
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
            for n in ["LMB24-3", "LMB24-SR", "LMB24-3-T", "NMQB24-MFT", "TFB24-S",
                      "FSAF24A", "LF24-S_US", "GMB24-3", "AMB24-3", "NMB24-3"]
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
                "UPS가 붙는다 — 계열 e7(FCU·CRAC)·e19(전력)를 채운다.",
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
]


def by_id(sid):
    for s in SOURCES:
        if s["id"] == sid:
            return s
    raise KeyError(sid)
