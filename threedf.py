#!/usr/bin/env python3
"""3DF reference tool: pack, unpack and validate .3df files (spec v0.1).

  python threedf.py pack <folder> <out.3df>
  python threedf.py unpack <file.3df> <folder>
  python threedf.py validate <file.3df | folder>
"""
import json
import sys
import zipfile
from pathlib import Path

MIMETYPE = "application/vnd.3df+zip"
SPEC_VERSION = "0.1"
ELEMENT_TYPES = {"text", "image", "model"}
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
MODEL_EXT = {".glb"}


class ThreeDFError(Exception):
    pass


def _safe_path(p):
    return isinstance(p, str) and p and not p.startswith(("/", "\\")) and ".." not in p.replace("\\", "/").split("/")


def _validate(doc, has_file):
    errs = []
    if not isinstance(doc, dict):
        return ["document.json must contain a JSON object"]
    _has = has_file
    has_file = lambda p: _safe_path(p) and _has(p)
    if doc.get("3df") != SPEC_VERSION:
        errs.append(f'"3df" must be "{SPEC_VERSION}"')
    page = doc.get("page") if isinstance(doc.get("page"), dict) else {}
    for k in ("width_mm", "height_mm"):
        if not isinstance(page.get(k), (int, float)) or page[k] <= 0:
            errs.append(f"page.{k} must be a positive number")
    pages = doc.get("pages")
    if not isinstance(pages, list) or not pages:
        errs.append('"pages" must be a non-empty list')
        return errs
    for pi, p in enumerate(pages, 1):
        if not isinstance(p, dict) or not isinstance(p.get("elements", []), list):
            errs.append(f"page {pi}: must be an object with an 'elements' list")
            continue
        for ei, el in enumerate(p.get("elements", []), 1):
            if not isinstance(el, dict):
                errs.append(f"page {pi}, element {ei}: must be an object")
                continue
            where = f"page {pi}, element {ei}"
            t = el.get("type")
            if t not in ELEMENT_TYPES:
                errs.append(f"{where}: unknown type {t!r}")
                continue
            for k in ("x", "y", "w", "h"):
                if not isinstance(el.get(k), (int, float)) or isinstance(el.get(k), bool):
                    errs.append(f"{where}: {k} (mm) is required")
            if isinstance(el.get("w"), (int, float)) and isinstance(el.get("h"), (int, float)) and (el["w"] <= 0 or el["h"] <= 0):
                errs.append(f"{where}: w and h must be positive")
            if t == "text" and not isinstance(el.get("text"), str):
                errs.append(f"{where}: text element needs a string 'text'")
            if t in ("image", "model"):
                src = el.get("src", "")
                ext = Path(str(src)).suffix.lower()
                allowed = IMAGE_EXT if t == "image" else MODEL_EXT
                if ext not in allowed:
                    errs.append(f"{where}: src {src!r} must be one of {sorted(allowed)}")
                elif not has_file(src):
                    errs.append(f"{where}: missing asset {src}")
                if not el.get("alt"):
                    errs.append(f"{where}: 'alt' text is required for {t}")
            needs_fallback = t == "model" or (t == "image" and Path(str(el.get("src", ""))).suffix.lower() == ".gif")
            if needs_fallback:
                fb = el.get("fallback")
                if not fb:
                    errs.append(f"{where}: animated/3D element needs a static 'fallback' image")
                elif Path(str(fb)).suffix.lower() not in {".png", ".jpg", ".jpeg"}:
                    errs.append(f"{where}: fallback must be PNG or JPEG")
                elif not has_file(fb):
                    errs.append(f"{where}: missing fallback {fb}")
    return errs


def _load_json(read):
    try:
        return json.loads(read()), None
    except (KeyError, FileNotFoundError):
        return None, ["document.json is missing"]
    except (ValueError, UnicodeDecodeError) as e:
        return None, [f"document.json is not valid JSON: {e}"]


def validate(path):
    path = Path(path)
    if not path.exists():
        return [f"{path} does not exist"]
    if path.is_dir():
        doc, err = _load_json(lambda: (path / "document.json").read_text(encoding="utf-8"))
        return err or _validate(doc, lambda p: (path / p).is_file())
    if not zipfile.is_zipfile(path):
        return [f"{path} is not a ZIP container"]
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        if not names or names[0] != "mimetype" or z.read("mimetype").decode() != MIMETYPE:
            return [f'first entry must be an uncompressed "mimetype" file containing {MIMETYPE}']
        if z.getinfo("mimetype").compress_type != zipfile.ZIP_STORED:
            return ['"mimetype" must be stored uncompressed']
        doc, err = _load_json(lambda: z.read("document.json"))
        return err or _validate(doc, lambda p: p in names)


def pack(folder, out):
    folder, out = Path(folder), Path(out)
    if not folder.is_dir():
        raise ThreeDFError(f"{folder} is not a folder")
    errs = validate(folder)
    if errs:
        raise ThreeDFError("\n".join(errs))
    with zipfile.ZipFile(out, "w") as z:
        z.writestr(zipfile.ZipInfo("mimetype"), MIMETYPE, compress_type=zipfile.ZIP_STORED)
        for f in sorted(folder.rglob("*")):
            rel_parts = f.relative_to(folder).parts
            if (f.is_file() and f.name != "mimetype" and f.resolve() != out.resolve()
                    and not any(part.startswith(".") for part in rel_parts)):
                rel = f.relative_to(folder).as_posix()
                # GLB/GIF are already compact; deflate the rest
                ctype = zipfile.ZIP_STORED if f.suffix.lower() in {".gif", ".png", ".jpg", ".jpeg", ".webp"} else zipfile.ZIP_DEFLATED
                z.write(f, rel, compress_type=ctype)
    return out


def unpack(file, folder):
    with zipfile.ZipFile(file) as z:
        for name in z.namelist():
            if not _safe_path(name):
                raise ThreeDFError(f"refusing to extract unsafe path {name!r}")
        z.extractall(folder)


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 2
    cmd = argv[1]
    try:
        if cmd == "pack" and len(argv) == 4:
            pack(argv[2], argv[3])
            print(f"wrote {argv[3]}")
        elif cmd == "unpack" and len(argv) == 4:
            unpack(argv[2], argv[3])
        elif cmd == "validate":
            errs = validate(argv[2])
            print("valid" if not errs else "\n".join(errs))
            return 1 if errs else 0
        else:
            print(__doc__)
            return 2
    except ThreeDFError as e:
        print(e)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
