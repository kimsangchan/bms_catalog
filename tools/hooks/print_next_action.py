#!/usr/bin/env python3
"""SessionStart 훅: NEXT.md 의 '현재-작업' 마커 블록만 새 세션 컨텍스트에 주입한다.

단일 출처 = NEXT.md (이 스크립트는 읽어서 출력만 한다 → 드리프트 없음).
.claude/settings.json 의 SessionStart 훅에서 호출한다. 표준출력이 세션 컨텍스트로 들어간다.
NEXT.md 나 마커가 없으면 조용히 아무것도 출력하지 않는다(exit 0, 안전한 no-op).

NEXT.md 경로 탐색(먼저 찾히는 것 사용):
  1) $CATCHUP_NEXT_PATH (명시 지정)
  2) <프로젝트>/NEXT.md
  3) <프로젝트>/coordination/NEXT.md
"""
import os
import sys

# Windows 기본 stdout 은 cp949 라 한글/em-dash 등에서 UnicodeEncodeError. UTF-8 고정.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

START = "<!-- NEXT-ACTION:START -->"
END = "<!-- NEXT-ACTION:END -->"


def _candidates(root):
    env = os.environ.get("CATCHUP_NEXT_PATH")
    if env:
        yield env
    yield os.path.join(root, "NEXT.md")
    yield os.path.join(root, "coordination", "NEXT.md")


def main() -> int:
    root = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    text = None
    for path in _candidates(root):
        try:
            with open(path, encoding="utf-8") as f:
                text = f.read()
            break
        except OSError:
            continue
    if text is None or START not in text or END not in text:
        return 0  # NEXT.md 없거나 마커 없으면 조용히 통과
    block = text.split(START, 1)[1].split(END, 1)[0].strip()
    if block:
        print("[NEXT] 현재 다음-작업 (SessionStart 자동 주입):\n")
        print(block)
    return 0


if __name__ == "__main__":
    sys.exit(main())
