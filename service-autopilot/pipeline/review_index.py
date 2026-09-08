# -*- coding: utf-8 -*-
"""review/ 폴더에 길잡이 문서를 깐다 — 탐색기에서 바로 알아보게.

  PYTHONIOENCODING=utf-8 python review_index.py          바뀔 것만 보여 준다
  PYTHONIOENCODING=utf-8 python review_index.py --run    실제로 쓴다

왜 필요한가
  review/ 에 HTML 이 열 개가 됐다. 이름만 보면 무엇인지, 누가 굽는지, 지금도 쓰는지
  알 수 없다. 그래서 **같은 이름의 `.md` 를 옆에 둔다** — 탐색기가 이름순으로 정렬하니
  `equip-catalog.html` 바로 밑에 `equip-catalog.md` 가 붙는다.

  낡은 것은 지우지 않고 `_archive/` 로 옮긴다. 지우면 왜 있었는지가 함께 사라진다.

⚠ 옮길 때 gitignore 를 같이 손봐야 한다
  원래 무시되던 HTML 을 `_archive/` 로 옮기면 **경로가 바뀌어 무시가 풀린다** —
  실제로 30 MB 가 스테이징에 딸려 들어왔다. `.gitignore` 에
  `service-autopilot/review/_archive/*.html` 을 두어 막았고, 굽는 스크립트가 없어
  되살릴 수 없는 `implementation_plan.html` 하나만 예외로 담는다.
"""
import io
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REVIEW = os.path.normpath(os.path.join(HERE, "..", "review"))
ARCHIVE = os.path.join(REVIEW, "_archive")

# (파일, 한 줄 소개, 굽는 명령, 무엇을 보나, 언제 다시 굽나)
CURRENT = [
    ("template-map.html", "BMS 기본화면 템플릿 검사대",
     "python template_map.py",
     ["계열별 템플릿 행 — 개념·종류·단위·등급·왜 필요한가·Haystack 근거·매칭 정규식",
      "**모델·판을 고르면** 각 행에 실제로 붙은 포인트 이름이 채워진다",
      "모델 × 행 덮개 격자 — 아무 모델도 안 내주는 행을 찾는다"],
     "템플릿 행을 고치거나 모델을 새로 취입한 뒤"),
    ("equip-catalog.html", "전체 카탈로그 — 이 저장소의 대표 산출물",
     "python build.py",
     ["설비 계열 → 모델 → 오브젝트·정격을 한 화면에서 훑는다",
      "모델별 BMS 기본화면·형번 확정본·시뮬레이터 입력"],
     "모델 JSON 이 바뀐 뒤 (validate.py 가 낡았다고 경고한다)"),
    ("point-verify.html", "취입 검사대 — 원문 쪽 그림과 나란히 본다",
     "python verify_points.py",
     ["국내 벤더 판별 포인트 전수 + 정격 표",
      "각 행의 출처(파일·쪽)와 **원문 쪽 그림**이 함께 뜬다 — 눈으로 대조하는 자리",
      "CSV 내보내기"],
     "새 벤더를 취입한 뒤. 무겁다(30 MB 안팎·쪽 그림 수백 장)"),
    ("data-map.html", "데이터 지도 — 원문이 어떤 층을 거쳐 BMS·시뮬레이터 모양이 되나",
     "python schema_map.py",
     ["6개 층과 6개 조인 키(modelId·equipId·interfaceId·형번·feature·templateName)",
      "point-schema·unit-schema 를 실시간으로 읽어 표로 보여 준다",
      "LS H100 하나를 층마다 따라가는 표본"],
     "스키마(point-schema·unit-schema)를 고친 뒤"),
    ("jci-ingest.html", "JCI 문서 취입 검사대",
     "python ingest_jci.py --export",
     ["JCI 포털 문서에서 뽑은 판·포인트를 원문 쪽 그림과 대조",
      "`--no-pages` 로 그림 없이 가볍게 굽을 수 있다"],
     "JCI 문서를 다시 취입한 뒤. 아주 무겁다(60 MB 안팎)"),
]

