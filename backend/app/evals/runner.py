"""
Evaluation Runner for Brain Trust

Executes test cases against agents and collects evaluation results.
"""

import os
import uuid
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from crewai import Agent, Task

from .schema import (
    TestCase,
    TestResult,
    EvaluatorResult,
    EvalRunSummary,
    ModelComparison,
    load_test_cases,
)
from .evaluators import get_evaluator

logger = logging.getLogger(__name__)


class EvalRunner:
    """
    Executes evaluation test cases against agents.

    Supports:
    - Running individual test cases
    - Running entire test suites
    - Comparing models A vs B
    - Parallel execution for faster results
    """

    def __init__(
        self,
        model_id: str = "gemini-2.0-flash",
        auto_route: bool = False,
        parallel: bool = False,
        max_workers: int = 3,
    ):
        """
        Initialize the eval runner.

        Args:
            model_id: Model to test (or 'auto' for semantic routing)
            auto_route: Use semantic router for model selection
            parallel: Run test cases in parallel
            max_workers: Max concurrent test executions
        """
        self.model_id = model_id
        self.auto_route = auto_route
        self.parallel = parallel
        self.max_workers = max_workers
        self._tools_called: List[str] = []

    def run_suite(
        self,
        test_cases: Optional[List[TestCase]] = None,
        categories: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
    ) -> EvalRunSummary:
        """
        Run a suite of test cases.

        Args:
            test_cases: Explicit test cases (or load from files if None)
            categories: Filter by categories
            tags: Filter by tags

        Returns:
            EvalRunSummary with all results
        """
        # Load test cases if not provided
        if test_cases is None:
            test_cases = load_test_cases()

        # Filter by category
        if categories:
            test_cases = [tc for tc in test_cases if tc.category in categories]

        # Filter by tags
        if tags:
            test_cases = [
                tc for tc in test_cases
                if any(tag in tc.tags for tag in tags)
            ]

        if not test_cases:
            logger.warning("No test cases to run")
            return EvalRunSummary(
                run_id=str(uuid.uuid4())[:8],
                model_id=self.model_id,
                started_at=datetime.now(),
                completed_at=datetime.now(),
            )

        logger.info(f"Running {len(test_cases)} test cases with model {self.model_id}")

        summary = EvalRunSummary(
            run_id=str(uuid.uuid4())[:8],
            model_id=self.model_id,
            started_at=datetime.now(),
        )

        # Execute test cases
        if self.parallel and len(test_cases) > 1:
            results = self._run_parallel(test_cases)
        else:
            results = self._run_sequential(test_cases)

        summary.test_results = results
        summary.completed_at = datetime.now()
        summary.calculate_summary()

        # Log summary
        logger.info(
            f"Eval complete: {summary.passed_tests}/{summary.total_tests} passed "
            f"({summary.average_score:.1%} avg score)"
        )

        return summary

    def run_single(self, test_case: TestCase) -> TestResult:
        """
        Run a single test case.

        Args:
            test_case: The test case to run

        Returns:
            TestResult with evaluation
        """
        logger.info(f"Running test: {test_case.id} - {test_case.name}")
        start_time = time.time()

        try:
            # Create and execute agent
            agent_output, tools_called = self._execute_agent(test_case)
            duration = time.time() - start_time

            # Create result
            result = TestResult(
                test_case_id=test_case.id,
                test_case_name=test_case.name,
                model_id=self.model_id,
                executed_at=datetime.now(),
                duration_seconds=duration,
                agent_output=agent_output,
                tools_called=tools_called,
            )

            # Run evaluators
            execution_context = {
                "model_id": self.model_id,
                "duration_seconds": duration,
            }

            for evaluator_name in test_case.evaluators:
                try:
                    evaluator = get_evaluator(evaluator_name)
                    eval_result = evaluator.evaluate(
                        test_case=test_case,
                        agent_output=agent_output,
                        tools_called=tools_called,
                        execution_context=execution_context,
                    )
                    result.evaluator_results.append(eval_result)
                except Exception as e:
                    logger.error(f"Evaluator {evaluator_name} failed: {e}")
                    result.evaluator_results.append(
                        EvaluatorResult(
                            evaluator_name=evaluator_name,
                            score=0.0,
                            passed=False,
                            reasoning=f"Evaluator error: {str(e)}",
                        )
                    )

            # Calculate overall score
            result.calculate_overall_score()
            result.passed = result.overall_score >= test_case.passing_threshold

            logger.info(
                f"Test {test_case.id}: {'PASS' if result.passed else 'FAIL'} "
                f"(score: {result.overall_score:.2f})"
            )

            return result

        except Exception as e:
            logger.error(f"Test {test_case.id} failed with error: {e}")
            return TestResult(
                test_case_id=test_case.id,
                test_case_name=test_case.name,
                model_id=self.model_id,
                executed_at=datetime.now(),
                duration_seconds=time.time() - start_time,
                agent_output="",
                error=str(e),
            )

    def compare_models(
        self,
        model_a: str,
        model_b: str,
        test_cases: Optional[List[TestCase]] = None,
    ) -> ModelComparison:
        """
        Compare two models on the same test suite.

        Args:
            model_a: First model ID
            model_b: Second model ID
            test_cases: Test cases to run (or load from files)

        Returns:
            ModelComparison with results and winner
        """
        logger.info(f"Comparing models: {model_a} vs {model_b}")

        # Load test cases if needed
        if test_cases is None:
            test_cases = load_test_cases()

        # Run model A
        self.model_id = model_a
        summary_a = self.run_suite(test_cases)

        # Run model B
        self.model_id = model_b
        summary_b = self.run_suite(test_cases)

        # Create comparison
        comparison = ModelComparison(
            model_a_id=model_a,
            model_b_id=model_b,
            model_a_summary=summary_a,
            model_b_summary=summary_b,
        )
        comparison.compare()

        logger.info(
            f"Comparison complete. Winner: {comparison.winner} "
            f"(margin: {comparison.margin:.1%})"
        )

        return comparison

    def _run_sequential(self, test_cases: List[TestCase]) -> List[TestResult]:
        """Run test cases sequentially."""
        results = []
        for test_case in test_cases:
            result = self.run_single(test_case)
            results.append(result)
        return results

    def _run_parallel(self, test_cases: List[TestCase]) -> List[TestResult]:
        """Run test cases in parallel."""
        results = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_test = {
                executor.submit(self.run_single, tc): tc
                for tc in test_cases
            }
            for future in as_completed(future_to_test):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    test_case = future_to_test[future]
                    logger.error(f"Parallel execution failed for {test_case.id}: {e}")
                    results.append(
                        TestResult(
                            test_case_id=test_case.id,
                            test_case_name=test_case.name,
                            model_id=self.model_id,
                            executed_at=datetime.now(),
                            duration_seconds=0,
                            agent_output="",
                            error=str(e),
                        )
                    )
        return results

    def _execute_agent(self, test_case: TestCase) -> tuple[str, List[str]]:
        """
        Create and execute an agent for the test case.

        Returns:
            Tuple of (agent_output, tools_called)
        """
        from app.tools import get_registry

        # Track tools called
        tools_called = []

        # Create LLM
        llm = self._create_llm(self.model_id)

        # Get tools for the role
        tool_registry = get_registry()
        tools = tool_registry.get_for_adapter("crewai", role=test_case.agent_role)

        # Wrap tools to track calls
        wrapped_tools = self._wrap_tools_for_tracking(tools, tools_called)

        # Build backstory
        backstory = test_case.agent_backstory or f"You are a {test_case.agent_role}."

        # Create agent
        agent = Agent(
            role=test_case.agent_role,
            goal=test_case.agent_goal,
            backstory=backstory,
            allow_delegation=False,
            tools=wrapped_tools,
            verbose=False,  # Quiet for eval runs
            llm=llm,
            max_iter=3,  # Limit iterations for eval speed
        )

        # Build task description
        task_description = test_case.input_prompt
        if test_case.context:
            task_description = f"Context:\n{test_case.context}\n\nTask:\n{task_description}"

        # Create and execute task
        task = Task(
            description=task_description,
            agent=agent,
            expected_output="Complete the task as specified.",
        )

        # Execute with timeout handling
        import signal

        def timeout_handler(signum, frame):
            raise TimeoutError(f"Test timed out after {test_case.timeout_seconds}s")

        # Note: signal.alarm only works on Unix, use threading for cross-platform
        try:
            result = agent.execute_task(task)
            output = str(result)
        except Exception as e:
            output = f"Error: {str(e)}"

        return output, tools_called

    def _wrap_tools_for_tracking(
        self,
        tools: List[Any],
        tools_called: List[str]
    ) -> List[Any]:
        """Wrap tools to track which ones are called."""
        # For now, return tools as-is
        # Tool tracking is done via CrewAI's internal logging
        # TODO: Implement proper tool call interception

        # Simple approach: monkey-patch the _run method
        for tool in tools:
            original_run = getattr(tool, '_run', None)
            if original_run:
                tool_name = getattr(tool, 'name', str(tool))

                def make_wrapped(orig, name):
                    def wrapped(*args, **kwargs):
                        tools_called.append(name)
                        return orig(*args, **kwargs)
                    return wrapped

                tool._run = make_wrapped(original_run, tool_name)

        return tools

    def _create_llm(self, model_name: str):
        """Create LLM instance for the given model."""
        model_lower = model_name.lower()

        if 'gemini' in model_lower:
            from langchain_google_genai import ChatGoogleGenerativeAI
            return ChatGoogleGenerativeAI(
                model=model_name,
                google_api_key=os.getenv("GEMINI_API_KEY"),
                temperature=0.0,  # Deterministic for evals
            )

        elif 'claude' in model_lower or 'sonnet' in model_lower or 'opus' in model_lower:
            from langchain_anthropic import ChatAnthropic

            # Map friendly names
            if "sonnet" in model_lower and "4" not in model_lower:
                ant_model = "claude-sonnet-4-20250514"
            elif "opus" in model_lower and "4" not in model_lower:
                ant_model = "claude-opus-4-20250514"
            else:
                ant_model = model_name

            return ChatAnthropic(
                model_name=ant_model,
                api_key=os.getenv("ANTHROPIC_API_KEY"),
                temperature=0.0,
            )

        elif 'gpt' in model_lower:
            try:
                from langchain_openai import ChatOpenAI
                return ChatOpenAI(
                    model=model_name,
                    api_key=os.getenv("OPENAI_API_KEY"),
                    temperature=0.0,
                )
            except ImportError:
                logger.warning("langchain_openai not installed, falling back to Gemini")

        # Default fallback
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            google_api_key=os.getenv("GEMINI_API_KEY"),
            temperature=0.0,
        )


def run_evals(
    model: str = "gemini-2.0-flash",
    categories: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
    parallel: bool = False,
) -> EvalRunSummary:
    """
    Convenience function to run evaluations.

    Args:
        model: Model ID to test
        categories: Filter by categories
        tags: Filter by tags
        parallel: Run in parallel

    Returns:
        EvalRunSummary with results
    """
    runner = EvalRunner(model_id=model, parallel=parallel)
    return runner.run_suite(categories=categories, tags=tags)


def compare_models(
    model_a: str,
    model_b: str,
    categories: Optional[List[str]] = None,
) -> ModelComparison:
    """
    Convenience function to compare two models.

    Args:
        model_a: First model ID
        model_b: Second model ID
        categories: Filter test cases by category

    Returns:
        ModelComparison with results
    """
    runner = EvalRunner()
    test_cases = load_test_cases()

    if categories:
        test_cases = [tc for tc in test_cases if tc.category in categories]

    return runner.compare_models(model_a, model_b, test_cases)
