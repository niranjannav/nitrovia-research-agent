---
name: presentation_design
description: >
  Skill for creating professional presentations and analyzing existing PPTX files.
  Provides code snippets for reading slide content using python-pptx, and design
  guidance for creating compelling slide decks. Use when the output format includes
  .pptx or when source documents include .pptx files.
triggers:
  file_types: [".pptx"]
  output_formats: ["pptx"]
  keywords: ["presentation", "slides", "powerpoint", "deck"]
---

# Presentation Design Skill

## Reading Existing Presentations

```python
from pptx import Presentation

prs = Presentation('presentation.pptx')
for i, slide in enumerate(prs.slides):
    print(f"\n=== Slide {i+1} (layout: {slide.slide_layout.name}) ===")
    for shape in slide.shapes:
        if shape.has_text_frame:
            for para in shape.text_frame.paragraphs:
                if para.text.strip():
                    print(f"  {para.text}")
        if shape.has_table:
            table = shape.table
            for row in table.rows:
                cells = [cell.text for cell in row.cells]
                print(f"  | {' | '.join(cells)} |")
```

## Extract Speaker Notes

```python
from pptx import Presentation

prs = Presentation('presentation.pptx')
for i, slide in enumerate(prs.slides):
    if slide.has_notes_slide:
        notes = slide.notes_slide.notes_text_frame.text
        if notes.strip():
            print(f"Slide {i+1} notes: {notes}")
```

## Slide Type Selection Guide

### Available Types
| Type | When to Use |
|------|-------------|
| `title` | Opening slide — main title + subtitle |
| `section` | Topic transition / divider |
| `content` | Core information with bullets (max 6) |
| `key_findings` | 3-5 most impactful discoveries |
| `stat_callout` | Single metric focus (stat_value + context) |
| `comparison` | Side-by-side: before/after, A vs B |
| `timeline` | Sequential events (4-6 max) |
| `chart` | Data visualization (bar, line, pie, horizontal_bar) |
| `recommendations` | Action items near the end |
| `closing` | Final slide — thank you / next steps |

## Design Principles

### Content Hierarchy
1. **One idea per slide** — two topics = two slides
2. **Title carries the message** — audience should get the point from the title
3. **Bullets support, don't repeat** — expand on title, don't restate it
4. **Progressive disclosure** — build complexity through sequence, not within one slide

### Visual Storytelling Flow
1. **Hook** (title + context): Why should the audience care?
2. **Evidence** (content + data): What does the data show?
3. **Insight** (findings + stats): What does it mean?
4. **Action** (recommendations): What should we do?
5. **Close** (closing): Memorable takeaway

### Data on Slides
- Never put a full data table on a slide — summarize or visualize
- If you must show a table, max 5 rows × 4 columns
- Always state the "so what" — don't make the audience interpret raw numbers
- Use chart slides with actual data_labels and data_values

### Speaker Notes
- Write as if briefing a presenter who hasn't read the source material
- Include: key talking points, data sources, anticipated questions
- Keep to 3-5 sentences per slide
