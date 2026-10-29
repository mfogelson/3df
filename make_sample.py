#!/usr/bin/env python3
"""Builds sample/ (an unpacked 3DF) and sample.3df: an animated GIF, a GLB truss, fallbacks."""
import json
import math
import struct
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

import threedf

OUT = Path(__file__).parent / "sample"
(OUT / "assets").mkdir(parents=True, exist_ok=True)


# ---------- 3D model: a 4-bay square truss, written as a GLB ----------
def truss_segments(bays=4, L=1.0, s=0.15):
    corners = [(-s, -s), (s, -s), (s, s), (-s, s)]
    nodes = lambda i: [np.array([i * L - bays * L / 2, y, z]) for y, z in corners]
    segs = []
    for i in range(bays + 1):
        n = nodes(i)
        segs += [(n[k], n[(k + 1) % 4]) for k in range(4)]          # battens
        if i < bays:
            m = nodes(i + 1)
            segs += [(n[k], m[k]) for k in range(4)]                  # longerons
            segs += [(n[k], m[(k + 1) % 4]) for k in range(4)]        # diagonals
    return segs


def box_along(a, b, r):
    d = b - a
    length = np.linalg.norm(d)
    u = d / length
    tmp = np.array([0, 0, 1.0]) if abs(u[2]) < 0.9 else np.array([1.0, 0, 0])
    v = np.cross(u, tmp); v /= np.linalg.norm(v)
    w = np.cross(u, v)
    pos, nrm, idx = [], [], []
    faces = [(v, w), (-v, w), (w, v), (-w, v)]                       # 4 long sides
    for n, t in faces:
        base = len(pos)
        for along in (0, length):
            for side in (-1, 1):
                pos.append(a + u * along + n * r + t * r * side)
                nrm.append(n)
        idx += [base, base + 2, base + 1, base + 1, base + 2, base + 3]
    return pos, nrm, idx


def write_glb(path, segs, r=0.012):
    P, N, I = [], [], []
    for a, b in segs:
        p, n, i = box_along(a, b, r)
        off = len(P)
        P += p; N += n; I += [off + k for k in i]
    P = np.array(P, np.float32); N = np.array(N, np.float32); I = np.array(I, np.uint32)
    # double-sided material avoids winding issues on the side faces
    bin_ = P.tobytes() + N.tobytes() + I.tobytes()
    gltf = {
        "asset": {"version": "2.0", "generator": "3df make_sample"},
        "scene": 0, "scenes": [{"nodes": [0]}], "nodes": [{"mesh": 0}],
        "meshes": [{"primitives": [{"attributes": {"POSITION": 0, "NORMAL": 1}, "indices": 2, "material": 0}]}],
        "materials": [{"pbrMetallicRoughness": {"baseColorFactor": [0.78, 0.8, 0.84, 1], "metallicFactor": 0.6,
                                                 "roughnessFactor": 0.35}, "doubleSided": True}],
        "buffers": [{"byteLength": len(bin_)}],
        "bufferViews": [
            {"buffer": 0, "byteOffset": 0, "byteLength": P.nbytes, "target": 34962},
            {"buffer": 0, "byteOffset": P.nbytes, "byteLength": N.nbytes, "target": 34962},
            {"buffer": 0, "byteOffset": P.nbytes + N.nbytes, "byteLength": I.nbytes, "target": 34963},
        ],
        "accessors": [
            {"bufferView": 0, "componentType": 5126, "count": len(P), "type": "VEC3",
             "min": P.min(0).tolist(), "max": P.max(0).tolist()},
            {"bufferView": 1, "componentType": 5126, "count": len(N), "type": "VEC3"},
            {"bufferView": 2, "componentType": 5125, "count": len(I), "type": "SCALAR"},
        ],
    }
    j = json.dumps(gltf, separators=(",", ":")).encode()
    j += b" " * (-len(j) % 4)
    bin_ += b"\0" * (-len(bin_) % 4)
    total = 12 + 8 + len(j) + 8 + len(bin_)
    with open(path, "wb") as f:
        f.write(struct.pack("<III", 0x46546C67, 2, total))
        f.write(struct.pack("<II", len(j), 0x4E4F534A)); f.write(j)
        f.write(struct.pack("<II", len(bin_), 0x004E4942)); f.write(bin_)


