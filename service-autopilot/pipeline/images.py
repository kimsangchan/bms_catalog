# -*- coding: utf-8 -*-
"""제품 사진 추출 — 카탈로그·데이터시트에서 모델 사진을 뽑아 카탈로그에 붙인다.

글자만 있는 표는 어느 장비인지 감이 안 온다. 카탈로그에 실린 제품 사진을 함께
보여 주면 고를 때 훨씬 빠르다.

고르는 규칙 (지어내지 않는다)
  · 앞쪽 몇 장에서만 찾는다 — 제품 사진은 표지·첫 절에 있다
  · 로고·아이콘은 뺀다 (가로세로 어느 쪽이든 너무 작거나 띠 모양인 것)
  · **앞쪽 페이지를 먼저** 본다 — 뒤쪽 큰 그림은 치수 도면인 경우가 많다
  · 같은 페이지 안에서는 큰 것을 고른다
  · 출처(문서·쪽·xref)를 함께 남긴다 — 어디서 왔는지 확인할 수 있어야 한다

HTML 은 폐쇄망에 파일 하나로 돌리므로 사진도 **줄여서 파일 안에** 넣는다
(가로 320px JPEG). 원본은 보관하지 않는다.

실행
  python images.py <pdf>                    후보를 본다
  python images.py --attach <모델> <pdf>      모델에 붙인다
  python images.py --auto                   연결표(spec-map)대로 한꺼번에
"""
import base64
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
RAW = os.path.join(DATA, "raw")

MAX_W = 320          # 화면에 쓰는 가로 크기
MIN_SIDE = 220       # 이보다 작으면 아이콘으로 본다
MAX_RATIO = 2.6      # 가로:세로가 이보다 치우치면 띠·머리글 그림이다


def candidates(pdf, pages=4):
    """앞쪽 몇 장의 그림 중 제품 사진일 만한 것 → 큰 순서"""
    import fitz
    doc = fitz.open(pdf)
    out = []
    for pi in range(min(pages, doc.page_count)):
        for x in doc[pi].get_images(full=True):
            xref = x[0]
            try:
                info = doc.extract_image(xref)
            except Exception:
                continue
            w, h = info["width"], info["height"]
            if min(w, h) < MIN_SIDE:
                continue
            if max(w, h) / max(1, min(w, h)) > MAX_RATIO:
                continue
            out.append({"page": pi + 1, "xref": xref, "w": w, "h": h,
                        "ext": info["ext"], "bytes": len(info["image"])})
    # 쪽이 먼저, 그 안에서 크기 — 크기만 보면 뒤쪽 치수 도면이 뽑힌다
    out.sort(key=lambda d: (d["page"], -(d["w"] * d["h"])))
    return out


def thumbnail(pdf, xref, max_w=MAX_W):
    """그림 하나를 줄여서 JPEG data URI 로. 파일 하나로 배포하려면 안에 넣어야 한다."""
    import fitz
    doc = fitz.open(pdf)
    pix = fitz.Pixmap(doc, xref)
    if pix.alpha:                       # 투명 배경은 흰색으로 깔아준다
        pix = fitz.Pixmap(fitz.csRGB, pix)
    elif pix.colorspace and pix.colorspace.n == 4:   # CMYK → RGB
        pix = fitz.Pixmap(fitz.csRGB, pix)
    if pix.width > max_w:
        scale = max_w / pix.width
        mat = fitz.Matrix(scale, scale)
        pix = fitz.Pixmap(doc, xref)
        if pix.alpha or (pix.colorspace and pix.colorspace.n == 4):
            pix = fitz.Pixmap(fitz.csRGB, pix)
        # Pixmap 은 직접 리샘플이 안 되므로 PIL 이 있으면 쓰고, 없으면 원본을 쓴다
        try:
            from PIL import Image
            im = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
            im.thumbnail((max_w, max_w * 3))
            buf = io.BytesIO()
            im.save(buf, "JPEG", quality=78, optimize=True)
            return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
        except ImportError:
            pass
    data = pix.tobytes("jpeg") if hasattr(pix, "tobytes") else pix.getPNGData()
    return "data:image/jpeg;base64," + base64.b64encode(data).decode()


def attach(mid, fname, pick=0):
    path = os.path.join(DATA, "models", mid + ".json")
    m = json.load(open(path, encoding="utf-8"))
    cs = candidates(os.path.join(RAW, fname))
    if not cs:
        return None
    c = cs[min(pick, len(cs) - 1)]
    uri = thumbnail(os.path.join(RAW, fname), c["xref"])
    m["photo"] = uri
    m["photoSource"] = "%s p%d" % (fname, c["page"])
    json.dump(m, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return c, len(uri)


def main(argv):
    if "--auto" in argv:
        mp = json.load(open(os.path.join(DATA, "spec-map.json"), encoding="utf-8"))
        done = 0
        for fname, mids in mp.items():
            if fname.startswith("_") or not os.path.exists(os.path.join(RAW, fname)):
                continue
            cs = candidates(os.path.join(RAW, fname))
            if not cs:
                print("  · %-46s 사진 없음" % fname[:46])
                continue
            try:
                uri = thumbnail(os.path.join(RAW, fname), cs[0]["xref"])
            except Exception as e:
                print("  ⚠ %-46s %s" % (fname[:46], str(e)[:40]))
                continue
            for mid in mids:
                p = os.path.join(DATA, "models", mid + ".json")
                if not os.path.exists(p):
                    continue
                m = json.load(open(p, encoding="utf-8"))
                if m.get("photo"):        # 이미 붙은 것은 그대로 둔다
                    continue
                m["photo"] = uri
                m["photoSource"] = "%s p%d" % (fname, cs[0]["page"])
                json.dump(m, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
                done += 1
            print("%-46s %4dx%-4d → 모델 %d건 · %.0f KB"
                  % (fname[:46], cs[0]["w"], cs[0]["h"], len(mids), len(uri) / 1024))
        print("\n사진 적용 %d건" % done)
        return 0

    if "--variants" in argv:
        # 형번별 사진 — 데이터시트 한 장이 형번 하나이므로 형번마다 실물이 다르다.
        import glob as _g
        n = 0
        for f in sorted(_g.glob(os.path.join(DATA, "models", "*.json"))):
            m = json.load(open(f, encoding="utf-8"))
            vs = m.get("variants") or []
            if not vs:
                continue
            ch = False
            for v in vs:
                if v.get("photo") or not v.get("source"):
                    continue
                src = os.path.join(RAW, v["source"])
                if not os.path.exists(src):
                    continue
                cs = candidates(src)
                if not cs:
                    continue
                try:
                    v["photo"] = thumbnail(src, cs[0]["xref"])
                    v["photoPage"] = cs[0]["page"]
                    ch = True
                    n += 1
                except Exception:
                    continue
            if ch:
                json.dump(m, open(f, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
                print("%-40s 형번 사진 %d/%d"
                      % (m["id"][:40], sum(1 for v in vs if v.get("photo")), len(vs)))
        print("\n형번 사진 %d건" % n)
        return 0

    if "--attach" in argv:
        i = argv.index("--attach")
        pick = int(argv[i + 3]) if len(argv) > i + 3 and argv[i + 3].isdigit() else 0
        r = attach(argv[i + 1], argv[i + 2], pick)
        print("%s ← %s" % (argv[i + 1], r[0] if r else "사진 없음"))
        return 0

    pdf = argv[0]
    for c in candidates(pdf)[:8]:
        print("  p%-3d xref=%-5d %4dx%-4d %-5s %8d B" %
              (c["page"], c["xref"], c["w"], c["h"], c["ext"], c["bytes"]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
