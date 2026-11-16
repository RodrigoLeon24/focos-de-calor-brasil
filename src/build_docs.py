"""
Injeta docs/assets/figures.json no docs/index.html (bloco <script id="fig-data">),
deixando o artigo autocontido: abre via GitHub Pages ou direto do disco (file://).

Uso:
    python -m src.build_docs
"""
import re

from src.etl import ROOT

HTML = ROOT / "docs" / "index.html"
DATA = ROOT / "docs" / "assets" / "figures.json"
PATTERN = re.compile(r'(<script id="fig-data" type="application/json">)(.*?)(</script>)', re.S)


def build() -> None:
    payload = DATA.read_text(encoding="utf-8").replace("</", "<\\/")
    html = HTML.read_text(encoding="utf-8")
    new, n = PATTERN.subn(lambda m: m.group(1) + payload + m.group(3), html)
    if n != 1:
        raise RuntimeError("Bloco <script id='fig-data'> não encontrado em docs/index.html")
    HTML.write_text(new, encoding="utf-8")
    print(f"docs/index.html atualizado ({len(payload) / 1024:.0f} KB de dados)")


if __name__ == "__main__":
    build()
