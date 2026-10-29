"""Writes viewer.html: viewer_template.html with sample.3df embedded as the start-up document."""
import base64
from pathlib import Path

here = Path(__file__).parent
sample = base64.b64encode((here / "sample.3df").read_bytes()).decode()
html = (here / "viewer_template.html").read_text(encoding="utf-8").replace("__SAMPLE_B64__", sample)
(here / "viewer.html").write_text(html, encoding="utf-8")
print("wrote viewer.html")