# (파일, 왜 물러났나 — 사실만 적는다)
RETIRED = [
    ("spec-verify.html",
     "2026-08-11 산출. `verify.py` 가 굽는 전 모델 정격 검사대다. "
     "⚠ **완전히 대체되지 않았다** — `point-verify.html` 의 정격 절은 국내 벤더와 "
     "FOCUS_MODELS 만 덮는다. 전 모델 정격을 한 번에 훑어야 하면 `verify.py` 를 "
     "다시 돌려라. 옮긴 이유는 넉 달 가까이 안 굽혀 데이터보다 낡았기 때문이다."),
    ("req-verify-e5.rtu.html",
     "2026-08-11 산출. 요구 프로파일 **하나**(e5.rtu)의 충족도 화면이다. "
     "지금은 `template-map.html` 이 프로파일 8개 전부를 같은 조인으로 보여 준다."),
    ("jci-points.html",
     "2026-08-12 산출. `vendor_jci_sceq.py` 의 SC-EQ 포인트 화면이다. "
     "`jci-ingest.html` 이 같은 문서군을 원문 쪽 그림까지 붙여 보여 준다. "
     "⚠ 현장 우선순위상 **냉동기는 멈춤**(6순위)이라 다시 굽을 일이 당분간 없다."),
    ("lg-bacnet-verify.html",
     "2026-09-04 산출. LG AC Smart BACnet 전용 검사대(`verify_lg.py`). "
     "그 뒤 `point-verify.html` 이 LG 를 포함한 국내 벤더를 다 덮게 됐고, "
     "LG 는 Modbus-TCP 판 3개가 더 붙어 이 화면은 165점 시절에 멈춰 있다."),
    ("implementation_plan.html",
     "2026-09-03 파일이지만 **굽는 스크립트가 없다** — 손으로 만든 옛 기획 산출물이다. "
     "지금 계획은 `NEXT.md` 와 `WORKLOG.md` 가 들고 있다."),
]

HEAD = ("<!-- review_index.py 가 만든다. 직접 고치지 마라 -->\n"
        "# %s\n\n%s\n\n")


def sidecar(name, one, cmd, sees, when, size):
    b = ["<!-- review_index.py 가 만든다. 직접 고치지 마라 -->",
         "# %s" % name, "",
         "**%s**" % one, "",
         "| | |", "|---|---|",
         "| 굽는 법 | `cd service-autopilot/pipeline && PYTHONIOENCODING=utf-8 %s` |" % cmd,
         "| 다시 굽는 때 | %s |" % when,
         "| 크기 | %s |" % size,
         "| 여는 법 | 더블클릭 (오프라인 단일 파일 · 인터넷 없이 열린다) |",
         "", "## 무엇을 보나", ""]
    b += ["- %s" % s for s in sees]
    b += ["", "---", "",
          "폴더 전체 안내는 [`_INDEX.md`](_INDEX.md) 에 있다.", ""]
    return "\n".join(b)


def human(path):
    try:
        n = os.path.getsize(path)
    except OSError:
        return "—"
    for u in ("B", "KB", "MB"):
        if n < 1024 or u == "MB":
            return "%.0f %s" % (n, u) if u != "MB" else "%.1f MB" % n
        n /= 1024.0
    return "%.1f MB" % n


