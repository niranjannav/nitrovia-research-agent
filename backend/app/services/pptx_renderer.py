"""PowerPoint presentation renderer using python-pptx."""

import logging
from io import BytesIO

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

from app.models.schemas import GeneratedPresentation

logger = logging.getLogger(__name__)


class PPTXRenderer:
    """Renders presentations as PPTX files."""

    # Brand colors
    PRIMARY_COLOR = RGBColor(37, 99, 235)  # #2563eb
    SECONDARY_COLOR = RGBColor(30, 64, 175)  # #1e40af
    WHITE = RGBColor(255, 255, 255)
    DARK_TEXT = RGBColor(26, 26, 26)
    GRAY_TEXT = RGBColor(107, 114, 128)

    # Slide dimensions (16:9)
    SLIDE_WIDTH = Inches(13.333)
    SLIDE_HEIGHT = Inches(7.5)

    def render(self, presentation: GeneratedPresentation) -> BytesIO:
        """
        Render a presentation to PPTX.

        Args:
            presentation: Generated presentation content

        Returns:
            BytesIO containing PPTX data
        """
        try:
            prs = Presentation()
            prs.slide_width = self.SLIDE_WIDTH
            prs.slide_height = self.SLIDE_HEIGHT

            for slide_data in presentation.slides:
                slide_type = slide_data.get("type", "content")

                if slide_type == "title":
                    self._add_title_slide(prs, slide_data)
                elif slide_type == "section":
                    self._add_section_slide(prs, slide_data)
                elif slide_type == "content":
                    self._add_content_slide(prs, slide_data)
                elif slide_type == "key_findings":
                    self._add_findings_slide(prs, slide_data)
                elif slide_type == "recommendations":
                    self._add_recommendations_slide(prs, slide_data)
                elif slide_type == "closing":
                    self._add_closing_slide(prs, slide_data)
                else:
                    # Default to content slide for unknown types
                    self._add_content_slide(prs, slide_data)

            output = BytesIO()
            prs.save(output)
            output.seek(0)
            return output

        except Exception as e:
            logger.error(f"PPTX rendering failed: {e}")
            raise

    def _add_title_slide(self, prs: Presentation, data: dict) -> None:
        """Add a title slide with branded background."""
        slide_layout = prs.slide_layouts[6]  # Blank layout
        slide = prs.slides.add_slide(slide_layout)

        # Set background color
        background = slide.background
        fill = background.fill
        fill.solid()
        fill.fore_color.rgb = self.PRIMARY_COLOR

        # Add title
        title_box = slide.shapes.add_textbox(
            Inches(0.5), Inches(2.5), Inches(12.333), Inches(1.5)
        )
        title_frame = title_box.text_frame
        title_para = title_frame.paragraphs[0]
        title_para.text = data.get("title", "Presentation")
        title_para.font.size = Pt(44)
        title_para.font.bold = True
        title_para.font.color.rgb = self.WHITE
        title_para.alignment = PP_ALIGN.CENTER

        # Add subtitle if present
        if subtitle := data.get("subtitle"):
            subtitle_box = slide.shapes.add_textbox(
                Inches(0.5), Inches(4.2), Inches(12.333), Inches(0.8)
            )
            subtitle_frame = subtitle_box.text_frame
            subtitle_para = subtitle_frame.paragraphs[0]
            subtitle_para.text = subtitle
            subtitle_para.font.size = Pt(24)
            subtitle_para.font.color.rgb = self.WHITE
            subtitle_para.alignment = PP_ALIGN.CENTER

    def _add_section_slide(self, prs: Presentation, data: dict) -> None:
        """Add a section divider slide."""
        slide_layout = prs.slide_layouts[6]
        slide = prs.slides.add_slide(slide_layout)

        # Left half background
        left_shape = slide.shapes.add_shape(
            1,  # Rectangle
            Inches(0), Inches(0),
            Inches(6.667), Inches(7.5)
        )
        left_shape.fill.solid()
        left_shape.fill.fore_color.rgb = self.PRIMARY_COLOR
        left_shape.line.fill.background()

        # Section title
        title_box = slide.shapes.add_textbox(
            Inches(0.5), Inches(3), Inches(6), Inches(1.5)
        )
        title_frame = title_box.text_frame
        title_para = title_frame.paragraphs[0]
        title_para.text = data.get("title", "Section")
        title_para.font.size = Pt(36)
        title_para.font.bold = True
        title_para.font.color.rgb = self.WHITE

    def _add_content_slide(self, prs: Presentation, data: dict) -> None:
        """Add a content slide with bullets."""
        slide_layout = prs.slide_layouts[6]
        slide = prs.slides.add_slide(slide_layout)

        # Title
        title_box = slide.shapes.add_textbox(
            Inches(0.5), Inches(0.3), Inches(12.333), Inches(0.8)
        )
        title_frame = title_box.text_frame
        title_para = title_frame.paragraphs[0]
        title_para.text = data.get("title", "")
        title_para.font.size = Pt(32)
        title_para.font.bold = True
        title_para.font.color.rgb = self.PRIMARY_COLOR

        # Accent line
        line = slide.shapes.add_shape(
            1,  # Rectangle
            Inches(0.5), Inches(1.1),
            Inches(2), Inches(0.05)
        )
        line.fill.solid()
        line.fill.fore_color.rgb = self.PRIMARY_COLOR
        line.line.fill.background()

        # Bullet points
        content_box = slide.shapes.add_textbox(
            Inches(0.5), Inches(1.5), Inches(12.333), Inches(5.5)
        )
        tf = content_box.text_frame
        tf.word_wrap = True

        bullets = data.get("bullets", [])
        for i, bullet in enumerate(bullets[:6]):  # Max 6 bullets
            if i == 0:
                p = tf.paragraphs[0]
            else:
                p = tf.add_paragraph()
            p.text = f"\u2022 {bullet}"
            p.font.size = Pt(20)
            p.font.color.rgb = self.DARK_TEXT
            p.space_after = Pt(12)

        # Speaker notes
        if notes := data.get("notes"):
            notes_slide = slide.notes_slide
            notes_slide.notes_text_frame.text = notes

    def _add_findings_slide(self, prs: Presentation, data: dict) -> None:
        """Add a key findings slide."""
        slide_data = {
            "title": data.get("title", "Key Findings"),
            "bullets": data.get("findings", []),
            "notes": data.get("notes"),
        }
        self._add_content_slide(prs, slide_data)

    def _add_recommendations_slide(self, prs: Presentation, data: dict) -> None:
        """Add a recommendations slide."""
        slide_data = {
            "title": data.get("title", "Recommendations"),
            "bullets": data.get("items", []),
            "notes": data.get("notes"),
        }
        self._add_content_slide(prs, slide_data)

    def _add_closing_slide(self, prs: Presentation, data: dict) -> None:
        """Add a closing/thank you slide."""
        slide_layout = prs.slide_layouts[6]
        slide = prs.slides.add_slide(slide_layout)

        # Background
        background = slide.background
        fill = background.fill
        fill.solid()
        fill.fore_color.rgb = self.SECONDARY_COLOR

        # Thank you text
        title_box = slide.shapes.add_textbox(
            Inches(0.5), Inches(2.8), Inches(12.333), Inches(1.5)
        )
        title_frame = title_box.text_frame
        title_para = title_frame.paragraphs[0]
        title_para.text = data.get("title", "Thank You")
        title_para.font.size = Pt(48)
        title_para.font.bold = True
        title_para.font.color.rgb = self.WHITE
        title_para.alignment = PP_ALIGN.CENTER

        # Contact info
        if contact := data.get("contact"):
            contact_box = slide.shapes.add_textbox(
                Inches(0.5), Inches(4.5), Inches(12.333), Inches(0.8)
            )
            contact_frame = contact_box.text_frame
            contact_para = contact_frame.paragraphs[0]
            contact_para.text = contact
            contact_para.font.size = Pt(20)
            contact_para.font.color.rgb = self.WHITE
            contact_para.alignment = PP_ALIGN.CENTER
