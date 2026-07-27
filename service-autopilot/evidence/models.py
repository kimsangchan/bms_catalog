# -*- coding: utf-8 -*-
"""L3 모델 데이터 — 근거 문서에서 직접 확인한 값만 담는다. 미확인은 unverified."""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
trane_pts = json.load(open(os.path.join(HERE, "trane_points.json"), encoding="utf-8"))
trane_ctv = json.load(open(os.path.join(HERE, "trane_ctv.json"), encoding="utf-8"))
import importlib.util as _i
_s = _i.spec_from_file_location("madd", os.path.join(HERE, "models_add.py"))
_a = _i.module_from_spec(_s); _s.loader.exec_module(_a)
_s2 = _i.spec_from_file_location("madd2", os.path.join(HERE, "models_add2.py"))
_b = _i.module_from_spec(_s2); _s2.loader.exec_module(_b)
_s3 = _i.spec_from_file_location("madd3", os.path.join(HERE, "models_add3.py"))
_c = _i.module_from_spec(_s3); _s3.loader.exec_module(_c)

DANFOSS_SPEC = [
    ["정격 용량 (200–240 V)", "0.25–45", "kW", "3상", "Fact Sheet"],
    ["정격 용량 (380–480 V)", "0.37–90", "kW", "3상", "Fact Sheet"],
    ["정격 용량 (525–600 V)", "2.2–90", "kW", "3상", "Fact Sheet"],
    ["공급 전압 허용범위", "±10", "%", "—", "Fact Sheet"],
    ["공급 주파수", "50 / 60", "Hz", "—", "Fact Sheet"],
    ["변위 역률 (cos φ)", "> 0.98", "—", "near unity", "Fact Sheet"],
    ["출력 전압", "0–100", "%", "공급 전압 대비", "Fact Sheet"],
    ["출력 주파수", "0–400", "Hz", "개·폐루프", "Fact Sheet"],
    ["가감속 시간", "1–3600", "s", "—", "Fact Sheet"],
    ["보호등급", "IP20 / IP21(UL Type 1, 옵션) / IP54", "—", "—", "Fact Sheet"],
    ["최대 주위온도", "50", "℃", "강제공랭 불요", "Fact Sheet"],
    ["내장 EMC 필터", "C1 / C2 / C3", "—", "C3 기본, C1·C2 옵션", "Fact Sheet"],
    ["고조파 대책", "DC 초크 내장", "—", "EN 61000-3-12 충족", "Fact Sheet"],
    ["옵션 고조파 필터", "5 / 10", "% THDi", "옵션", "Fact Sheet"],
    ["에너지 절감", "최대 25", "%", "제품 페이지는 50% — **출처 불일치**", "Fact Sheet"],
    ["과부하 내량", "—", "—", "**unverified** · Design Guide 필요", "미확보"],
    ["용량별 정격 출력전류", "—", "A", "**unverified** · Design Guide 필요", "미확보"],
]
DANFOSS_IO = [
    ["디지털 입력", "4", "PNP/NPN 선택, 0–24 V DC", "Fact Sheet"],
    ["아날로그 입력", "2", "0–10 V 또는 0/4–20 mA (스케일 가능)", "Fact Sheet"],
    ["아날로그 출력", "2", "0/4–20 mA (디지털 출력 겸용)", "Fact Sheet"],
    ["릴레이 출력", "2", "240 V AC 2 A / 400 V AC 2 A", "Fact Sheet"],
]

