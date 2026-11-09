"""Convert a Graphviz SVG figure to PDF for inclusion in LaTeX documents.

Usage: python scripts/svg_to_pdf.py <input.svg> <output.pdf>
Requires: pip install svglib reportlab
"""

from __future__ import annotations

import sys

from reportlab.graphics import renderPDF
from svglib.svglib import svg2rlg


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    drawing = svg2rlg(sys.argv[1])
    renderPDF.drawToFile(drawing, sys.argv[2])
    print(f"wrote {sys.argv[2]}")


if __name__ == "__main__":
    main()
