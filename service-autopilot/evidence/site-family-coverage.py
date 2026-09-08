# -*- coding: utf-8 -*-
"""현장 포인트리스트의 설비가 19계열에 전부 붙는가 — 덮개 감사 (읽기 전용).

세는 단위는 **설비코드**다(포인트가 아니다). 스냅샷이 월별로 겹쳐 있어 같은 설비가
여러 파일에 나오므로 코드로 중복을 없앤다.
"""
import collections
import csv
import glob
import io
import os
import re
import sys

ROOT = os.path.join('service-autopilot', '포인트리스트')

# 설비 약어 → 계열. 뜻은 원문 OBJ_DESC 에서 읽은 것이다(10-site-driven-priority.md 표).
FAMILY = [
    # 접두 한 글자가 쓰임새를 가른다 — 계열이 다른 게 아니라 이름 변형이다.
    #   공조기: OHU 외기처리(외조기) · CHU 급기 · HVU 환기 · PAH 패키지 · AVU
    ("e5",  "공조기 (AHU)",           r"^(AH|AHU|HV|HVU|OAC|OAU|OHU|CHU|PAH|AVU|DOAS)$"),
    ("e6",  "터미널 (VAV·CAV)",       r"^(VAV|CAV|FPB)$"),
    ("e7",  "FCU · 항온항습기",        r"^(FCU|FC|CRAC|PAC|AHP)$"),
    ("e8",  "VRF / DVM",              r"^(DVM|VRF|IDU|ODU|EHP)$"),
    ("e9",  "냉동기 (칠러)",           r"^(CH|CHR|DACH|TR|ABS|CHILLER)$"),
    ("e10", "냉각탑",                 r"^(CT|CTW|COOLINGTOWER)$"),
    ("e11", "보일러 · 온수발생기",       r"^(BO|BLR|HWG|HWB|STG|BOILER)$"),
    ("e12", "열교환기 · 전열교환기",     r"^(HX|HE|PHE|ERV|HRV|TEV)$"),
    #   송풍기: K 주방 · T 화장실 · P 주차장 · S 오배수 · L 유인
    ("e13", "송풍기 (급·환·배기)",
     r"^(SF|RF|EF|FAN|PF|JF|OAF|VF|KEF|KSF|TEF|TSF|PSF|PEF|SEF|LF|GEF)$"),
    ("e14", "펌프",                   r"^(P|PU|PMP|CHP|CWP|HWP|SP|BP|FP|EEP)$"),
    ("e15", "인버터 (VFD)",           r"^(INV|VFD|VSD)$"),
    ("e16", "계량·계측·제어기",         r"^(FM|WM|EM|MT|SEN|TC|DDC|ICU|UC)$"),
    ("e19", "전력 설비",              r"^(TR2|MCC|ACB|VCB|GEN|UPS|ATS|PNL|SW|LP|EP)$"),
    ("e20", "조명 · 차양",            r"^(LT|LGT|LIGHT|BL|SH)$"),
    ("e21", "방재 (소방·제연·검지)",    r"^(FD|SD|GD|SM|PD|FIRE|DP)$"),
    ("e22", "승강 설비",              r"^(EV|ELV|ESC)$"),
    ("e24", "환경 · 실내공기질",        r"^(IAQ|CO2|TH|WS)$"),
    ("e25", "급배수 · 위생",
     r"^(WT|WTR|TK|STP|WWT|GT|SUMP|EET|WTANK|OILTNK|HWT)$"),
]
COMPILED = [(e, ko, re.compile(p, re.I)) for e, ko, p in FAMILY]

CODE_A = re.compile(r"(?<![A-Z0-9])(\d)-([A-Z]{2,5})-(\d{2,4})")   # 1-AH-112 (셔블)
CODE_B = re.compile(r"^([A-Z]{2,6})[-_](\d{2,4})")            # AHU-115_… (네이버)
CODE_C = re.compile(r"^([A-Z]{2,10})_")                       # CHILLER_… (AAC)


def classify(abbr):
    for e, ko, rx in COMPILED:
        if rx.match(abbr):
            return e, ko
    return None, None


