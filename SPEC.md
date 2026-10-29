# 3DF (3D Document Format), version 0.1

3DF (`.3df`) is a paginated, fixed-layout document format like PDF, with two additions: animated images (GIF, animated WebP) and interactive 3D models (glTF binary) that the reader can orbit, pan and zoom.

## Container

A `.3df` file is a ZIP archive.

1. The first entry is named `mimetype`, stored uncompressed, containing exactly `application/vnd.3df+zip`. This lets tools identify the file from its first bytes, the same approach EPUB and ODF use.
2. `document.json` at the root describes the document.
3. Assets live anywhere else in the archive, conventionally under `assets/`. Paths in `document.json` are relative to the archive root and use forward slashes.

## document.json

```json
{
  "3df": "0.1",
  "title": "string",
  "author": "string",
  "page": { "width_mm": 210, "height_mm": 297 },
  "pages": [ { "elements": [ ... ] } ]
}
```

All pages share one size in v0.1. Lengths are millimetres; the origin is the page's top-left corner, y grows downward. Font sizes are points (1 pt = 25.4/72 mm).

### Common element fields

| Field | Required | Meaning |
|---|---|---|
| `type` | yes | `text`, `image` or `model` |
| `x`, `y`, `w`, `h` | yes | Box position and size in mm |
| `z` | no | Stacking order, default 0 |

### text

`text` (string, required), `font_size_pt` (default 11), `font_family`, `weight` (100–900), `color` (CSS hex), `align` (`left`, `center`, `right`, `justify`). Text wraps inside its box and is clipped at the box edge.

### image

`src` (PNG, JPEG, GIF or WebP), `alt` (required). Animated GIF/WebP play in a loop as authored. Animated images require `fallback`: a static PNG or JPEG used for printing and by readers without animation.

### model

| Field | Required | Meaning |
|---|---|---|
| `src` | yes | glTF 2.0 binary (`.glb`), metres as the unit |
| `alt` | yes | Text description |
| `fallback` | yes | Static PNG/JPEG for printing and non-3D readers |
| `camera` | no | `{ "yaw_deg", "pitch_deg", "distance" }` orbiting the model's bounding-box centre |
| `auto_rotate` | no | Spin slowly until the reader interacts; readers must honour reduced-motion settings |
| `background` | no | Viewport colour, CSS hex |

Readers provide orbit (drag), zoom (scroll/pinch), pan (right-drag or two-finger drag) and a reset gesture (double-click).

## Reader behaviour

A conforming reader must render text and static images, must show `fallback` for any element it cannot render live, and must use `fallback` when printing or exporting to PDF. Readers should limit live 3D viewports to those near the visible area, since browsers cap active WebGL contexts at around 16.

## Security

3DF has no scripting, forms or external references. Readers must not load any resource outside the archive. glTF files must be self-contained (no external `uri` buffers or images).

## Versioning

Readers reject a `3df` major version they don't know and should attempt minor versions above their own, ignoring unknown fields.
