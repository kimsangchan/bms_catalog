# -*- coding: utf-8 -*-
"""공기측 설비 모델 — Belimo VAV-Compact
포인트는 **제조사 배포 EDE 파일을 파서로 취입한 결과**다(ede_parser.py).
"""
import os, importlib.util as _il
_p = _il.spec_from_file_location("bvp", os.path.join(os.path.dirname(os.path.abspath(__file__)), "belimo_vav_points.py"))
_bv = _il.module_from_spec(_p); _p.loader.exec_module(_bv)


def P(i, t, u, n, note=""):
    return {"inst": i, "type": t, "unitDisp": u, "name": n, "note": note}


BELIMO_OBJ = [
    P(0, "Dev", "—", "Device · 장치 식별 번호", "0~4,194,302 · 기본 1"),
    P(1, "AI", "%", "RelPos · 댐퍼 상대 개도", "0~100 % · 기어 분리 시 Overridden"),
    P(2, "AI", "°", "AbsPos · 댐퍼 절대 위치", "0~최대각(회전형 °, 직선형 mm)"),
    P(6, "AI", "%", "SpAnalog · 아날로그 설정값", "아날로그 제어일 때만 유효"),
    P(10, "AI", "%", "RelFlow · 상대 풍량", "정격풍량 V'nom 대비 0~100 %"),
    P(19, "AI", "㎥/h", "AbsFlow_UnitSel · 절대 풍량", "MV[121]에서 고른 단위로 표시"),
    P(20, "AI", "mV", "Sens1Analog · 센서1 아날로그 값", "Sens1Type=Active일 때만"),
    P(1, "AO", "%", "SpRel · 상대 설정값 (풍량 지령)", "V'min~V'max 사이로 스케일"),
    P(97, "AV", "%", "Min · 최소 풍량 V'min", "0~V'max · 기본 0"),
    P(98, "AV", "%", "Max · 최대 풍량 V'max", "V'min~100 · 20% 초과 필수 · 기본 100"),
    P(104, "AV", "㎥/h", "Vnom_UnitSel · 정격 풍량", "선택 단위로 표시"),
    P(130, "AV", "s", "Bus Watchdog · 통신 감시 시간", "0~3600 · 0이면 해제. 만료 시 우선순위 배열 초기화"),
    P(20, "BI", "—", "Sens1Switch · 센서1 접점", "Inactive / Active"),
    P(99, "BI", "—", "BusTermination · 종단저항(120Ω)", "Inactive / Active"),
    P(101, "BI", "—", "SummaryStatus · 종합 상태", "OK / Not OK (MI106·MI110 종합)"),
    P(100, "MI", "—", "InternalActivity · 내부 동작", "1 None · 2 Test · 3 Adaptation"),
    P(106, "MI", "—", "StatusActuator · 액추에이터 상태",
      "1 OK · 2 구동 불가(과부하·구속) · 3 기어 분리 · 4 이동범위 초과"),
    P(110, "MI", "—", "StatusDevice · 장치 상태", "1 OK · 2 Bus Watchdog 만료"),
    P(1, "MO", "—", "Override · 강제 제어",
      "1 None · 2 Open · 3 Close · 4 Min(V'min) · 5 Mid(V'mid) · 6 Max(V'max)"),
    P(120, "MV", "—", "Command · 기능 지령", "1 None · 2 Adaption(원점 조정) · 3 Test · 4 Reset"),
    P(121, "MV", "—", "UnitSelFlow · 풍량 단위 선택",
      "1 m³/s · 2 m³/h(기본) · 3 l/s · 4 l/min · 5 l/h · 6 gpm · 7 cfm"),
    P(122, "MV", "—", "SpSource · 설정값 소스", "1 Analog(0~10V) · 2 Bus(기본)"),
    P(123, "MV", "—", "ControlMode · 제어 모드", "1 PosCtrl(개도) · 2 FlowCtrl(풍량, 정상 운전값)"),
    P(220, "MV", "—", "Sens1Type · 센서1 종류", "Active / Switch / 미사용"),
]

