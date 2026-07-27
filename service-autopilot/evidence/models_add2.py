# -*- coding: utf-8 -*-
"""2차 추가 모델 — pdftotext로 재추출 성공한 문서 기반."""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
cgam = json.load(open(os.path.join(HERE, "trane_cgam.json"), encoding="utf-8"))
gmod = json.load(open(os.path.join(HERE, "grundfos_modbus.json"), encoding="utf-8"))


def P(i, t, u, n, note=""):
    return {"inst": i, "type": t, "unitDisp": u, "name": n, "note": note}


# Daikin DMS502B71 — 실내기 멤버 오브젝트 (Design Guide EDUS72-749C, Object Point List)
DAIKIN_MEMBERS = [
    P(1, "BO", "—", "StartStopCommand · 운전·정지 지령", "On / Off"),
    P(2, "BI", "—", "StartStopStatus · 운전 상태", "On / Off"),
    P(3, "BI", "—", "Alarm · 알람", "Normal / Malfunction"),
    P(4, "MI", "—", "MalfunctionCode · 고장 코드", "Daikin 지정 코드"),
    P(5, "MO", "—", "AirConModeCommand · 운전모드 지령", "Cool / Heat / Fan / Auto / Dry"),
    P(6, "MI", "—", "AirConModeStatus · 운전모드 상태", "Cool / Heat / Fan / Dry"),
    P(7, "MO", "—", "AirFlowRateCommand · 풍량 지령", "Low / … "),
    P(8, "MI", "—", "AirFlowRateStatus · 풍량 상태", "Low / …"),
    P(9, "AI", "℃", "RoomTemp · 실내온도", "℃ / ℉"),
    P(10, "AV", "℃", "TempAdjust · 설정온도", "℃ / ℉"),
    P(11, "BI", "—", "FilterSign · 필터 신호", "No / Yes"),
    P(12, "BV", "—", "FilterSignReset · 필터 신호 리셋", "Reset"),
    P(13, "BV", "—", "RemoteControlStart · 리모컨 운전 허용", "Permit / Prohibit"),
    P(14, "BV", "—", "RemoteControlAirConModeSet · 리모컨 모드 허용", "Permit / Prohibit"),
    P(16, "BV", "—", "RemoteControlTempAdjust · 리모컨 설정온도 허용", "Permit / Prohibit"),
    P(18, "—", "—", "GasTotalPower · 적산 가스", "Accumulator"),
    P(19, "—", "kWh", "ElecTotalPower · 적산 전력", "Accumulator"),
    P(20, "BI", "—", "CommunicationStatus · 통신 상태", "Normal / Communication error"),
    P(21, "BV", "—", "SystemForcedOff · 강제 정지", "Inactive / Active"),
    P(22, "AV", "—", "AirDirectionCommand · 풍향 지령", ""),
    P(23, "AI", "—", "AirDirectionStatus · 풍향 상태", ""),
    P(24, "BO", "—", "ForcedThermoOFFCommand · 강제 서모오프 지령", "Inactive / Active"),
    P(25, "BI", "—", "ForcedThermoOFFStatus · 강제 서모오프 상태", "Inactive / Active"),
    P(26, "BO", "—", "EnergyEfficiencyCommand · 절전 지령", "Inactive / Active"),
    P(27, "BI", "—", "EnergyEfficiencyStatus · 절전 상태", "Inactive / Active"),
    P(28, "BI", "—", "ThermoStatus · 서모온 상태", "Off / On"),
    P(29, "BI", "—", "CompressorStatus · 압축기 상태", "Off / On"),
    P(30, "BI", "—", "IndoorFanStatus · 실내팬 상태", "Off / On"),
    P(31, "BI", "—", "HeaterStatus · 히터 상태", "Off / On"),
    P(32, "MO", "—", "VentilationModeCommand · 환기모드 지령", "Bypass / ERV / Auto"),
    P(33, "MI", "—", "VentilationModeStatus · 환기모드 상태", "Bypass / ERV / Auto"),
    P(34, "MO", "—", "VentilationAmountCommand · 환기량 지령", "Low / High / Auto"),
    P(35, "MI", "—", "VentilationAmountStatus · 환기량 상태", "Low / High / Auto"),
]

