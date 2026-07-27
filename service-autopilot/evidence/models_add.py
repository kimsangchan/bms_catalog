# -*- coding: utf-8 -*-
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
GRUNDFOS_REG = json.load(open(os.path.join(HERE, "grundfos_modbus.json"), encoding="utf-8"))

def P(inst, t, u, name, note=""):
    return {"inst": inst, "type": t, "unitDisp": u, "name": name, "note": note}

# --- Johnson Controls VRF Smart Gateway (SI-VRFCBN02) 실내기 32점
JCI_IDU = [
    P(4, "AI", "—", "UNIT-CAP · 실내기 용량 코드", "0~255"),
    P(5, "BO", "—", "UNITEN-MODE · 운전 허용", "Shutdown / Enable"),
    P(6, "MO", "—", "SYSTEM-MODE · 운전모드 지령", "1 Cool · 2 Dry · 3 Fan · 4 Heat · 5 Auto"),
    P(7, "BI", "—", "HtClg-REQ · 냉난방 요구", "False / True"),
    P(8, "MO", "—", "SF-SPEED-C · 팬속도 지령", "1 Low · 2 Med · 3 High · 4 Auto"),
    P(9, "AI", "%", "EXPV-% · 팽창밸브 개도", "0.0~100.0 %"),
    P(10, "AI", "℃", "LIQ-PIPE-T · 액관 온도", "-50~99 ℃"),
    P(11, "AI", "℃", "GAS-PIPE-T · 가스관 온도", "-50~99 ℃"),
    P(12, "AI", "℃", "RA-T · 환기(리턴) 온도", "-50~99 ℃"),
    P(13, "AI", "℃", "DA-T · 급기(토출) 온도", "-50~99 ℃"),
    P(14, "AI", "℃", "DIFF-T · 코일 차온", "-127~127 ℃"),
    P(15, "AO", "℃", "ZN-SP · 실내 설정온도", "17~30 ℃"),
    P(16, "AI", "℃", "RZN-T · 리모컨 실내온도", "리모컨 없으면 Unreliable"),
    P(17, "AI", "Hz", "COMP to REQ · 요구 압축기 속도", "0~255 Hz"),
    P(18, "AI", "—", "UNIT-STOP-CODE · 정지 코드", "0~255"),
    P(19, "AI", "—", "ALARM-CODE · 알람 코드", "0~255"),
    P(20, "BI", "—", "RMT-OPT · 실내 서모스탯 옵션", "False / True"),
    P(21, "BI", "—", "DEFROST-S · 제상 상태", "False / True"),
    P(22, "BI", "—", "REM-CON · 리모컨 연결", "False / True"),
    P(23, "BI", "—", "SF-S · 팬 운전 상태", "Off / On"),
    P(24, "BI", "—", "ALARM-S · 알람 상태", "Normal / Alarm"),
    P(25, "MI", "—", "SYSTEM-S · 실제 운전모드", "Cool / Dry / Fan / Heat"),
    P(26, "MI", "—", "SF-SPD · 실제 팬속도", "Low / Med / High"),
    P(27, "AI", "℃", "ZN-T · 실내온도(흡입)", "RA-T와 동일 값"),
    P(28, "BI", "—", "FILT-S · 필터 상태", "Clean / Dirty"),
    P(29, "BO", "—", "FILT-S-RESET · 필터 리셋", "Clean / Dirty"),
    P(30, "BO", "—", "UNIT-LO · 리모컨 운전 잠금", "Unlock / Lock"),
    P(31, "BO", "—", "FANCMD-LO · 리모컨 기동 잠금", "Unlock / Lock"),
    P(32, "BO", "—", "SYSMODE-LO · 리모컨 모드 잠금", "Unlock / Lock"),
    P(33, "BO", "—", "ZNSP-LO · 리모컨 설정온도 잠금", "Unlock / Lock"),
    P(34, "BO", "—", "FANSPD-LO · 리모컨 풍량 잠금", "Unlock / Lock"),
    P(35, "BO", "—", "LOUVER-LO · 리모컨 루버 잠금", "Unlock / Lock"),
]
JCI_ODU = [
    P(3, "AI", "—", "ALARM-CODE · 알람 코드", "0~255"),
    P(6, "MI", "—", "SYSTEM-MODE · 계통 모드", "1 Heat · 2 Cool · 3 Auto"),
    P(7, "MI", "—", "SYSTEM-S · 계통 상태", "13종 (Thermo off·Pump down·Defrost 등)"),
    P(8, "MI", "—", "HX-STATE · 열교환기 상태", "증발/응축 모드 4종"),
    P(9, "MI", "—", "INV-STATE · 인버터 상태", "31종 (과전류·저전압·결상 등)"),
    P(10, "MI", "—", "FAN-STATE · 팬제어 상태", "INV-STATE와 동일 집합"),
    P(11, "AI", "h", "INV-HRS · 인버터 압축기1 운전시간", "0~655,350 h"),
    P(12, "AI", "h", "COMP-HRS · 압축기2 운전시간", "0~655,350 h"),
    P(13, "AI", "Hz", "INV-FREQ · 인버터 압축기 주파수", "0~255 Hz"),
    P(14, "AI", "Hz", "TOTAL-FREQ · 총 주파수", "0~65,535 Hz"),
    P(15, "AI", "%", "FAN-% · 실외기 팬 출력", "0~100 %"),
    P(16, "AI", "%", "EXPV-% · 팽창밸브 개도", "0~100 %"),
    P(17, "AI", "%", "BYPEXPV-% · 바이패스 팽창밸브 개도", "0~100 %"),
    P(18, "AI", "psi", "DISCH-P · 토출 압력", "0~3,698.5 psi"),
    P(19, "AI", "psi", "SUCT-P · 흡입 압력", "0~369.8 psi"),
    P(20, "AI", "℃", "OA-T · 외기온도", "-50~99 ℃"),
    P(21, "AI", "A", "INV2ND-A · 인버터 압축기 보조 전류", "0~127.0 A"),
    P(22, "AI", "A", "INVPRI-A · 인버터 압축기 주 전류", "0~127.0 A"),
    P(23, "AI", "A", "COMP2-A · 압축기2 전류", "0~127.0 A"),
    P(24, "AI", "℃", "INVTOP-T · 인버터 압축기 상부온도", "0~99 ℃"),
    P(25, "AI", "℃", "COMP2TOP-T · 압축기2 상부온도", "0~99 ℃"),
    P(26, "MI", "—", "PROT-CODE · 보호 코드", "9종 (압력비·전류보호 등)"),
    P(27, "BI", "—", "DEFROST-S · 제상 상태", "Off / On"),
    P(28, "BI", "—", "EMERGRUN-S · 비상운전 상태", "Off / On"),
    P(29, "BI", "—", "INV-S · 인버터 상태", "Stop / Run"),
    P(30, "BI", "—", "FAN-S · 팬 상태", "Stop / Run"),
]

