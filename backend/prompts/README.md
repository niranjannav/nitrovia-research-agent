# LLM Prompts Directory

This directory contains all LLM prompt templates used by the Research Agent backend.

## Files

| File | Purpose | Used By |
|------|---------|---------|
| `report_generation.txt` | Main report generation prompt | `llm_service.py` |
| `detail_levels.txt` | Detail level guidance (executive/standard/comprehensive) | `llm_service.py` |
| `presentation_generation.txt` | Slide generation from report | `llm_service.py` |
| `section_edit.txt` | Edit a single section | `llm_service.py` |
| `context_summarization.txt` | Summarize long documents | `context_builder.py` |

## Template Variables

Templates use Python's `.format()` syntax with `{variable_name}` placeholders.

### report_generation.txt
- `{detail_level}` - "executive", "standard", or "comprehensive"
- `{detail_guidance}` - Loaded from detail_levels.txt

### presentation_generation.txt
- `{slide_count_min}` - Minimum number of slides
- `{slide_count_max}` - Maximum number of slides

### section_edit.txt
- `{section_title}` - Title of the section being edited
- `{section_content}` - Current content of the section
- `{user_instructions}` - User's edit request
- `{report_context}` - Summary of the full report for context

### context_summarization.txt
- `{filename}` - Name of the document being summarized
- `{content}` - Full document content

## Modifying Prompts

1. Edit the `.txt` file directly
2. Restart the backend server for changes to take effect
3. No code changes required

## Notes

- Use double braces `{{` and `}}` for literal braces in JSON examples
- Keep prompts focused and clear
- Test changes thoroughly before deploying