DAIKIN = {
    "vendor": "Daikin", "model": "DMS502B71",
    "name": "VRV BACnet 인터페이스 (DIII-NET ↔ BACnet 게이트웨이)",
    "cat": "HVAC.AIR.TERMINAL.VRF", "tag": "vrf-indoorUnit-fcu", "status": "active",
    "summary": "실내기 1대당 **멤버 오브젝트 35종**을 노출한다. DIII 포트 4개 × 64대 = **최대 256대**를 "
               "하나의 게이트웨이가 담당하며, 오브젝트 ID는 목록이 아니라 **계산식**으로 정해진다.",
    "has": {"spec": False, "points": True},
    "spec": [
        ["최대 접속 실내기", "256", "대", "DIII 포트 4개 × 64대", "Design Guide"],
        ["오브젝트 ID 계산식", "ObjectType×2²² + 실내기번호×256 + 멤버번호", "—",
         "예: 실내기 000 · StartStopCommand → BO(4) + 0×256 + 1 = **16777217**", "Design Guide"],
        ["오브젝트 타입 오프셋", "AV=2 · BI=3 · BO=4 · BV=5 · MI=13 · MO=14", "—",
         "타입별 ID 베이스", "Design Guide"],
        ["실내기당 멤버 오브젝트", "35", "종", "아래 표", "Design Guide"],
    ],
    "comm": [["BACnet/IP", "게이트웨이 표준", "Ethernet", "Design Guide"],
             ["DIII-NET", "실내기 측", "전용 2선", "Design Guide"]],
    "io": [], "points": DAIKIN_MEMBERS,
    "docs": [["매뉴얼", "Interface for use in BACnet — Design Guide (DMS502B71)", "Daikin",
              "EDUS72-749C", "—",
              "https://daikincomfort.com/docs/default-source/interface-for-use-bacnet-/eg-dms502b71bacnet-guide.pdf",
              "확보"]],
    "gap": "실내기 정격(냉난방능력·소비전력·냉매)은 게이트웨이 문서에 없다 → 실내기 카탈로그 필요. "
           "**오브젝트 ID가 계산식이라 실내기 수만큼 자동 전개된다** — 카탈로그가 '식'을 저장해야지 "
           "8,960개(256×35) 행을 저장할 일이 아니다.",
}

TRANE_CGAM = {
    "vendor": "Trane", "model": "Symbio™ 800 (CH530) — CGAM",
    "name": "Symbio™ 800 공랭 스크류 냉동기 — BACnet CGAM",
    "cat": "HVAC.PLANT.CHILLER", "tag": "chiller", "status": "active",
    "summary": "앞서 자동 추출에 실패했던 문서를 **pdftotext로 재추출해 확보**했다. "
               "회로 2개(Ckt1/Ckt2)·압축기 6대(1A~2C)의 시동 횟수·운전시간이 개별 포인트로 나온다.",
    "has": {"spec": False, "points": True},
    "spec": [], "comm": [["BACnet", "통합 포인트 리스트 공개", "—", "Points List"]],
    "io": [], "points": cgam,
    "docs": [["포인트리스트", "Symbio™ 800 Integration Points List — BACnet CGAM (CH530)",
              "Trane Technologies", "BAS-PTS027A-EN", "2024-12-06",
              "https://elibrary.tranetechnologies.com/public/commercial-hvac/Literature/Points%20List/BAS-PTS027A-EN_12062024.pdf",
              "확보"]],
    "gap": "레이아웃 추출이라 설명·단위 열이 한 행씩 밀려 붙은 경우가 있다 — **단위 열은 참고값**으로 보고 "
           "확정 전 원문 대조 필요. 정격 성능표는 별도 카탈로그 필요.",
}

GRUNDFOS_REG = gmod
