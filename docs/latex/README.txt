Meeting → Slides POC — LaTeX documentation
==========================================

Build PDF (requires a LaTeX distribution: MiKTeX, TeX Live, etc.)

  cd docs/latex
  pdflatex -interaction=nonstopmode meeting-slides-poc.tex
  pdflatex -interaction=nonstopmode meeting-slides-poc.tex

Output: meeting-slides-poc.pdf

Optional: latexmk -pdf meeting-slides-poc.tex
