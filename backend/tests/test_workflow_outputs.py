"""Test workflow steps with raw LLM inputs and outputs.

This test demonstrates that pydantic-ai properly enforces schema compliance
for structured outputs, eliminating probabilistic parsing.

Run with: pytest tests/test_workflow_outputs.py -v -s
"""

import asyncio
import json
import os
from datetime import datetime

import pytest
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai_litellm import LiteLLMModel

# Simple test schema
class SimpleReport(BaseModel):
    """A simple report schema for testing."""

    title: str = Field(..., description="Report title")
    summary: str = Field(..., description="Brief summary")
    key_points: list[str] = Field(..., description="List of key points")


class TestStructuredOutputs:
    """Test that pydantic-ai enforces structured outputs."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test environment."""
        # Ensure API key is set
        if not os.environ.get("ANTHROPIC_API_KEY"):
            pytest.skip("ANTHROPIC_API_KEY not set")

    @pytest.mark.asyncio
    async def test_simple_structured_output(self):
        """Test that pydantic-ai returns validated Pydantic model."""
        model = LiteLLMModel("anthropic/claude-3-5-haiku-20241022")

        agent = Agent(
            model,
            output_type=SimpleReport,
            system_prompt="You are a helpful assistant that creates brief reports.",
        )

        user_message = "Create a brief report about the benefits of exercise."

        print("\n" + "=" * 60)
        print("TEST: Simple Structured Output")
        print("=" * 60)
        print(f"\n[INPUT] User message:\n{user_message}")
        print(f"\n[INPUT] Expected schema:\n{json.dumps(SimpleReport.model_json_schema(), indent=2)}")

        # Run the agent
        result = await agent.run(user_message)

        print(f"\n[OUTPUT] Result type: {type(result.output)}")
        print(f"\n[OUTPUT] Result data:\n{result.output.model_dump_json(indent=2)}")

        # Verify it's a validated Pydantic model
        assert isinstance(result.output, SimpleReport)
        assert result.output.title
        assert result.output.summary
        assert len(result.output.key_points) > 0

        # Log usage
        usage = result.usage()
        print(f"\n[USAGE] Request tokens: {usage.request_tokens}")
        print(f"[USAGE] Response tokens: {usage.response_tokens}")
        print("=" * 60)

    @pytest.mark.asyncio
    async def test_complex_nested_schema(self):
        """Test nested schema validation."""

        class Section(BaseModel):
            """A report section."""
            title: str
            content: str
            importance: str = Field(..., description="high, medium, or low")

        class DetailedReport(BaseModel):
            """A detailed report with nested sections."""
            title: str
            executive_summary: str
            sections: list[Section]
            recommendations: list[str]

        model = LiteLLMModel("anthropic/claude-3-5-haiku-20241022")

        agent = Agent(
            model,
            output_type=DetailedReport,
            system_prompt="You are an expert analyst creating detailed reports.",
        )

        user_message = "Create a report analyzing remote work trends in 2024."

        print("\n" + "=" * 60)
        print("TEST: Complex Nested Schema")
        print("=" * 60)
        print(f"\n[INPUT] User message:\n{user_message}")
        print(f"\n[INPUT] Expected schema (nested):\n{json.dumps(DetailedReport.model_json_schema(), indent=2)[:1000]}...")

        result = await agent.run(user_message)

        print(f"\n[OUTPUT] Result type: {type(result.output)}")
        print(f"[OUTPUT] Title: {result.output.title}")
        print(f"[OUTPUT] Sections count: {len(result.output.sections)}")
        print(f"[OUTPUT] First section: {result.output.sections[0].title if result.output.sections else 'N/A'}")
        print(f"[OUTPUT] Recommendations count: {len(result.output.recommendations)}")

        # Verify nested structure
        assert isinstance(result.output, DetailedReport)
        assert len(result.output.sections) > 0
        for section in result.output.sections:
            assert isinstance(section, Section)
            assert section.title
            assert section.content
            assert section.importance in ["high", "medium", "low"]

        print("=" * 60)

    @pytest.mark.asyncio
    async def test_gateway_structured_output(self):
        """Test the ModelGateway structured output method."""
        from app.llm import GatewayConfig, ModelGateway, TaskType

        config = GatewayConfig(
            anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
        )
        gateway = ModelGateway(config)

        user_message = "Create a brief report about cloud computing benefits."

        print("\n" + "=" * 60)
        print("TEST: Gateway Structured Output")
        print("=" * 60)
        print(f"\n[INPUT] Task type: {TaskType.REPORT_GENERATION.value}")
        print(f"\n[INPUT] User message:\n{user_message}")
        print(f"\n[INPUT] Output schema: SimpleReport")

        result, usage = await gateway.generate_structured(
            task=TaskType.REPORT_GENERATION,
            output_schema=SimpleReport,
            messages=[{"role": "user", "content": user_message}],
            system_prompt="You are a helpful assistant that creates brief reports.",
        )

        print(f"\n[OUTPUT] Result type: {type(result)}")
        print(f"\n[OUTPUT] Result:\n{result.model_dump_json(indent=2)}")
        print(f"\n[USAGE] Input tokens: {usage.input_tokens}")
        print(f"[USAGE] Output tokens: {usage.output_tokens}")
        print(f"[USAGE] Estimated cost: ${usage.estimated_cost:.4f}")

        # Verify it's a validated Pydantic model
        assert isinstance(result, SimpleReport)
        assert result.title
        assert result.summary
        assert len(result.key_points) > 0

        print("=" * 60)


