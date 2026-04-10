import json
from pathlib import Path
from typing import Any

from pptx import Presentation
from pptx.util import Inches, Pt


def build_deck(summary: dict[str, Any], title: str, output_path: Path) -> None:
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    def add_title_slide(t: str, subtitle: str) -> None:
        layout = prs.slide_layouts[6]  # blank
        slide = prs.slides.add_slide(layout)
        box = slide.shapes.add_textbox(Inches(0.8), Inches(2.2), Inches(11.5), Inches(2))
        tf = box.text_frame
        p = tf.paragraphs[0]
        run = p.add_run()
        run.text = t
        run.font.size = Pt(36)
        run.font.bold = True
        p2 = tf.add_paragraph()
        p2.text = subtitle
        p2.font.size = Pt(18)

    def add_bullets(heading: str, bullets: list[str]) -> None:
        layout = prs.slide_layouts[6]
        slide = prs.slides.add_slide(layout)
        title_box = slide.shapes.add_textbox(Inches(0.7), Inches(0.5), Inches(11.5), Inches(0.8))
        tf = title_box.text_frame
        tf.paragraphs[0].text = heading
        tf.paragraphs[0].font.size = Pt(28)
        tf.paragraphs[0].font.bold = True
        body = slide.shapes.add_textbox(Inches(0.9), Inches(1.4), Inches(11.2), Inches(5.5))
        btf = body.text_frame
        btf.word_wrap = True
        for i, line in enumerate(bullets):
            para = btf.paragraphs[0] if i == 0 else btf.add_paragraph()
            para.text = line
            para.level = 0
            para.font.size = Pt(18)

    def add_paragraph_slide(heading: str, text: str) -> None:
        layout = prs.slide_layouts[6]
        slide = prs.slides.add_slide(layout)
        title_box = slide.shapes.add_textbox(Inches(0.7), Inches(0.5), Inches(11.5), Inches(0.8))
        tf = title_box.text_frame
        tf.paragraphs[0].text = heading
        tf.paragraphs[0].font.size = Pt(28)
        tf.paragraphs[0].font.bold = True
        body = slide.shapes.add_textbox(Inches(0.9), Inches(1.4), Inches(11.2), Inches(5.5))
        btf = body.text_frame
        btf.word_wrap = True
        btf.paragraphs[0].text = text
        btf.paragraphs[0].font.size = Pt(16)

    add_title_slide("Meeting Briefing", title)
    add_paragraph_slide("Executive summary", summary.get("executive_summary", ""))
    add_bullets("High-level objectives", list(summary.get("objectives", [])[:3]))
    add_bullets("Actionable items", list(summary.get("actionable_items", [])[:3]))
    add_bullets("Next steps", list(summary.get("next_steps", [])))
    add_paragraph_slide("Human review", summary.get("human_review_notes", ""))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(output_path))


def write_summary_json(summary: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