# Danfoss FC-101 3x380–480 V AC 전기 데이터 (Design Guide §5.1.2 Table 12)
# 값 출처: pdftotext 추출. 효율 열은 PDF 줄바꿈으로 소수 둘째자리가 분리돼 복원한 값 → 원문 재확인 권장.
DANFOSS_ELEC = [
    ["PK37", "0.37", "1.2", "1.2", "13 / 15", "97.8 / 97.3"],
    ["PK75", "0.75", "2.2", "2.1", "16 / 21", "98.0 / 97.6"],
    ["P1K5", "1.5", "3.7", "3.5", "46 / 57", "97.7 / 97.2"],
    ["P2K2", "2.2", "5.3", "4.7", "46 / 58", "98.3 / 97.9"],
    ["P3K0", "3.0", "7.2", "6.3", "66 / 83", "98.2 / 97.8"],
    ["P4K0", "4.0", "9.0", "8.3", "95 / 118", "98.0 / 97.6"],
    ["P5K5", "5.5", "12", "11.2", "104 / 131", "98.4 / 98.0"],
    ["P7K5", "7.5", "15.5", "15.1", "159 / 198", "98.2 / 97.8"],
    ["P11K", "11", "23", "22.1", "248 / 274", "98.1 / 97.9"],
    ["P15K", "15", "—", "—", "353 / 379", "98.0 / 97.8"],
    ["P18K", "18.5", "—", "—", "412 / 456", "98.1 / 97.9"],
    ["P22K", "22", "—", "—", "475 / 523", "98.1 / 97.9"],
    ["P30K", "30", "—", "—", "733", "97.8"],
    ["P37K", "37", "—", "—", "922", "97.7"],
    ["P45K", "45", "—", "—", "1067", "98.0"],
    ["P55K", "55", "—", "—", "1133", "98.2"],
    ["P75K", "75", "—", "—", "1733", "97.8"],
    ["P90K", "90", "—", "—", "2141", "97.9"],
]

DANFOSS_COMM = [
    ["BACnet MS/TP", "표준 내장", "RS-485", "Fact Sheet"],
    ["Modbus RTU", "표준 내장", "RS-485", "Fact Sheet"],
    ["FC Protocol", "표준 내장", "RS-485", "Fact Sheet"],
    ["N2 Metasys", "표준 내장", "RS-485", "Fact Sheet"],
    ["FLN Apogee", "표준 내장", "RS-485", "Fact Sheet"],
]