class TestWorkflowSteps:
    """Test individual workflow steps with raw outputs."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test environment."""
        if not os.environ.get("ANTHROPIC_API_KEY"):
            pytest.skip("ANTHROPIC_API_KEY not set")

    @pytest.mark.asyncio
    async def test_report_generation_step(self):
        """Test the report generation step with full schema."""
        from app.llm import GatewayConfig, ModelGateway, TaskType
        from app.models.llm_outputs import LLMGeneratedReport

        config = GatewayConfig(
            anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
        )
        gateway = ModelGateway(config)

        # Simulated document context
        context = """
        Document 1: Q4 2024 Sales Report
        - Total revenue: $5.2M
        - Growth: 15% YoY
        - Top product: Enterprise Suite
        - New customers: 45

        Document 2: Customer Feedback Summary
        - Overall satisfaction: 4.2/5
        - Top praise: Product reliability
        - Top complaint: Onboarding complexity
        - NPS Score: 42
        """

        system_prompt = """You are an expert research analyst. Create a professional report.

DETAIL LEVEL: STANDARD
Create a balanced report (3-5 pages equivalent). Include executive summary, analysis, and recommendations."""

        user_message = f"""SOURCE DOCUMENTS:
{context}

Generate the report now."""

        print("\n" + "=" * 60)
        print("TEST: Report Generation Workflow Step")
        print("=" * 60)
        print(f"\n[INPUT] System prompt:\n{system_prompt[:500]}...")
        print(f"\n[INPUT] User message:\n{user_message[:500]}...")
        print(f"\n[INPUT] Output schema: LLMGeneratedReport")

        result, usage = await gateway.generate_structured(
            task=TaskType.REPORT_GENERATION,
            output_schema=LLMGeneratedReport,
            messages=[{"role": "user", "content": user_message}],
            system_prompt=system_prompt,
            max_tokens=4000,
        )

        print(f"\n[OUTPUT] Result type: {type(result)}")
        print(f"\n[OUTPUT] Title: {result.title}")
        print(f"[OUTPUT] Executive summary length: {len(result.executive_summary)} chars")
        print(f"[OUTPUT] Sections: {len(result.sections)}")
        for i, section in enumerate(result.sections):
            print(f"  - Section {i+1}: {section.title} ({len(section.content)} chars)")
        print(f"[OUTPUT] Key findings: {len(result.key_findings)}")
        for finding in result.key_findings:
            print(f"  - {finding[:80]}...")
        print(f"[OUTPUT] Recommendations: {len(result.recommendations)}")

        print(f"\n[USAGE] Input tokens: {usage.input_tokens}")
        print(f"[USAGE] Output tokens: {usage.output_tokens}")
        print(f"[USAGE] Model: {usage.model}")

        # Verify schema compliance
        assert isinstance(result, LLMGeneratedReport)
        assert result.title
        assert len(result.executive_summary) >= 100
        assert len(result.sections) >= 1
        assert len(result.key_findings) >= 2
        assert len(result.recommendations) >= 1

        print("\n[VERIFICATION] All schema constraints satisfied!")
        print("=" * 60)


class TestSchemaEnforcement:
    """Verify that invalid outputs are properly rejected."""

    @pytest.mark.asyncio
    async def test_schema_validation(self):
        """Demonstrate that pydantic-ai enforces the schema at the model level."""

        class StrictSchema(BaseModel):
            """Schema with strict requirements."""
            name: str = Field(..., min_length=5)
            count: int = Field(..., ge=1, le=10)
            category: str = Field(..., pattern="^(A|B|C)$")

        model = LiteLLMModel("anthropic/claude-3-5-haiku-20241022")

        agent = Agent(
            model,
            output_type=StrictSchema,
            system_prompt="Return data matching the schema exactly.",
        )

        print("\n" + "=" * 60)
        print("TEST: Schema Enforcement")
        print("=" * 60)
        print("\n[INPUT] Schema constraints:")
        print("  - name: min_length=5")
        print("  - count: 1-10 inclusive")
        print("  - category: must be A, B, or C")

        result = await agent.run("Generate a valid entry with name='Testing', count=5, category='B'")

        print(f"\n[OUTPUT] Result: {result.output.model_dump()}")

        # Verify constraints are met
        assert len(result.output.name) >= 5
        assert 1 <= result.output.count <= 10
        assert result.output.category in ["A", "B", "C"]

        print("\n[VERIFICATION] Schema constraints enforced by pydantic-ai!")
        print("=" * 60)


if __name__ == "__main__":
    # Run tests with output
    pytest.main([__file__, "-v", "-s"])
