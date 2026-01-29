"""
LLM Judge Evaluator

Uses another LLM to evaluate the quality of an agent's output.
This provides nuanced evaluation that heuristics cannot capture.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
from .base import BaseEvaluator, register_evaluator
from ..schema import TestCase, EvaluatorResult

logger = logging.getLogger(__name__)


@register_evaluator("llm_judge")
class LLMJudgeEvaluator(BaseEvaluator):
    """
    Uses an LLM to evaluate output quality.

    The judge model evaluates the agent's output against:
    - The original task requirements
    - Custom criteria if provided in test case
    - A rubric if provided

    Supports multiple LLM providers:
    - google (Gemini)
    - anthropic (Claude)

    Uses a cheap, fast model by default (gemini-2.0-flash).
    """

    name = "llm_judge"

    DEFAULT_CRITERIA = """
Evaluate the AI agent's response based on:
1. **Task Completion**: Did it actually do what was asked?
2. **Accuracy**: Is the information/output correct?
3. **Clarity**: Is the response clear and well-organized?
4. **Relevance**: Does it stay focused on the task?
5. **Quality**: Is it professional and appropriate?
"""

    DEFAULT_RUBRIC = {
        "excellent": "Score 0.9-1.0: Fully completes the task with high quality, exceeds expectations",
        "good": "Score 0.7-0.89: Completes the task well with minor issues",
        "acceptable": "Score 0.5-0.69: Completes the core task but with notable gaps",
        "poor": "Score 0.2-0.49: Partially completes the task, significant issues",
        "fail": "Score 0.0-0.19: Fails to complete the task or is incorrect",
    }

    def __init__(
        self,
        judge_model: str = "gemini-2.0-flash",
        provider: str = "google",
    ):
        """
        Initialize the LLM judge.

        Args:
            judge_model: Model to use for judging
            provider: LLM provider ("google" or "anthropic")
        """
        self.judge_model = judge_model
        self.provider = provider

    def evaluate(
        self,
        test_case: TestCase,
        agent_output: str,
        tools_called: List[str],
        execution_context: Dict[str, Any],
    ) -> EvaluatorResult:
        """Evaluate using LLM judge."""

        try:
            # Get evaluation from LLM
            evaluation = self._call_judge(test_case, agent_output, tools_called)

            if evaluation is None:
                return EvaluatorResult(
                    evaluator_name=self.name,
                    score=0.5,
                    passed=True,
                    reasoning="LLM judge unavailable, defaulting to neutral score.",
                    details={"error": "judge_unavailable", "model": self.judge_model},
                )

            # Parse evaluation response
            score = evaluation.get("score", 0.5)
            reasoning = evaluation.get("reasoning", "No reasoning provided")
            criteria_scores = evaluation.get("criteria_scores", {})

            passed = score >= test_case.passing_threshold

            return EvaluatorResult(
                evaluator_name=self.name,
                score=score,
                passed=passed,
                reasoning=reasoning,
                details={
                    "judge_model": self.judge_model,
                    "criteria_scores": criteria_scores,
                    "raw_evaluation": evaluation,
                },
            )

        except Exception as e:
            logger.error(f"LLM judge evaluation failed: {e}")
            return EvaluatorResult(
                evaluator_name=self.name,
                score=0.5,
                passed=True,
                reasoning=f"LLM judge error: {str(e)}. Defaulting to neutral score.",
                details={"error": str(e), "model": self.judge_model},
            )

    def _call_judge(
        self,
        test_case: TestCase,
        agent_output: str,
        tools_called: List[str],
    ) -> Optional[Dict[str, Any]]:
        """Call the judge LLM and parse response."""

        # Build evaluation prompt
        prompt = self._build_prompt(test_case, agent_output, tools_called)

        # Call appropriate provider
        if self.provider == "google":
            response = self._call_gemini(prompt)
        elif self.provider == "anthropic":
            response = self._call_anthropic(prompt)
        else:
            logger.error(f"Unknown provider: {self.provider}")
            return None

        if not response:
            return None

        # Parse JSON from response
        return self._parse_response(response)

    def _build_prompt(
        self,
        test_case: TestCase,
        agent_output: str,
        tools_called: List[str],
    ) -> str:
        """Build the evaluation prompt for the judge."""

        criteria = test_case.judge_criteria or self.DEFAULT_CRITERIA
        rubric = test_case.judge_rubric or self.DEFAULT_RUBRIC

        rubric_text = "\n".join(f"- {k}: {v}" for k, v in rubric.items())

        prompt = f"""You are an expert AI evaluator. Evaluate the following agent output.

## Task Information
**Agent Role**: {test_case.agent_role}
**Agent Goal**: {test_case.agent_goal}
**Task Prompt**: {test_case.input_prompt}

## Agent Output
```
{agent_output[:4000]}
```

## Tools Called
{', '.join(tools_called) if tools_called else 'None'}

## Evaluation Criteria
{criteria}

## Scoring Rubric
{rubric_text}

## Your Task
Evaluate the agent's output and respond with ONLY a JSON object in this exact format:
{{
    "score": <float 0.0-1.0>,
    "reasoning": "<2-3 sentence explanation of your score>",
    "criteria_scores": {{
        "task_completion": <float 0.0-1.0>,
        "accuracy": <float 0.0-1.0>,
        "clarity": <float 0.0-1.0>,
        "relevance": <float 0.0-1.0>,
        "quality": <float 0.0-1.0>
    }},
    "strengths": ["<strength1>", "<strength2>"],
    "weaknesses": ["<weakness1>", "<weakness2>"]
}}

Output only valid JSON, no other text."""

        return prompt

    def _call_gemini(self, prompt: str) -> Optional[str]:
        """Call Google Gemini model."""
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI

            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                logger.error("GEMINI_API_KEY not set")
                return None

            llm = ChatGoogleGenerativeAI(
                model=self.judge_model,
                google_api_key=api_key,
                temperature=0.0,  # Deterministic evaluation
            )

            response = llm.invoke(prompt)
            return response.content

        except Exception as e:
            logger.error(f"Gemini call failed: {e}")
            return None

    def _call_anthropic(self, prompt: str) -> Optional[str]:
        """Call Anthropic Claude model."""
        try:
            import anthropic

            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                logger.error("ANTHROPIC_API_KEY not set")
                return None

            client = anthropic.Anthropic(api_key=api_key)

            response = client.messages.create(
                model=self.judge_model,
                max_tokens=1024,
                temperature=0.0,
                messages=[{"role": "user", "content": prompt}],
            )

            return response.content[0].text

        except Exception as e:
            logger.error(f"Anthropic call failed: {e}")
            return None

    def _parse_response(self, response: str) -> Optional[Dict[str, Any]]:
        """Parse JSON from LLM response."""
        try:
            # Clean up response
            content = response.strip()

            # Handle code blocks
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            data = json.loads(content.strip())

            # Validate and normalize score
            score = float(data.get("score", 0.5))
            score = max(0.0, min(1.0, score))
            data["score"] = score

            return data

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse judge response: {e}")
            logger.debug(f"Response was: {response[:500]}")

            # Try to extract score with regex as fallback
            import re
            score_match = re.search(r'"score"\s*:\s*([\d.]+)', response)
            if score_match:
                return {
                    "score": float(score_match.group(1)),
                    "reasoning": "Partial parse - extracted score only",
                    "criteria_scores": {},
                }

            return None
