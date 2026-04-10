Meeting → Slides POC — LaTeX documentation
==========================================

File: meeting-slides-poc.tex
Output: meeting-slides-poc.pdf (in this folder after build)

Requirements
------------
A full TeX distribution: TeX Live, MiKTeX, or MacTeX.

Needed packages (usually auto-installed on first use):
  charter/mathdesign, microtype, geometry, babel, booktabs, tabularx,
  longtable, xcolor, listings, caption, tcolorbox, tikz, fancyhdr,
  lastpage, enumitem, titlesec, hyperref, setspace, parskip, array

Build (pdfLaTeX — run twice for TOC and LastPage)
-------------------------------------------------
  cd docs/latex
  pdflatex -interaction=nonstopmode meeting-slides-poc.tex
  pdflatex -interaction=nonstopmode meeting-slides-poc.tex

Alternative
-----------
  latexmk -pdf meeting-slides-poc.tex

Optional: copy PDF to docs/ for sharing
----------------------------------------
  copy meeting-slides-poc.pdf ..\meeting-slides-poc.pdf   (Windows cmd)
  cp meeting-slides-poc.pdf ../meeting-slides-poc.pdf     (Unix)