MODELS = {
    15: [{
        "vendor": "Danfoss", "model": "FC-101",
        "name": "VLT® HVAC Basic Drive FC 101",
        "cat": "HVAC.AUX.VFD", "tag": "vfd", "status": "active",
        "summary": "팬·펌프용 HVAC 전용 인버터. 유도전동기와 PM 전동기 모두 구동.",
        "has": {"spec": True, "points": False},
        "spec": DANFOSS_SPEC, "comm": DANFOSS_COMM, "io": DANFOSS_IO, "points": [],
        "elec": {"header": ["형식", "축출력 kW", "출력전류 A (40℃ 연속)", "입력전류 A (연속)",
                            "**손실 W** (best/typ)", "**효율 %** (best/typ)"], "rows": DANFOSS_ELEC,
                 "note": "3x380–480 V AC · Design Guide §5.1.2 Table 12·13. **정격점 값이다.** EN 50598-2(=IEC 61800-9-2) 기준 **부분부하 8운전점 손실**은 데이터시트에 없고 제조사 계산기(Danfoss MyDrive Energy Efficiency Calculator)에 있다. typical=정격 조건, best case=고입력전압·저스위칭주파수."},
        "docs": [["카탈로그", "VLT® HVAC Basic Drive FC 101 Fact Sheet", "Danfoss Drives",
                  "DKDD.PFP.100.A4.02", "2017-07",
                  "https://files.danfoss.com/download/Drives/DKDDPFP100A402_HVAC_Basic.pdf", "확보"],
                 ["매뉴얼", "VLT® HVAC Basic Drive FC 101 Design Guide", "Danfoss Drives",
                  "AJ275648114271", "—",
                  "https://assets.danfoss.com/documents/latest/514925/AJ275648114271en-001201.pdf", "미확보"]],
        "gap": "**전기 데이터 확보 완료**(아래 표). 남은 것: ⑴ EN 50598-2 부분부하 8운전점 손실 — Danfoss MyDrive Energy 계산기에서 추출 필요 ⑵ Modbus 레지스터 표(Design Guide §10.8.8 Coil/Register) ⑶ 과부하 내량 ⑷ 주위온도·스위칭주파수 디레이팅 곡선(§6.3.1).",
    }],
    9: [{
        "vendor": "Trane", "model": "Symbio™ 800 (UC800)",
        "name": "Symbio™ 800 냉동기 컨트롤러 — BACnet ACSA",
        "cat": "HVAC.PLANT.CHILLER", "tag": "chiller", "status": "active",
        "summary": "흡수식 냉동기(ACSA) + UC800 컨트롤러의 BACnet 통합 포인트. "
                   "기종(CGAM·CTV 등)이 바뀌면 포인트 리스트가 별도로 존재한다.",
        "has": {"spec": False, "points": True},
        "spec": [], "comm": [["BACnet", "통합 포인트 리스트 공개", "—", "Points List"],
                             ["Modbus RTU", "별도 문서", "—", "BAS-SVP022"]],
        "io": [], "points": trane_pts,
        "docs": [["포인트리스트", "Symbio™ 800 Integration Points List — BACnet ACSA (UC800)",
                  "Trane Technologies", "BAS-PTS026A-EN", "2024-12-06",
                  "https://elibrary.tranetechnologies.com/public/commercial-hvac/Literature/Points%20List/BAS-PTS026A-EN_12062024.pdf", "확보"],
                 ["포인트리스트", "Symbio™ 800 — BACnet CGAM (CH530)", "Trane Technologies",
                  "BAS-PTS027A-EN", "2024-12-06",
                  "https://elibrary.tranetechnologies.com/public/commercial-hvac/Literature/Points%20List/BAS-PTS027A-EN_12062024.pdf", "미추출"],
                 ["포인트리스트", "Symbio™ 800 — BACnet CTV-Simplex (UC800)", "Trane Technologies",
                  "BAS-PTS029A-EN", "2024-12-06",
                  "https://elibrary.tranetechnologies.com/public/commercial-hvac/Literature/Points%20List/BAS-PTS029A-EN_12062024.pdf", "미추출"]],
        "gap": "정격 스펙(냉동능력·COP·유량 등) 값 미확보 → 제품 카탈로그/성능표 필요. "
               "포인트 이름·인스턴스·단위는 PDF에서 자동 추출한 것이라 일부 표기가 원문과 다를 수 있다.",
    }, {
        "vendor": "Trane", "model": "Symbio™ 800 (UC800) — CTV",
        "name": "Symbio™ 800 원심(터보) 냉동기 — BACnet CTV-Simplex",
        "cat": "HVAC.PLANT.CHILLER", "tag": "chiller", "status": "active",
        "summary": "같은 UC800 컨트롤러라도 **기종이 다르면 포인트가 다르다**는 실증. "
                   "흡수식(ACSA) 98점 대비 원심(CTV)은 217점이다.",
        "has": {"spec": False, "points": True},
        "spec": [], "comm": [["BACnet", "통합 포인트 리스트 공개", "—", "Points List"]],
        "io": [], "points": trane_ctv,
        "docs": [["포인트리스트", "Symbio™ 800 Integration Points List — BACnet CTV-Simplex (UC800)",
                  "Trane Technologies", "BAS-PTS029A-EN", "2024-12-06",
                  "https://elibrary.tranetechnologies.com/public/commercial-hvac/Literature/Points%20List/BAS-PTS029A-EN_12062024.pdf", "확보"]],
        "gap": "정격 스펙 미확보. (CGAM 리스트는 pdftotext 재추출로 확보 — 아래 모델 참조)",
    }, _b.TRANE_CGAM],
    5: [_c.TRANE_RAUK],
    6: [_c.BELIMO_VAV],
    8: [_a.VRF_MODEL, _b.DAIKIN],
    14: [_a.GRUNDFOS],
}

