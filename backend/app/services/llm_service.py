"""LLM service for generating reports and presentations using Claude."""

import json
import logging
from typing import Any

from anthropic import Anthropic

from app.models.schemas import GeneratedPresentation, GeneratedReport, ReportSection

logger = logging.getLogger(__name__)


class LLMService:
    """Service for interacting with Claude API for content generation."""

    def __init__(self, api_key: str):
        """Initialize with Anthropic API key."""
        self.client = Anthropic(api_key=api_key)

    def generate_report(
        self,
        context: str,
        custom_instructions: str | None,
        detail_level: str,
        title_hint: str | None = None,
    ) -> GeneratedReport:
        """
        Generate a structured report from document context.

        Args:
            context: Combined document content
            custom_instructions: User-provided instructions
            detail_level: "executive", "standard", or "comprehensive"
            title_hint: Optional title suggestion

        Returns:
            GeneratedReport with structured content
        """
        detail_guidance = {
            "executive": """Create a concise executive summary report (1-2 pages equivalent).
Focus on:
- High-level insights and key takeaways
- Critical findings that require attention
- Actionable recommendations
Keep sections brief and impactful.""",
            "standard": """Create a balanced report (3-5 pages equivalent).
Include:
- Executive summary
- Detailed analysis of key topics
- Supporting evidence and data
- Clear recommendations with rationale""",
            "comprehensive": """Create an in-depth analytical report (5-10 pages equivalent).
Provide:
- Thorough executive summary
- Comprehensive analysis of all topics
- Detailed findings with full supporting evidence
- Multiple recommendations with implementation considerations
- Context and background where relevant""",
        }

        system_prompt = f"""You are an expert research analyst and report writer.

Your task is to synthesize the provided source documents into a well-structured, professional report.

DETAIL LEVEL: {detail_level.upper()}
{detail_guidance.get(detail_level, detail_guidance["standard"])}

OUTPUT FORMAT: You must respond with ONLY valid JSON matching this exact structure:
{{
    "title": "Report Title",
    "executive_summary": "2-3 paragraph executive summary",
    "sections": [
        {{
            "title": "Section Title",
            "content": "Section content with full paragraphs. Use complete sentences and professional language.",
            "subsections": [
                {{
                    "title": "Subsection Title",
                    "content": "Subsection content",
                    "subsections": []
                }}
            ]
        }}
    ],
    "key_findings": [
        "Key finding 1 - specific and actionable",
        "Key finding 2 - with supporting context"
    ],
    "recommendations": [
        "Recommendation 1 - clear and implementable",
        "Recommendation 2 - with expected impact"
    ],
    "sources": [
        "Source document 1 name",
        "Source document 2 name"
    ]
}}

CRITICAL REQUIREMENTS:
1. Write in professional, clear prose
2. Support all claims with evidence from the source documents
3. Maintain objectivity - present facts, not opinions unless clearly labeled
4. Structure content logically with clear transitions
5. Cite sources when referencing specific information
6. Return ONLY the JSON object, no additional text or markdown"""

        user_content = ""
        if custom_instructions:
            user_content += f"""USER INSTRUCTIONS:
{custom_instructions}

"""

        if title_hint:
            user_content += f"""SUGGESTED TITLE: {title_hint}

"""

        user_content += f"""SOURCE DOCUMENTS:
{context}

Generate the report now. Remember to output ONLY valid JSON."""

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=8000,
                messages=[{"role": "user", "content": user_content}],
                system=system_prompt,
            )

            # Parse JSON response
            response_text = response.content[0].text.strip()

            # Handle potential markdown code blocks
            if response_text.startswith("```"):
                # Extract JSON from code block
                lines = response_text.split("\n")
                json_lines = []
                in_json = False
                for line in lines:
                    if line.startswith("```") and not in_json:
                        in_json = True
                        continue
                    elif line.startswith("```") and in_json:
                        break
                    elif in_json:
                        json_lines.append(line)
                response_text = "\n".join(json_lines)

            report_data = json.loads(response_text)

            # Convert to Pydantic model
            return GeneratedReport(
                title=report_data.get("title", "Research Report"),
                executive_summary=report_data.get("executive_summary", ""),
                sections=[
                    self._parse_section(s) for s in report_data.get("sections", [])
                ],
                key_findings=report_data.get("key_findings", []),
                recommendations=report_data.get("recommendations", []),
                sources=report_data.get("sources", []),
            )

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            logger.error(f"Response was: {response_text[:500]}...")
            raise ValueError("LLM returned invalid JSON response")
        except Exception as e:
            logger.error(f"Report generation failed: {e}")
            raise

    def _parse_section(self, section_data: dict) -> ReportSection:
        """Parse a section dict into ReportSection model."""
        return ReportSection(
            title=section_data.get("title", ""),
            content=section_data.get("content", ""),
            subsections=[
                self._parse_section(s)
                for s in section_data.get("subsections", [])
            ],
        )

    def generate_presentation(
        self,
        report: GeneratedReport,
        slide_count_min: int,
        slide_count_max: int,
    ) -> GeneratedPresentation:
        """
        Generate a presentation from a report.

        Args:
            report: Generated report to convert
            slide_count_min: Minimum number of slides
            slide_count_max: Maximum number of slides

        Returns:
            GeneratedPresentation with slide structure
        """
        system_prompt = f"""You are an expert presentation designer.

Convert the provided report into a compelling, professional presentation.

SLIDE COUNT: Create between {slide_count_min} and {slide_count_max} slides.

OUTPUT FORMAT: Respond with ONLY valid JSON matching this structure:
{{
    "title": "Presentation Title",
    "slides": [
        {{
            "type": "title",
            "title": "Main Presentation Title",
            "subtitle": "Subtitle or date"
        }},
        {{
            "type": "section",
            "title": "Section Divider Title"
        }},
        {{
            "type": "content",
            "title": "Slide Title",
            "bullets": ["Point 1", "Point 2", "Point 3"],
            "notes": "Speaker notes for this slide"
        }},
        {{
            "type": "key_findings",
            "title": "Key Findings",
            "findings": ["Finding 1", "Finding 2", "Finding 3"]
        }},
        {{
            "type": "recommendations",
            "title": "Recommendations",
            "items": ["Recommendation 1", "Recommendation 2"]
        }},
        {{
            "type": "closing",
            "title": "Thank You",
            "contact": "Contact information or next steps"
        }}
    ]
}}

SLIDE TYPES:
- "title": Opening slide with main title and subtitle
- "section": Section divider slide
- "content": Main content slide with bullet points (max 6 bullets per slide)
- "key_findings": Highlight key findings
- "recommendations": Present recommendations
- "closing": Final slide

GUIDELINES:
1. Start with a title slide
2. Use section dividers to organize major topics
3. Keep bullet points concise (1-2 lines each)
4. Maximum 6 bullet points per content slide
5. Include speaker notes with additional context
6. End with recommendations and a closing slide
7. Make content visually digestible - avoid text overload

Return ONLY the JSON object."""

        # Format report content for LLM
        sections_text = ""
        for section in report.sections:
            sections_text += f"\n## {section.title}\n{section.content}\n"
            for subsection in section.subsections:
                sections_text += f"\n### {subsection.title}\n{subsection.content}\n"

        user_content = f"""Create a presentation from this report:

TITLE: {report.title}

EXECUTIVE SUMMARY:
{report.executive_summary}

SECTIONS:
{sections_text}

KEY FINDINGS:
{chr(10).join(f'- {f}' for f in report.key_findings)}

RECOMMENDATIONS:
{chr(10).join(f'- {r}' for r in report.recommendations)}

Generate the presentation slides now. Return ONLY valid JSON."""

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4000,
                messages=[{"role": "user", "content": user_content}],
                system=system_prompt,
            )

            response_text = response.content[0].text.strip()

            # Handle potential markdown code blocks
            if response_text.startswith("```"):
                lines = response_text.split("\n")
                json_lines = []
                in_json = False
                for line in lines:
                    if line.startswith("```") and not in_json:
                        in_json = True
                        continue
                    elif line.startswith("```") and in_json:
                        break
                    elif in_json:
                        json_lines.append(line)
                response_text = "\n".join(json_lines)

            pres_data = json.loads(response_text)

            return GeneratedPresentation(
                title=pres_data.get("title", report.title),
                slides=pres_data.get("slides", []),
            )

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse presentation JSON: {e}")
            raise ValueError("LLM returned invalid JSON for presentation")
        except Exception as e:
            logger.error(f"Presentation generation failed: {e}")
            raise

    def get_token_usage(self, response: Any) -> tuple[int, int]:
        """Extract input and output token counts from response."""
        if hasattr(response, "usage"):
            return (
                getattr(response.usage, "input_tokens", 0),
                getattr(response.usage, "output_tokens", 0),
            )
        return 0, 0
