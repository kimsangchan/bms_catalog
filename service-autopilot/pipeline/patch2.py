import re

with open('datasets.py', 'r', encoding='utf-8') as f:
    text = f.read()

# Replace capacity_cooling array start
text = re.sub(
    r'("capacity_cooling": \[)',
    r'\g<1>\n        r"냉방\\s*능력", r"Cooling\\s+Capacity",',
    text
)

# Replace heatingCapacity array start
text = re.sub(
    r'("heatingCapacity": \[)',
    r'\g<1>r"난방\\s*능력", r"Heating\\s+Capacity",\n                        ',
    text
)

with open('datasets.py', 'w', encoding='utf-8') as f:
    f.write(text)
print('Done!')