# L3 확보 현황 (계열번호: [상태, 다음에 받을 문서])
L3_STATUS = {
    5:  ["확보", "[Trane Symbio 800 IntelliCore Split(RAUK) 포인트리스트](https://elibrary.tranetechnologies.com/public/commercial-hvac/Literature/Points%20List/BAS-PTS036A-EN_12042024.pdf) — 취입 완료(136점) · [Trane Symbio 700 RTU](https://elibrary.tranetechnologies.com/public/commercial-hvac/Literature/Points%20List/BAS-PTS001A-EN_11082024.pdf) · 원본 통합가이드 — [Carrier i-Vu BACnet Integration Guide](https://www.shareddocs.com/hvac/docs/1000/Public/03/11-808-357-01.pdf) · Siemens Desigo 애플리케이션 라이브러리"],
    6:  ["확보", "**Belimo EDE 파일(zip) 취입** — [제품 페이지](https://www.belimo.com/ch/shop/en_GB/p?code=LMV-D3-MOD) · VAV 박스 OEM 선정표(정격풍량·인렛구경)"],
    7:  ["미확보", "FCU 카탈로그 + 게이트웨이 포인트 맵 — Belimo 밸브 액추에이터 문서가 [File Archive](https://www.belimo.com/ch/en_GB/support-eu/support-services/file-history)에 공개 — [Carrier ChillerVu Application Guide](https://www.shareddocs.com/hvac/docs/1000/Public/0E/11-808-535-01.pdf)"],
    8:  ["확보", "실내기 정격(냉난방능력·소비전력) — [LG ACP 포인트리스트](https://rji-sales.com/wp-content/uploads/2014/03/LG_BacNet_Submittal_PointsList_PQNFB17C1.pdf) · [삼성 MIM-B17BN](https://s3.amazonaws.com/samsung-files/Tech_Files/Controls/Central+Control/Submittals/MIM-B17BN_MIM-B17BUN+SUBMITTAL_BAC2.5_092017A.PDF) · [Daikin DMS502B71](https://daikincomfort.com/docs/default-source/interface-for-use-bacnet-/eg-dms502b71bacnet-guide.pdf)"],
    9:  ["일부 확보", "정격 성능표(냉동능력·COP 곡선) — [York YVAA/YVFA BACnet·Modbus 데이터맵](https://docs.johnsoncontrols.com/chillers/v/u/YORK/en-US/YVAA-YVFA-YAGK-Native-BACnet-and-Modbus-N2-Data-Map/322)"],
    10: ["미확보", "냉각탑 성능표 — 설계 습구·어프로치·레인지 3온도가 필수 (제조사 선정 시트)"],
    11: ["미확보", "보일러 카탈로그 + 효율곡선(부분부하·수온)"],
    12: ["미확보", "판형 열교환기 선정표 / 전열교환기 카탈로그"],
    13: ["미확보", "송풍기 성능곡선 — **곡선계수가 아니라 유량-압력 점 배열**로 확보할 것"],
    14: ["일부 확보", "[Grundfos CIM/CIU BACnet Functional Profile](https://api.grundfos.com/literature/Grundfosliterature-6012933.pdf) · 펌프 성능곡선(Q-H) 점 배열"],
    15: ["일부 확보", "[Danfoss VLT Modbus RTU 운영지침](https://files.danfoss.com/download/Drives/MG10S202.pdf) · [Modbus TCP 모듈](https://files.danfoss.com/download/Drives/MG17N102.pdf) · [ABB ACH580 문서](https://library.abb.com/r?cid=9AAC182825&lang=en)"],
    16: ["미확보", "**[Belimo EDE CSV](https://www.belimo.com/mam/general-documents/system_integration/BACnet/belimo_BACnet_EDE_File_TEM.csv)** — 기계판독 실물 · [Belimo File Archive](https://www.belimo.com/ch/en_GB/support-eu/support-services/file-history)"],
    19: ["미확보", "디지털 계전기·전력미터 Modbus 맵 — [BTL 목록](https://www.bacnetinternational.net/btl/)에서 Schneider·LS 검색"],
    20: ["미확보", "DALI 게이트웨이 사양"],
    21: ["미확보", "화재 수신기 연동 접점표 (감시 전용)"],
    22: ["미확보", "승강기 벤더 BMS 연동 인터페이스 사양"],
    23: ["미확보", "NVR·출입 컨트롤러 연동 API/접점표"],
    24: ["미확보", "IAQ 센서 통신 사양 + 실내공기질 관리법 유지기준 원문"],
    25: ["미확보", "부스터 펌프 유닛·수위계 통신 사양"],
}