def scan_csv():
    hits = collections.defaultdict(set)     # 약어 → {설비코드}
    desc = collections.defaultdict(collections.Counter)
    files = glob.glob(os.path.join(ROOT, '포인트리스트_자동제어', '**', '*.csv'),
                      recursive=True)
    for f in files:
        for enc in ('utf-8-sig', 'cp949'):
            try:
                with io.open(f, encoding=enc) as fh:
                    rows = list(csv.DictReader(fh))
                break
            except (UnicodeDecodeError, LookupError):
                continue
        else:
            continue
        for row in rows:
            name = (row.get('OBJ_NAME') or '').strip()
            d = (row.get('OBJ_DESC') or '').strip()
            # 맨 앞에서만 찾으면 안 된다 — `A_1-CH-101_STATUS` 처럼 코드가 이름
            # 가운데 박힌 판이 있다. 실제로 그래서 냉동기가 0대로 나왔다.
            m = CODE_A.search(name) or CODE_A.search(d)
            if m:
                abbr, code = m.group(2).upper(), m.group(0)
                hits[abbr].add(code)
                if d:
                    desc[abbr][d[:46]] += 1
    return hits, desc, len(files)


XLSX_ONLY = set()


def scan_xlsx():
    hits = collections.defaultdict(set)
    desc = collections.defaultdict(collections.Counter)
    try:
        import openpyxl
    except ImportError:
        return hits, desc, 0
    paths = (glob.glob(os.path.join(ROOT, '네이버', '**', '*.xlsx'), recursive=True) +
             glob.glob(os.path.join(ROOT, 'csv파일', '*.xlsx')))
    for p in paths:
        try:
            wb = openpyxl.load_workbook(p, read_only=True, data_only=True)
        except Exception:
            continue
        for ws in wb.worksheets:
            for row in ws.iter_rows(values_only=True):
                cells = [str(c).strip() for c in row if c is not None]
                if not cells:
                    continue
                name = cells[0]
                d = " ".join(cells[1:3])[:46]
                m = CODE_B.match(name) or CODE_C.match(name)
                if m:
                    abbr = m.group(1).upper()
                    hits[abbr].add(name.split('_')[0])
                    XLSX_ONLY.add(abbr)
                    if d:
                        desc[abbr][d] += 1
        wb.close()
    return hits, desc, len(paths)


def main():
    h1, d1, n1 = scan_csv()
    h2, d2, n2 = scan_xlsx()
    hits = collections.defaultdict(set)
    desc = collections.defaultdict(collections.Counter)
    for src in (h1, h2):
        for k, v in src.items():
            hits[k] |= v
    for src in (d1, d2):
        for k, v in src.items():
            desc[k].update(v)

    print("훑은 파일: CSV %d · XLSX %d" % (n1, n2))
    print("약어 %d종 · 설비코드 %d개" % (len(hits), sum(len(v) for v in hits.values())))
    print()
    byfam = collections.defaultdict(lambda: [0, []])
    unmapped = []
    for abbr, codes in hits.items():
        e, ko = classify(abbr)
        if e:
            byfam[(e, ko)][0] += len(codes)
            byfam[(e, ko)][1].append("%s(%d)" % (abbr, len(codes)))
        else:
            unmapped.append((len(codes), abbr, desc[abbr].most_common(1)))
    print("■ 계열에 붙은 것")
    for (e, ko), (n, abbrs) in sorted(byfam.items(), key=lambda x: -x[1][0]):
        print("  %-4s %-22s %4d대  %s" % (e, ko, n, " ".join(sorted(abbrs))[:70]))
    print()
    print("■ 어느 계열에도 안 붙은 것 — %d종" % len(unmapped))
    for n, abbr, sample in sorted(unmapped, reverse=True)[:40]:
        s = sample[0][0] if sample else ""
        tag = " [xlsx 첫칸 — 설비코드가 아닐 수 있다]" if abbr in XLSX_ONLY else ""
        print("  %-10s %4d대  %s%s" % (abbr, n, s, tag))


if __name__ == "__main__":
    sys.exit(main())