VRF_MODEL = {
    "vendor": "Johnson Controls", "model": "SI-VRFCBN02-0Sx",
    "name": "VRF Smart Gateway (Metasys 연동)",
    "cat": "HVAC.AIR.TERMINAL.VRF", "tag": "vrf-indoorUnit-fcu", "status": "active",
    "summary": "VRF 실내기·실외기를 BACnet으로 노출하는 게이트웨이. "
               "실내기 32점 · 실외기 27점이 인스턴스 번호까지 문서에 확정돼 있다.",
    "has": {"spec": False, "points": True},
    "spec": [],
    "comm": [["BACnet", "게이트웨이 표준", "—", "설치 지침서"]],
    "io": [],
    "points": JCI_IDU + [P(0, "—", "—", "── 이하 실외기(ODU) ──", "")] + JCI_ODU,
    "docs": [["설치지침", "VRF Smart Gateway — BACnet Points", "Johnson Controls",
              "24-10143-1183", "—",
              "https://docs.johnsoncontrols.com/bas/r/Metasys/en-US/VRF-Smart-Gateway-Installation-Instructions/E/BACnet-Points", "확보"]],
    "gap": "실내기 정격 스펙(냉난방능력·소비전력·냉매)은 게이트웨이 문서에 없다 → 실내기 제조사 카탈로그 필요. "
           "국내는 삼성 DMS·LG ACP 게이트웨이가 같은 역할이며 포인트 구성이 유사하다(LG ACP: RS-485 4포트·실내기 256대, "
           "삼성 DMS 2.5: 실내기당 제어·감시 25점·최대 256대).",
}

