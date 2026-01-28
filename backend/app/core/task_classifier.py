"""
Task Classifier for Brain Trust

Analyzes incoming tasks to determine their characteristics:
- Complexity score (1-10)
- Primary domain (code, creative, reasoning, etc.)
- Tool requirements
- Estimated token usage

This classification enables intelligent model routing without human intervention.

Design Philosophy:
- Use a cheap, fast model for classification (meta-routing)
- Cache classifications for repeated similar tasks
- Fallback to heuristics if classification fails
"""

import os
import re
import json
import logging
import hashlib
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum

logger = logging.getLogger(__name__)


class TaskDomain(str, Enum):
    """Primary task domain categories."""
    CODE = "code"
    CREATIVE = "creative"
    FACTUAL = "factual"
    REASONING = "reasoning"
    MULTIMODAL = "multimodal"
    TOOL_USE = "tool_use"


@dataclass
class TaskProfile:
    """Complete analysis of a task's requirements."""

    # Complexity
    complexity_score: int  # 1-10

    # Domain
    primary_domain: TaskDomain
    secondary_domains: List[TaskDomain] = field(default_factory=list)

    # Requirements
    estimated_input_tokens: int = 0
    estimated_output_tokens: int = 0
    requires_tools: bool = False
    tool_types: List[str] = field(default_factory=list)

    # Metadata
    confidence: float = 1.0  # 0.0-1.0
    classification_method: str = "heuristic"  # "llm" or "heuristic"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "complexity_score": self.complexity_score,
            "primary_domain": self.primary_domain.value,
            "secondary_domains": [d.value for d in self.secondary_domains],
            "estimated_input_tokens": self.estimated_input_tokens,
            "estimated_output_tokens": self.estimated_output_tokens,
            "requires_tools": self.requires_tools,
            "tool_types": self.tool_types,
            "confidence": self.confidence,
            "classification_method": self.classification_method,
        }