BELIMO_VAV = {
    "vendor": "Belimo", "model": "VAV-Compact (..MV-D3-MOD)",
    "name": "VAV-Compact — 압력센서 + VAV 컨트롤러 + 댐퍼 액추에이터 일체형",
    "cat": "HVAC.AIR.TERMINAL.VAV", "tag": "vav", "status": "active",
    "summary": "차압센서·제어기·액추에이터가 한 몸인 VAV 단말 장치. **제조사가 BACnet EDE 파일(CSV)을 "
               "직접 배포하는 드문 사례**라 오브젝트 목록을 기계가 그대로 읽어들일 수 있다. "
               "모델: LMV-D3-MOD(5Nm) · NMV-D3-MOD(10Nm) · SMV-D3-MOD · LHV-D3-MOD.",
    "has": {"spec": True, "points": True},
    "ede": True,
    "spec": [
        ["전원", "AC/DC 24", "V", "—", "제품 데이터"],
        ["소비전력 (운전 중)", "2 (LMV) / 3 (NMV)", "W", "토크에 따라", "제품 데이터"],
        ["소비전력 (유지)", "1 (LMV) / 1.5 (NMV)", "W", "정지 유지 상태", "제품 데이터"],
        ["배선 산정용 용량", "4 (LMV) / 5 (NMV)", "VA", "전선 굵기 계산용", "제품 데이터"],
        ["토크", "5 (LMV) / 10 (NMV)", "Nm", "댐퍼 크기에 따라 선정", "제품 데이터"],
        ["제어 방식", "BACnet MS/TP · Modbus RTU · MP-Bus · DC 0/2~10 V", "—", "하이브리드(통신+아날로그)", "제품 데이터"],
        ["연결 케이블", "1 m, 6×0.75", "mm²", "—", "제품 데이터"],
        ["BACnet 장치 프로파일", "B-ASC", "—", "BTL 인증 (BTL-31112)", "PICS"],
        ["BACnet 프로토콜 개정", "12", "—", "Vendor ID 423", "PICS"],
        ["COV 구독", "최대 6개 · 수명 1~28,800", "s", "8시간", "PICS"],
        ["제어 모드 주의", "FlowCtrl", "—", "**정상 동작하려면 풍량 제어로 설정해야 한다**(MV[123]=2)", "인터페이스 설명서"],
    ],
    "comm": [
        ["BACnet MS/TP", "내장", "RS-485", "PICS"],
        ["Modbus RTU", "내장", "RS-485", "제품 데이터"],
        ["MP-Bus", "내장", "전용 2선 · 최대 8대", "제품 데이터"],
        ["아날로그", "DC 0/2~10 V", "제어선", "제품 데이터"],
    ],
    "io": [
        ["MS/TP 통신 속도", "9,600 / 19,200 / 38,400 / 76,800 bps", "기본 38,400", "PICS"],
        ["MS/TP 주소", "0~127", "기본 1", "PICS"],
        ["최대 노드 수", "32 (리피터 없이)", "1 full bus load", "PICS"],
        ["종단 저항", "120 Ω", "BI[99]로 상태 확인", "PICS"],
        ["쓰기 제한", "인스턴스 ≥90 영구저장 객체", "**상시 쓰기 금지** — 플래시 수명", "인터페이스 설명서"],
    ],
    "points": _bv.BELIMO_EDE_POINTS,
    "docs": [
        ["인터페이스", "BACnet Interface Description — VAV-Compact V3.08", "Belimo", "V3.08", "2026-01",
         "https://www.belimo.com/mam/general-documents/system_integration/BACnet/belimo_BACnet_Interface-description_VAV_V3_8_en-gb.pdf",
         "확보"],
        ["EDE", "BACnet EDE File — VAV-MOD V3.0.8 (4파일 세트) · **기계판독 CSV**", "Belimo", "V3.0.8", "2025-04-25",
         "https://www.belimo.com/mam/general-documents/system_integration/BACnet/belimo_BACnet_EDE_File_VAV-MOD_V3_0_8.zip",
         "**취입 완료**"],
        ["Modbus", "Modbus Register — VAV V3.8", "Belimo", "V3.8", "—",
         "https://www.belimo.com/mam/general-documents/system_integration/Modbus/belimo_Modbus-Register_VAV_V3_8_en-gb.pdf", "미취입"],
        ["PICS", "BTL Listing 31112 — VAV-Compact", "BACnet International", "BTL-31112", "—",
         "https://www.bacnetinternational.net/btl/listings/belimo%20automation%20ag/BTL_Listing_31112_BELIMO_VAV-Compact.pdf",
         "확보"],
        ["데이터시트", "VAV-Compact D3 Technical datasheet", "Belimo", "—", "—",
         "https://www.belimo.cz/store/belimo-vav-compact-d3-datasheet-en-gb.pdf", "확보"],
    ],
    "gap": "아래 오브젝트 목록은 **손으로 옮긴 것이 아니라 제조사 EDE 파일을 파서가 읽어 만든 것**이다 — 단위 코드(269종)와 상태 문자열(12집합)까지 자동 해석됐다. 벤더 배포 EDE 취입 경로의 첫 실증. "
           "남은 것: Modbus 레지스터 문서 미취입. "
           "VAV 박스 자체의 정격 풍량·인렛 구경은 액추에이터가 아니라 **박스 제조사(OEM)** 자료에 있다 — "
           "Belimo는 OEM 채널로만 공급되므로 박스 제조사 선정표가 별도로 필요하다.",
}