GRUNDFOS = {
    "vendor": "Grundfos", "model": "CIM/CIU 200 (Modbus RTU)",
    "name": "E-pump 통신 인터페이스 모듈 CIM 200",
    "cat": "HVAC.PLANT.PUMP", "tag": "pump", "status": "active",
    "summary": "Grundfos E-펌프를 Modbus RTU로 노출하는 통신 모듈. "
               "적용 제품: CRE/CRNE/CRIE · MTRE · CHIE · CME · TPE(Series 2000) · NBE/NKE · CUE · MAGNA3.",
    "has": {"spec": False, "points": True},
    "spec": [
        ["적용 제품군", "CRE/CRNE/CRIE, MTRE, CHIE, CME, TPE, TPE Series 2000, NBE/NKE, CUE, MAGNA3",
         "—", "E-pump 계열", "Functional profile"],
        ["Modbus 함수 코드", "0x03 읽기(holding) · 0x04 읽기(input) · 0x06 단일쓰기 · 0x10 다중쓰기 · 0x08 진단",
         "—", "—", "Functional profile §8·§12"],
        ["전송 속도", "설정 가능", "bps", "RS-485, 정지비트·패리티 설정", "Functional profile §5.1~5.2"],
        ["주소 지정", "로터리 스위치", "—", "§14 주소표", "Functional profile"],
        ["종단 저항", "모듈 내장", "—", "§5.4", "Functional profile"],
        ["개별 레지스터 주소", "103건 추출", "—", "아래 표 — 확정 전 원문 대조 필요", "Functional profile §9"],
    ],
    "comm": [["Modbus RTU", "CIM/CIU 200", "RS-485", "Functional profile"],
             ["Modbus TCP", "CIM/CIU 500", "Ethernet", "Functional profile"],
             ["BACnet MS/TP", "CIM/CIU 300", "RS-485", "별도 문서"],
             ["BACnet IP", "CIM/CIU 500", "Ethernet", "별도 문서"]],
    "io": [
        ["CIM 설정 레지스터 블록", "§9.2", "모듈 설정", "Functional profile"],
        ["CIM 상태 레지스터 블록", "§9.3", "모듈 상태", "Functional profile"],
        ["펌프 제어 레지스터 블록", "§9.4", "기동·정지·설정값·제어모드", "Functional profile"],
        ["펌프 상태 레지스터 블록", "§9.5", "운전상태·알람", "Functional profile"],
        ["펌프 데이터 레지스터 블록", "§9.6", "전력·유량·양정 등 계측", "Functional profile"],
        ["센서 종속 계측", "§9.7", "부착 센서에 따라 가변", "Functional profile"],
        ["알람 시뮬레이션 / 사용자 블록", "§9.8·§9.9", "시험·사용자 정의", "Functional profile"],
    ],
    "points": GRUNDFOS_REG,
    "docs": [["매뉴얼", "Modbus for Grundfos pumps — Functional profile and user manual",
              "Grundfos", "6012947", "—",
              "https://api.grundfos.com/literature/Grundfosliterature-6012947.pdf", "확보 · 레지스터 추출"],
             ["매뉴얼", "BACnet for Grundfos pumps — CIM/CIU 300 BACnet MS/TP",
              "Grundfos", "6012933", "—",
              "https://api.grundfos.com/literature/Grundfosliterature-6012933.pdf", "확보 · BACnet 오브젝트 미파싱"]],
    "gap": "**레지스터 표 재추출 성공**(아래 103건). 레이아웃 추출이라 설명 열이 일부 밀려 붙었다 — 확정 전 원문 대조 필요. "
           "펌프 정격(유량·양정·출력)은 제품 선정표에서 별도 확보 필요.",
}
