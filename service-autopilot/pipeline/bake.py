# -*- coding: utf-8 -*-
"""산출물을 **순서대로** 굽는다 — 무엇을 먼저 돌려야 하는지 기억할 필요를 없앤다.

  PYTHONIOENCODING=utf-8 python bake.py          전부 (느린 것 포함)
  PYTHONIOENCODING=utf-8 python bake.py --fast   쪽 그림 굽는 취입 검사대만 건너뛴다
  PYTHONIOENCODING=utf-8 python bake.py --list   순서만 보여 준다

왜 있나
  굽는 것들이 **사슬로 묶여 있는데** 그 순서가 사람 머리에만 있었다.

      data/models/*.json ·  equip-templates.json ·  equip-requirements.json ·  point-concepts.json
                                    │
                                    ▼   datasets.py
                        data/datasets/*.json  (model-mappings 등)
                                    │
            ┌───────────────────────┼───────────────────────┐
            ▼                       ▼                       ▼
      template_map.py          schema_map.py           build.py *
      template-map.html        data-map.html           equip-catalog.html
      (* build.py 는 datasets 를 라이브로 다시 계산하지만 같은 입력을 본다)

  가운데(datasets.py)를 빼먹으면 화면이 **조용히 옛 결과**를 보여 준다. 실제로 그랬다 —
  매칭을 하루 종일 고치고 화면을 다시 구웠는데, model-mappings.json 이 사흘 전 것이라
  모델별 덮개가 하나도 안 바뀌었다. 화면은 멀쩡히 열리고 숫자도 그럴듯해서 아무도 몰랐다.
  그 뒤로 셋을 걸었다: 이 파일(순서) · validate.py 의 review-stale(전 도구 공통 게이트) ·
  template_map.py 의 문지기(낡은 입력이면 굽기를 거부).

  ⚠ 취입 검사대(verify_points.py)는 쪽 그림을 담아 느리고 산출물이 gitignore 된다.
    --fast 로 건너뛸 수 있지만, **원문 대조를 할 참이면 빼지 마라.**
"""
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))

# (스크립트, 인자, 한 줄 설명, 느린가)
STEPS = [
    ("datasets.py", [], "모델·템플릿 매칭을 다시 계산해 data/datasets/*.json 로", False),
    ("build.py", [], "전체 카탈로그 → review/equip-catalog.html", False),
    ("template_map.py", [], "템플릿 검사대 → review/template-map.html", False),
    ("schema_map.py", [], "데이터 지도 → review/data-map.html", False),
    ("verify_points.py", [], "취입 검사대 → review/point-verify.html (쪽 그림·느리다)", True),
    ("review_index.py", ["--run"], "review/ 길잡이 .md 갱신", False),
]


def main(argv):
    fast = "--fast" in argv
    if "--list" in argv:
        for i, (name, args, what, slow) in enumerate(STEPS, 1):
            print("%d. %-18s %s%s" % (i, name, what, "  [--fast 면 건너뜀]" if slow else ""))
        return 0

    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    for i, (name, args, what, slow) in enumerate(STEPS, 1):
        if fast and slow:
            print("%d/%d  %-18s 건너뜀 (--fast)" % (i, len(STEPS), name))
            continue
        print("%d/%d  %-18s %s" % (i, len(STEPS), name, what))
        t0 = time.time()
        r = subprocess.run([sys.executable, os.path.join(HERE, name)] + args,
                           cwd=HERE, env=env)
        if r.returncode:
            # ⚠ 멈춘다. 앞 단계가 실패했는데 뒤를 구우면 **반쯤 낡은 산출물**이 남고,
            #   그게 가장 알아채기 어려운 상태다.
            print("\n중단 — %s 가 실패했다(코드 %d). 고치고 다시 돌려라." % (name, r.returncode))
            return r.returncode
        print("      (%.0f초)" % (time.time() - t0))
    print("\n다 구웠다. 확인:  PYTHONIOENCODING=utf-8 python validate.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
