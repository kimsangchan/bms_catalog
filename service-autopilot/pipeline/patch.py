import re

with open('datasets.py', 'r', encoding='utf-8') as f:
    text = f.read()

target = '''    "capacity_cooling": [
        r"Nominal\s+Cooling\s+Capacity",
        r"Cooling\s+Capacity",
        r"^Cooling\\b",
        r"Capacity\s*\(\s*Cooling",
        r"Gross\s+Cooling\s+Capacity",
    ],'''
replacement = '''    "capacity_cooling": [
        r"냉방\s*능력", r"Cooling\s+Capacity",
        r"Nominal\s+Cooling\s+Capacity",
        r"^Cooling\\b",
        r"Capacity\s*\(\s*Cooling",
        r"Gross\s+Cooling\s+Capacity",
    ],'''
if target in text: text = text.replace(target, replacement)
else: print('target 1 not found')

target2 = '''    "heatingCapacity": [r"^Total High Heat Capacity",
                        # JCI Roomtop RTC/RTH 기술 가이드에 'Nominal capacities' 가
                        # (2026-08-21). 라벨에 단위가 붙어 있어(?W) 다른 벤더의
                        # 'Cooling capacity' 류와 겹치지 않으므로 기존 모델 건수
                        # 대조에서 걸러진 라벨 0건을 확인하고 넣었다.
                        r"^Heating capacity \(?W\)?$"],'''
replacement2 = '''    "heatingCapacity": [r"난방\s*능력", r"Heating\s+Capacity",
                        r"^Total High Heat Capacity",
                        # JCI Roomtop RTC/RTH 기술 가이드에 'Nominal capacities' 가
                        # (2026-08-21). 라벨에 단위가 붙어 있어(?W) 다른 벤더의
                        # 'Cooling capacity' 류와 겹치지 않으므로 기존 모델 건수
                        # 대조에서 걸러진 라벨 0건을 확인하고 넣었다.
                        r"^Heating capacity \(?W\)?$"],'''
if target2 in text: text = text.replace(target2, replacement2)
else: print('target 2 not found')

target3 = '''        if not code_cols:
            capacity_units_from_table(table, model, capacity_units)
            continue'''
replacement3 = '''        if not code_cols:
            for col in range(1, len(header)):
                cell = header[col] or ""
                if re.match(r"^(AM|RC|DV)\d+[A-Z0-9]+", cell, re.I):
                    code_cols.append((col, cell))
                elif re.match(r"^(ARUM|ARUN|PRHR|PAHC|LG)\d+[A-Z0-9]+", cell, re.I):
                    code_cols.append((col, cell))
        if not code_cols:
            for col in range(1, len(first)):
                cell = first[col] or ""
                if re.match(r"^(AM|RC|DV|ARUM|ARUN|PRHR|PAHC|LG)\d+[A-Z0-9]+", cell, re.I):
                    code_cols.append((col, cell))
        if not code_cols:
            capacity_units_from_table(table, model, capacity_units)
            continue'''
if target3 in text: text = text.replace(target3, replacement3)
else: print('target 3 not found')

with open('datasets.py', 'w', encoding='utf-8') as f:
    f.write(text)
print('Done!')
