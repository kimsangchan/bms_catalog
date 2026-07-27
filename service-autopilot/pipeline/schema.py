# -*- coding: utf-8 -*-
"""카탈로그 데이터 형식 정의 — 모든 저장소는 이 형식 하나로 통일한다.

지금까지 마크다운(장비 공통) · 파이썬 딕셔너리(모델) · JSON(파서 결과)로 흩어져 있던 것을
JSON 한 벌로 모은다. 파이썬 파일은 더 이상 데이터 저장소가 아니다.

디렉터리
  data/equips/<equip-id>.json    장비 계열 (공통 사양·표준 포인트)
  data/models/<model-id>.json    모델 (정격·통신·오브젝트 목록·근거)
  data/docs.json                 문서 메타 (경로·해시·출처·상태)
  data/known-good.json           검증용 정답 대조셋
"""
import re

# ── BACnet 오브젝트 타입 canonical 코드
BACNET_TYPES = {"AI", "AO", "AV", "BI", "BO", "BV", "MSI", "MSO", "MSV",
                "MI", "MO", "MV", "Dev", "NC", "SV", "LAV", "TL", "Sched", "Cal", "Loop"}
# ── LonTalk 네트워크 변수 — BACnet 오브젝트는 아니지만 같은 '통신 맵' 자리에 들어간다
#    NV  = nvi(입력)·nvo(출력) 네트워크 변수 — 실시간 데이터
#    NCI = nci 설정 네트워크 변수 — 커미셔닝 시 쓰는 구성값
LON_TYPES = {"NV", "NCI"}
# ── Modbus 레지스터 — 같은 문서에 BACnet 오브젝트와 나란히 실려 있는 경우가 많다
#    인스턴스 = 레지스터 주소(3xxxx 입력, 4xxxx 홀딩)
MODBUS_TYPES = {"MB"}
OBJ_TYPES = BACNET_TYPES | LON_TYPES | MODBUS_TYPES | {"—"}
# MI/MO/MV 는 문서 표기 그대로 받아들이되 canonical 은 MSI/MSO/MSV
TYPE_ALIAS = {"MI": "MSI", "MO": "MSO", "MV": "MSV"}

# 프로토콜 판정 — 오브젝트 타입만 보고 어느 통신 맵인지 알 수 있다
def protocol_of(t):
    c = canon_type(t)
    if c in LON_TYPES:
        return "LonTalk"
    if c in MODBUS_TYPES:
        return "Modbus"
    return "BACnet"

# ── 단위 정규화 (실측 표기 변형 → canonical)
UNIT_CANON = {
    "℃": "degC", "°C": "degC", "degC": "degC", "C": "degC",
    "℉": "degF", "°F": "degF", "degF": "degF",
    "%": "percent", "percent": "percent", "%RH": "percentRH",
    "CMH": "m3h", "㎥/h": "m3h", "m³/h": "m3h", "m3/h": "m3h", "m³/hr": "m3h", "m3h": "m3h",
    "㎥/s": "m3s", "m³/s": "m3s", "L/s": "Lps", "l/s": "Lps",
    "L/min": "Lpm", "l/min": "Lpm", "LPM": "Lpm", "L/h": "Lph",
    "Hz": "Hz", "V": "V", "A": "A", "mA": "mA", "kW": "kW", "kWh": "kWh", "W": "W",
    "kVA": "kVA", "kvar": "kvar", "VA": "VA",
    "Pa": "Pa", "kPa": "kPa", "MPa": "MPa", "mmAq": "mmH2O", "mmH2O": "mmH2O", "psi": "psi",
    "ppm": "ppm", "㎍/㎥": "ugm3", "Bq/㎥": "Bqm3", "lux": "lux", "lm": "lm", "K": "K",
    "s": "s", "min": "min", "h": "h", "㎥": "m3", "m3": "m3", "mm": "mm", "°": "deg",
    "Ω": "ohm", "mV": "mV", "rpm": "rpm", "Nm": "Nm", "dB(A)": "dBA", "RT": "RT",
    "kcal/h": "kcalh", "N㎥/h": "Nm3h", "mg/L": "mgL", "µS/cm": "uScm", "W/㎡": "Wm2",
    "m/s": "ms", "PSI": "psi", "Hours": "h", "Hour": "h", "Minutes": "min",
    "Seconds": "s", "Amps": "A", "Volts": "V", "Percent": "percent",
    "Temperature": None, "Pressure": None, "Real": None, "No Units": None,
    "인": "person", "회": "count", "층": "floor", "—": None, "": None,
}

REQUIRED_EQUIP = ["id", "no", "title", "domain"]
REQUIRED_MODEL = ["id", "vendor", "model", "name", "equipId", "cat", "tag"]
REQUIRED_POINT = ["type", "name"]
REQUIRED_DOC = ["kind", "title", "publisher", "url", "status"]

DOC_STATUS = {"확보", "취입 완료", "미취입", "미추출", "미확보", "확보 · 미파싱"}
EXTRACTORS = {"table", "ede", "layout", "manual", "html"}


def canon_type(t):
    t = (t or "—").strip()
    return TYPE_ALIAS.get(t, t)


NO_UNIT = {"", "—", "-", "None", "N/A", "*", "none"}


def canon_unit(u):
    """정규 단위 코드를 돌려준다. (코드, 상태) — 상태: ok | unitless | unknown"""
    if u is None:
        return None
    t = str(u).strip()
    if t in NO_UNIT:
        return None
    return UNIT_CANON.get(t, None)


def unit_state(u):
    if u is None or str(u).strip() in NO_UNIT:
        return "unitless"
    return "ok" if UNIT_CANON.get(str(u).strip()) else "unknown"


def point_key(p):
    """모델 안에서 포인트를 유일하게 식별하는 키"""
    return (canon_type(p.get("type")), p.get("inst"))


def model_id(vendor, model):
    s = "%s-%s" % (vendor, model)
    s = re.sub(r"[™®©]", "", s)
    s = re.sub(r"[^\w가-힣]+", "-", s, flags=re.U).strip("-").lower()
    return re.sub(r"-{2,}", "-", s)
