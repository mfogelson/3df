# 3DF

3DF (`.3df`) is a fixed-layout document format, like PDF, that also supports animated images and interactive 3D models (glTF). See [SPEC.md](SPEC.md).

## Contents

| File | Purpose |
|---|---|
| `SPEC.md` | Format specification, v0.1 |
| `threedf.py` | Pack, unpack and validate `.3df` files |
| `pptx2_3df.py` | Convert PowerPoint (`.pptx`) decks to `.3df`. For Google Slides, download as `.pptx` first |
| `viewer_template.html` | Browser viewer; `build_viewer.py` embeds a sample document into it |
| `make_sample.py`, `make_test_deck.py` | Generate the sample document and a converter test deck |

## Quick start

```
pip install -r requirements.txt
python make_sample.py                     # builds sample.3df
python threedf.py validate sample.3df
python pptx2_3df.py deck.pptx             # needs LibreOffice installed
python build_viewer.py                    # writes viewer.html with sample.3df embedded
```

Open `viewer.html` in a browser and use **Open .3df** to view any document.

## License

MIT. See [LICENSE](LICENSE). The specification in `SPEC.md` is covered by the same license, so anyone may implement readers and writers for 3DF.
