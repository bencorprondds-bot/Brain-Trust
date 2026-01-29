"""
Evaluation API Routes

Endpoints for running and managing evaluations.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Security
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.core.auth import verify_api_key
from app.evals import load_test_cases, TestCase
from app.evals.runner import EvalRunner, run_evals, compare_models

router = APIRouter(prefix="/evals", tags=["evaluations"])


class EvalRequest(BaseModel):
    """Request to run evaluations."""
    model: str = "gemini-2.0-flash"
    categories: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    parallel: bool = False
    test_ids: Optional[List[str]] = None  # Run specific tests


class CompareRequest(BaseModel):
    """Request to compare two models."""
    model_a: str
    model_b: str
    categories: Optional[List[str]] = None


class EvalResponse(BaseModel):
    """Response from eval run."""
    run_id: str
    model_id: str
    total_tests: int
    passed_tests: int
    failed_tests: int
    average_score: float
    duration_seconds: float
    results: List[Dict[str, Any]]


class CompareResponse(BaseModel):
    """Response from model comparison."""
    model_a_id: str
    model_b_id: str
    model_a_score: float
    model_b_score: float
    winner: str
    margin: float
    test_comparisons: List[Dict[str, Any]]


# Store running/completed evals
_eval_results: Dict[str, Dict[str, Any]] = {}


@router.post("/run", dependencies=[Security(verify_api_key)])
async def run_evaluations(request: EvalRequest, background_tasks: BackgroundTasks):
    """
    Run evaluation suite.

    Can run in foreground (blocking) or background.
    """
    runner = EvalRunner(
        model_id=request.model,
        parallel=request.parallel,
    )

    # Load and filter test cases
    test_cases = load_test_cases()

    if request.test_ids:
        test_cases = [tc for tc in test_cases if tc.id in request.test_ids]

    if request.categories:
        test_cases = [tc for tc in test_cases if tc.category in request.categories]

    if request.tags:
        test_cases = [
            tc for tc in test_cases
            if any(tag in tc.tags for tag in request.tags)
        ]

    if not test_cases:
        raise HTTPException(status_code=404, detail="No matching test cases found")

    # Run evaluations
    summary = runner.run_suite(test_cases)

    # Store result
    _eval_results[summary.run_id] = summary.to_dict()

    return EvalResponse(
        run_id=summary.run_id,
        model_id=summary.model_id,
        total_tests=summary.total_tests,
        passed_tests=summary.passed_tests,
        failed_tests=summary.failed_tests,
        average_score=summary.average_score,
        duration_seconds=(
            (summary.completed_at - summary.started_at).total_seconds()
            if summary.completed_at else 0
        ),
        results=[r.to_dict() for r in summary.test_results],
    )


@router.post("/compare", dependencies=[Security(verify_api_key)])
async def compare_models_endpoint(request: CompareRequest):
    """
    Compare two models on the same test suite.
    """
    comparison = compare_models(
        model_a=request.model_a,
        model_b=request.model_b,
        categories=request.categories,
    )

    return CompareResponse(
        model_a_id=comparison.model_a_id,
        model_b_id=comparison.model_b_id,
        model_a_score=comparison.model_a_summary.average_score,
        model_b_score=comparison.model_b_summary.average_score,
        winner=comparison.winner or "tie",
        margin=comparison.margin,
        test_comparisons=comparison.test_comparisons,
    )


@router.get("/tests", dependencies=[Security(verify_api_key)])
async def list_test_cases(
    category: Optional[str] = None,
    tag: Optional[str] = None,
):
    """
    List available test cases.
    """
    test_cases = load_test_cases()

    if category:
        test_cases = [tc for tc in test_cases if tc.category == category]

    if tag:
        test_cases = [tc for tc in test_cases if tag in tc.tags]

    return {
        "count": len(test_cases),
        "tests": [
            {
                "id": tc.id,
                "name": tc.name,
                "agent_role": tc.agent_role,
                "category": tc.category,
                "tags": tc.tags,
                "evaluators": tc.evaluators,
            }
            for tc in test_cases
        ],
    }


@router.get("/results/{run_id}", dependencies=[Security(verify_api_key)])
async def get_eval_result(run_id: str):
    """
    Get results of a specific eval run.
    """
    if run_id not in _eval_results:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

    return _eval_results[run_id]


@router.get("/categories", dependencies=[Security(verify_api_key)])
async def list_categories():
    """
    List available test categories.
    """
    test_cases = load_test_cases()
    categories = set(tc.category for tc in test_cases)
    return {"categories": sorted(categories)}


@router.get("/tags", dependencies=[Security(verify_api_key)])
async def list_tags():
    """
    List available test tags.
    """
    test_cases = load_test_cases()
    tags = set()
    for tc in test_cases:
        tags.update(tc.tags)
    return {"tags": sorted(tags)}
