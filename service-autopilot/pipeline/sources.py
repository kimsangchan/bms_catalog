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
        "kind": "인터페이스·EDE",
        "note": "BACnet 인터페이스 설명서 23종 + Modbus 레지스터 21종 + **EDE 파일(zip)**. "
                "URL 패턴이 규칙적. ⚠ curl 403(봇 차단) — 브라우저로만 내려받힌다.",
        "enumerate": "page",
        "page": "https://www.belimo.com/ch/en_GB/support-eu/support-services/file-history",
        "link_pattern": r"/mam/general-documents/system_integration/(BACnet|Modbus)/[^\"']+\.(pdf|zip|csv)",
        "extractor": "ede",
        "access": "브라우저 필요",
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
