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
    "Percentage": "percent", "No Units": None,
    "lpm": "Lpm", "LPM": "Lpm", "gpm": "gpm", "Secs": "s", "Sec": "s",
    "Mins": "min", "Hrs": "h", "Deg F": "degF", "Deg C": "degC",
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


# 대소문자만 다른 표기('PERCENTAGE' vs 'Percentage')를 따로 적지 않기 위한 색인.
# 단, 'C'(섭씨) 와 'c' 처럼 대소문자가 뜻을 가르는 기호는 원표기 조회가 먼저다.
_UNIT_CI = {k.lower(): v for k, v in UNIT_CANON.items()}


def canon_unit(u):
    """정규 단위 코드를 돌려준다. 못 찾으면 None (unit_state 로 상태를 본다)."""
    if u is None:
        return None
    t = str(u).strip()
    if t in NO_UNIT:
        return None
    if t in UNIT_CANON:
        return UNIT_CANON[t]
    return _UNIT_CI.get(t.lower())


# 문서가 단위 대신 **단위 그룹명**만 적은 경우. BACnet 표준의 단위 분류 이름이다.
# 'Percentage' 는 percent 로 확정되지만 'Pressure, Fluidic' 은 kPa 인지 psi 인지
# 문서만으로 알 수 없다 → 없는 값을 지어내지 않고 '그룹만 알려짐'으로 남긴다.
#   BACnet 단위 분류는 '주분류, 세부' 꼴이다 — 주분류만 적어두고 표기 변형은
#   비교 전에 정리한다. 같은 값이 'Pressure, Fluidic'·'PRESSURE FLUIDIC _' 등으로
#   문서마다 다르게 찍혀 나온다.
UNIT_GROUP = {"pressure", "power", "current", "voltage", "temperature", "time",
              "frequency", "energy", "flow", "velocity", "enthalpy", "electrical",
              "humidity", "area", "volume", "mass", "force", "other", "real",
              "enumerated", "boolean", "state", "not applicable", "none"}


def _group_key(u):
    """'PRESSURE FLUIDIC _' → 'pressure' — 표기 변형을 걷어내고 주분류만 남긴다."""
    t = re.sub(r"[_\-]+", " ", str(u or "")).strip().lower()
    t = re.sub(r"\s+", " ", t)
    return re.split(r"[,\s]", t, 1)[0] if t else ""


def unit_group(u):
    t = re.sub(r"[_\-\s]+", " ", str(u or "")).strip().lower()
    return t in UNIT_GROUP or _group_key(u) in UNIT_GROUP


def is_state_text(u):
    """단위가 아니라 상태 설명인가 — '0 = Normal 1 = In Alarm', 'Inactive = Off …'.

    문서에 따라 상태 열이 단위 열 자리에 들어온다. 단위 기호에는 '='가 없으므로
    이것만으로 갈린다. 상태 텍스트를 '정규화 실패'로 세면 진짜 실패가 묻힌다.
    """
    return "=" in str(u or "")


def unit_state(u):
    if u is None or str(u).strip() in NO_UNIT:
        return "unitless"
    if is_state_text(u):
        return "states"
    if canon_unit(u):
        return "ok"
    return "group" if unit_group(u) else "unknown"


def point_key(p):
    """모델 안에서 포인트를 유일하게 식별하는 키"""
    return (canon_type(p.get("type")), p.get("inst"))


def model_id(vendor, model):
    s = "%s-%s" % (vendor, model)
    s = re.sub(r"[™®©]", "", s)
    s = re.sub(r"[^\w가-힣]+", "-", s, flags=re.U).strip("-").lower()
    return re.sub(r"-{2,}", "-", s)