def index(sizes, moved):
    b = ["<!-- review_index.py 가 만든다. 직접 고치지 마라 -->",
         "# review/ — 무엇이 무엇인가", "",
         "여기 있는 HTML 은 **오프라인 단일 파일**이다. 더블클릭하면 인터넷 없이 열린다.",
         "파일마다 같은 이름의 `.md` 가 옆에 있으니 탐색기에서 바로 확인하면 된다.", "",
         "## 지금 쓰는 것", "",
         "| 화면 | 무엇 | 굽는 법 | 크기 |", "|---|---|---|---|"]
    for name, one, cmd, _s, _w in CURRENT:
        b.append("| [`%s`](%s) | %s | `%s` | %s |"
                 % (name, name, one, cmd, sizes.get(name, "—")))
    b += ["", "## 물러난 것 — `_archive/`", "",
          "지우지 않았다. **지우면 왜 있었는지가 함께 사라진다.** "
          "사유는 각 파일 옆 `.md` 에 적혀 있다.", "",
          "| 화면 | 왜 물러났나 |", "|---|---|"]
    for name, why in RETIRED:
        # 첫 문장만 자르면 '2026-08-11 산출.' 만 남아 아무 정보가 없다 — 두 문장 쓴다
        parts = [x for x in why.split(". ") if x]
        short = ". ".join(parts[:2]).rstrip(".") + "."
        b.append("| `_archive/%s` | %s |" % (name, short))
    b += ["", "## 굽는 순서 (전부 다시 만들 때)", "",
          "```bash", "cd service-autopilot/pipeline",
          "PYTHONIOENCODING=utf-8 python validate.py      # 먼저 오류 0 확인",
          "PYTHONIOENCODING=utf-8 python datasets.py      # 데이터셋 먼저",
          "PYTHONIOENCODING=utf-8 python build.py",
          "PYTHONIOENCODING=utf-8 python template_map.py",
          "PYTHONIOENCODING=utf-8 python schema_map.py",
          "PYTHONIOENCODING=utf-8 python verify_points.py # 무겁다(수 분)",
          "```", ""]
    if moved:
        b += ["> 이번에 옮긴 것: %s" % ", ".join(moved), ""]
    return "\n".join(b)


def main(argv):
    run = "--run" in argv
    plan = []
    sizes = {}
    for name, one, cmd, sees, when in CURRENT:
        p = os.path.join(REVIEW, name)
        sizes[name] = human(p)
        if not os.path.exists(p):
            print("  ⚠ 없다(아직 안 구웠다): %s" % name)
        plan.append((os.path.join(REVIEW, name[:-5] + ".md"),
                     sidecar(name, one, cmd, sees, when, sizes[name])))

    moved = []
    for name, why in RETIRED:
        src = os.path.join(REVIEW, name)
        dst = os.path.join(ARCHIVE, name)
        if os.path.exists(src):
            moved.append(name)
            if run:
                if not os.path.isdir(ARCHIVE):
                    os.makedirs(ARCHIVE)
                tracked = subprocess.call(
                    ["git", "ls-files", "--error-unmatch", src],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0
                if tracked:
                    subprocess.check_call(["git", "mv", src, dst])
                else:
                    os.replace(src, dst)
        tgt = dst if (run or os.path.exists(dst)) else src
        plan.append((os.path.join(ARCHIVE, name[:-5] + ".md"),
                     "\n".join(["<!-- review_index.py 가 만든다. 직접 고치지 마라 -->",
                                "# %s — 물러남" % name, "",
                                why, "",
                                "| | |", "|---|---|",
                                "| 크기 | %s |" % human(tgt),
                                "| 지웠나 | **아니다.** 옮기기만 했다 |", "",
                                "폴더 전체 안내는 [`../_INDEX.md`](../_INDEX.md).", ""])))

    plan.append((os.path.join(REVIEW, "_INDEX.md"), index(sizes, moved)))

    print("길잡이 %d개 · 옮길 것 %d개" % (len(plan), len(moved)))
    for p, _t in plan:
        print("   %s" % os.path.relpath(p, REVIEW))
    if not run:
        print("(미리보기다. 실제로 쓰려면 --run)")
        return 0
    for p, text in plan:
        d = os.path.dirname(p)
        if not os.path.isdir(d):
            os.makedirs(d)
        with io.open(p, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
    print("→ %s" % os.path.relpath(REVIEW, HERE))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