class TaskClassifier:
    """
    Lightweight classifier to analyze incoming tasks.

    Uses a combination of:
    1. Keyword heuristics (fast, free)
    2. LLM classification (accurate, costs tokens)

    The classifier uses the cheapest available model for LLM classification
    to minimize overhead.
    """

    # Keyword patterns for heuristic classification
    CODE_PATTERNS = [
        r'\b(code|function|class|method|api|bug|fix|implement|refactor)\b',
        r'\b(python|javascript|typescript|java|rust|go|sql)\b',
        r'\b(variable|loop|array|string|integer|boolean)\b',
        r'\b(debug|error|exception|stack trace)\b',
    ]

    CREATIVE_PATTERNS = [
        r'\b(write|story|creative|fiction|character|narrative)\b',
        r'\b(poem|essay|blog|article|description)\b',
        r'\b(imagine|describe|create|invent)\b',
        r'\b(tone|style|voice|mood)\b',
    ]

    REASONING_PATTERNS = [
        r'\b(analyze|evaluate|compare|contrast|explain why)\b',
        r'\b(logic|reason|argument|evidence|conclusion)\b',
        r'\b(math|calculate|equation|formula|proof)\b',
        r'\b(strategy|plan|decision|tradeoff)\b',
    ]

    FACTUAL_PATTERNS = [
        r'\b(what is|who is|when did|where is|how does)\b',
        r'\b(define|explain|describe|summarize|list)\b',
        r'\b(fact|information|data|statistic)\b',
    ]

    TOOL_PATTERNS = [
        r'\b(search|find|look up|fetch|retrieve)\b',
        r'\b(file|document|folder|directory|drive)\b',
        r'\b(execute|run|call|invoke|use tool)\b',
        r'\b(api|endpoint|request|response)\b',
    ]

    COMPLEXITY_INDICATORS = {
        # Low complexity (1-3)
        'low': [
            r'\b(simple|basic|quick|just|only)\b',
            r'\b(single|one|first)\b',
        ],
        # Medium complexity (4-6)
        'medium': [
            r'\b(several|multiple|various)\b',
            r'\b(then|after|before|next)\b',
        ],
        # High complexity (7-10)
        'high': [
            r'\b(complex|comprehensive|detailed|thorough)\b',
            r'\b(all|every|entire|complete)\b',
            r'\b(architecture|system|framework|pipeline)\b',
            r'\b(optimize|improve|enhance|refactor)\b',
        ],
    }

    def __init__(
        self,
        use_llm: bool = False,
        classifier_model: str = "gemini-2.0-flash"
    ):
        """
        Initialize the classifier.

        Args:
            use_llm: Whether to use LLM for classification (more accurate, costs tokens)
            classifier_model: Model to use for LLM classification
        """
        self.use_llm = use_llm
        self.classifier_model = classifier_model
        self._cache: Dict[str, TaskProfile] = {}

    def classify(
        self,
        task_description: str,
        agent_role: Optional[str] = None,
        context: Optional[str] = None
    ) -> TaskProfile:
        """
        Analyze a task and return its profile.

        Args:
            task_description: The task/goal text
            agent_role: Optional agent role for context
            context: Optional additional context

        Returns:
            TaskProfile with complexity, domain, and requirements
        """
        # Check cache first
        cache_key = self._cache_key(task_description, agent_role)
        if cache_key in self._cache:
            logger.debug(f"Cache hit for task classification")
            return self._cache[cache_key]

        # Try LLM classification if enabled
        if self.use_llm:
            try:
                profile = self._classify_with_llm(task_description, agent_role, context)
                if profile:
                    self._cache[cache_key] = profile
                    return profile
            except Exception as e:
                logger.warning(f"LLM classification failed, falling back to heuristics: {e}")

        # Fallback to heuristic classification
        profile = self._classify_with_heuristics(task_description, agent_role)
        self._cache[cache_key] = profile
        return profile

    def _cache_key(self, task: str, role: Optional[str]) -> str:
        """Generate cache key for a task."""
        content = f"{task}|{role or ''}"
        return hashlib.md5(content.encode()).hexdigest()[:16]

    def _classify_with_heuristics(
        self,
        task_description: str,
        agent_role: Optional[str] = None
    ) -> TaskProfile:
        """
        Classify task using keyword pattern matching.

        This is fast and free but less accurate than LLM classification.
        """
        text = task_description.lower()
        if agent_role:
            text += f" {agent_role.lower()}"

        # Detect primary domain
        domain_scores = {
            TaskDomain.CODE: self._pattern_score(text, self.CODE_PATTERNS),
            TaskDomain.CREATIVE: self._pattern_score(text, self.CREATIVE_PATTERNS),
            TaskDomain.REASONING: self._pattern_score(text, self.REASONING_PATTERNS),
            TaskDomain.FACTUAL: self._pattern_score(text, self.FACTUAL_PATTERNS),
            TaskDomain.TOOL_USE: self._pattern_score(text, self.TOOL_PATTERNS),
        }

        # Primary domain is highest scoring
        primary_domain = max(domain_scores, key=domain_scores.get)

        # Secondary domains are any with score > 0
        secondary = [d for d, s in domain_scores.items()
                     if s > 0 and d != primary_domain]

        # Detect complexity
        complexity = self._estimate_complexity(text)

        # Detect tool requirements
        requires_tools = domain_scores[TaskDomain.TOOL_USE] > 0
        tool_types = self._detect_tool_types(text)

        # Estimate tokens
        input_tokens = len(task_description.split()) * 1.3  # rough estimate
        output_tokens = self._estimate_output_tokens(primary_domain, complexity)

        return TaskProfile(
            complexity_score=complexity,
            primary_domain=primary_domain,
            secondary_domains=secondary,
            estimated_input_tokens=int(input_tokens),
            estimated_output_tokens=int(output_tokens),
            requires_tools=requires_tools,
            tool_types=tool_types,
            confidence=0.7,  # Heuristics are less confident
            classification_method="heuristic",
        )

    def _pattern_score(self, text: str, patterns: List[str]) -> int:
        """Count pattern matches in text."""
        score = 0
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            score += len(matches)
        return score

    def _estimate_complexity(self, text: str) -> int:
        """Estimate task complexity from 1-10."""
        low_score = sum(
            len(re.findall(p, text, re.IGNORECASE))
            for p in self.COMPLEXITY_INDICATORS['low']
        )
        high_score = sum(
            len(re.findall(p, text, re.IGNORECASE))
            for p in self.COMPLEXITY_INDICATORS['high']
        )

        # Base complexity on text length and indicators
        base = 5
        length_factor = min(len(text.split()) / 50, 2)  # Longer = more complex

        complexity = base + length_factor + (high_score * 1.5) - (low_score * 1.5)
        return max(1, min(10, int(complexity)))

    def _detect_tool_types(self, text: str) -> List[str]:
        """Detect likely tool types needed."""
        tools = []

        if re.search(r'\b(file|document|folder|drive|read|write)\b', text, re.I):
            tools.append("file_access")

        if re.search(r'\b(search|google|web|internet|lookup)\b', text, re.I):
            tools.append("web_search")

        if re.search(r'\b(execute|run|command|script|shell)\b', text, re.I):
            tools.append("code_execution")

        if re.search(r'\b(api|endpoint|http|request|fetch)\b', text, re.I):
            tools.append("api_call")

        return tools

    def _estimate_output_tokens(self, domain: TaskDomain, complexity: int) -> int:
        """Estimate expected output token count."""
        base_tokens = {
            TaskDomain.CODE: 500,
            TaskDomain.CREATIVE: 1000,
            TaskDomain.REASONING: 800,
            TaskDomain.FACTUAL: 300,
            TaskDomain.TOOL_USE: 200,
            TaskDomain.MULTIMODAL: 500,
        }

        base = base_tokens.get(domain, 500)
        # Scale by complexity
        multiplier = 0.5 + (complexity / 10)
        return int(base * multiplier)

    def _classify_with_llm(
        self,
        task_description: str,
        agent_role: Optional[str],
        context: Optional[str]
    ) -> Optional[TaskProfile]:
        """
        Classify task using LLM (more accurate but costs tokens).

        Uses the cheapest fast model available.
        """
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI

            llm = ChatGoogleGenerativeAI(
                model=self.classifier_model,
                google_api_key=os.getenv("GEMINI_API_KEY"),
                temperature=0.0,  # Deterministic
            )

            prompt = f"""Analyze this task and respond with JSON only:

Task: {task_description}
Agent Role: {agent_role or 'General'}
Context: {context or 'None'}

Respond with this exact JSON structure:
{{
  "complexity_score": <1-10>,
  "primary_domain": "<code|creative|factual|reasoning|tool_use>",
  "requires_tools": <true|false>,
  "tool_types": ["<type1>", "<type2>"],
  "estimated_output_tokens": <number>
}}

Only output valid JSON, nothing else."""

            response = llm.invoke(prompt)
            content = response.content.strip()

            # Extract JSON from response
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]

            data = json.loads(content)

            return TaskProfile(
                complexity_score=int(data.get("complexity_score", 5)),
                primary_domain=TaskDomain(data.get("primary_domain", "factual")),
                requires_tools=bool(data.get("requires_tools", False)),
                tool_types=data.get("tool_types", []),
                estimated_output_tokens=int(data.get("estimated_output_tokens", 500)),
                confidence=0.9,
                classification_method="llm",
            )

        except Exception as e:
            logger.warning(f"LLM classification failed: {e}")
            return None

    def clear_cache(self) -> None:
        """Clear the classification cache."""
        self._cache.clear()


# Convenience function
def classify_task(
    task: str,
    role: Optional[str] = None,
    use_llm: bool = False
) -> TaskProfile:
    """Quick task classification."""
    classifier = TaskClassifier(use_llm=use_llm)
    return classifier.classify(task, role)