# ── Trane Symbio 800 IntelliCore Split (RAUK) — 공조기(공기측)
import json as _json
_rauk = _json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     "trane_rauk.json"), encoding="utf-8"))

TRANE_RAUK = {
    "vendor": "Trane", "model": "Symbio™ 800 — IntelliCore Split (RAUK)",
    "name": "IntelliCore 스플릿 공조 시스템 — BACnet / Modbus 동시 대응",
    "cat": "HVAC.AIR.AHU", "tag": "ahu", "status": "active",
    "summary": "공기측 설비 첫 모델. **BACnet 오브젝트와 Modbus 레지스터가 1:1로 대응 표기**된 드문 문서라 "
               "두 프로토콜 매핑을 한 번에 확보했다. 압축기 6대(1A~2C)의 운전시간·시동횟수, "
               "이코노마이저 최소개도, 급기온도 중재(arbitration) 구조가 그대로 보인다.",
    "has": {"spec": False, "points": True},
    "spec": [
        ["BACnet 프로파일", "MS/TP · IP · Zigbee(Air-Fi)", "—", "Symbio 800 컨트롤러", "통합가이드 BAS-SVP083"],
        ["Modbus", "RTU · TCP", "—", "동일 포인트를 레지스터로도 노출", "포인트리스트"],
        ["포인트 가변성", "self-configuration", "—",
         "**공장 출하 시 유닛 구성에 따라 노출 포인트가 달라진다** — 같은 모델도 옵션에 따라 다름", "포인트리스트 주석"],
    ],
    "comm": [["BACnet MS/TP", "내장", "RS-485", "통합가이드"],
             ["BACnet IP", "내장", "Ethernet · Wi-Fi", "통합가이드"],
             ["BACnet Zigbee (Air-Fi)", "내장", "무선", "통합가이드"],
             ["Modbus RTU / TCP", "내장", "RS-485 / Ethernet", "통합가이드"],
             ["LonTalk", "별도 가이드", "—", "통합가이드"]],
    "io": [],
    "points": _rauk,
    "docs": [["포인트리스트", "Symbio™ 800 Integration Points List — BACnet/Modbus IntelliCore Split (RAUK)",
              "Trane Technologies", "BAS-PTS036A-EN", "2024-12-04",
              "https://elibrary.tranetechnologies.com/public/commercial-hvac/Literature/Points%20List/BAS-PTS036A-EN_12042024.pdf",
              "**취입 완료**"],
             ["통합가이드", "BACnet® and Modbus Integration — Symbio™ 800", "Trane Technologies",
              "BAS-SVP083A-EN", "2024-08-30",
              "https://www.trane.com/content/dam/Trane/Commercial/global/products-systems/equipment/unitary/rooftop-systems/BAS-SVP083A-EN_08302024.pdf",
              "미취입"],
             ["포인트리스트", "Symbio™ 700 — Precedent/Axiom Rooftop WSHP", "Trane Technologies",
              "BAS-PTS001A-EN", "2024-11-08",
              "https://elibrary.tranetechnologies.com/public/commercial-hvac/Literature/Points%20List/BAS-PTS001A-EN_11082024.pdf",
              "미취입"]],
    "gap": "정격 성능(풍량·정압·코일 용량)은 포인트 문서에 없다 → 제품 카탈로그 필요. "
           "문서가 명시하듯 **노출 포인트는 유닛 구성에 따라 달라진다** — 프로파일을 '모델'이 아니라 "
           "'변형(옵션 조합)' 단위로 둬야 하는 이유의 실증 사례다.",
}