def iso(p, scale, cx, cy):
    x, y, z = p
    a = math.radians(30)
    return (cx + (x - y) * math.cos(a) * scale, cy - z * scale + (x + y) * math.sin(a) * scale * 0.5)


def model_fallback(path, segs):
    im = Image.new("RGB", (1200, 600), (244, 246, 248))
    d = ImageDraw.Draw(im)
    for a, b in segs:
        d.line([iso(a, 420, 600, 300), iso(b, 420, 600, 300)], fill=(60, 70, 85), width=4)
    im.save(path)


# ---------- animated GIF: accordion solar panels unfolding ----------
def deploy_gif(path, still_path, frames=36, W=600, H=300):
    imgs = []
    for f in range(frames):
        t = min(1.0, f / (frames * 0.7))
        t = 0.5 - 0.5 * math.cos(math.pi * t)                          # ease in/out
        im = Image.new("RGB", (W, H), (20, 28, 48))
        d = ImageDraw.Draw(im)
        panel, n = 90, 5
        fold = math.radians(85 * (1 - t))
        x, y = 40.0, H / 2
        d.rectangle([20, y - 40, 40, y + 40], fill=(180, 186, 196))      # bus
        for k in range(n):
            ang = fold if k % 2 == 0 else -fold
            x2 = x + panel * math.cos(ang); y2 = y - panel * math.sin(ang)
            d.line([(x, y), (x2, y2)], fill=(70, 120, 220), width=10)
            d.ellipse([x - 3, y - 3, x + 3, y + 3], fill=(230, 230, 230))
            x, y = x2, y2
        imgs.append(im.convert("P", palette=Image.ADAPTIVE, colors=32))
        if f == frames - 1:
            im.save(still_path)
    imgs[0].save(path, save_all=True, append_images=imgs[1:], duration=60, loop=0)


segs = truss_segments()
write_glb(OUT / "assets/truss.glb", segs)
model_fallback(OUT / "assets/truss_fallback.png", segs)
deploy_gif(OUT / "assets/deploy.gif", OUT / "assets/deploy_fallback.png")

doc = {
    "3df": "0.1",
    "title": "3DF sample",
    "author": "3DF reference tools",
    "page": {"width_mm": 210, "height_mm": 297},
    "pages": [
        {"elements": [
            {"type": "text", "x": 20, "y": 22, "w": 170, "h": 16, "text": "A document that moves",
             "font_size_pt": 26, "weight": 600},
            {"type": "text", "x": 20, "y": 40, "w": 170, "h": 24,
             "text": "Page 1 holds an animated GIF. Page 2 holds a 3D model you can rotate and zoom. "
                     "Every animated or 3D element carries a static fallback for printing and older readers.",
             "font_size_pt": 11},
            {"type": "image", "x": 20, "y": 72, "w": 170, "h": 85, "src": "assets/deploy.gif",
             "fallback": "assets/deploy_fallback.png", "alt": "Accordion-folded panels unfolding"},
            {"type": "text", "x": 20, "y": 160, "w": 170, "h": 8,
             "text": "Figure 1. Panel deployment sequence (GIF, loops).", "font_size_pt": 9, "color": "#5a6270"},
        ]},
        {"elements": [
            {"type": "text", "x": 20, "y": 22, "w": 170, "h": 12, "text": "Interactive model",
             "font_size_pt": 20, "weight": 600},
            {"type": "text", "x": 20, "y": 36, "w": 170, "h": 12,
             "text": "Drag to orbit, scroll or pinch to zoom, right-drag to pan. Double-click to reset the view.",
             "font_size_pt": 11},
            {"type": "model", "x": 20, "y": 52, "w": 170, "h": 120, "src": "assets/truss.glb",
             "fallback": "assets/truss_fallback.png", "alt": "Four-bay square truss",
             "camera": {"yaw_deg": 35, "pitch_deg": 20, "distance": 4.2}, "auto_rotate": False,
             "background": "#eef1f4"},
            {"type": "text", "x": 20, "y": 175, "w": 170, "h": 8,
             "text": "Figure 2. Four-bay truss (glTF binary, 1 m bays).", "font_size_pt": 9, "color": "#5a6270"},
        ]},
    ],
}
(OUT / "document.json").write_text(json.dumps(doc, indent=2))
threedf.pack(OUT, Path(__file__).parent / "sample.3df")
print("wrote sample.3df")
