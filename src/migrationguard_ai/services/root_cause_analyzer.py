"""
Root cause analyzer using Claude Sonnet 4.5 for intelligent issue diagnosis.

This module implements AI-powered root cause analysis that:
- Analyzes signals and patterns to identify underlying causes
- Classifies issues into categories (migration misstep, platform regression, etc.)
- Provides confidence scores and detailed reasoning
- Considers alternative hypotheses
- Recommends appropriate actions
"""

import json
from typing import Optional
from anthropic import AsyncAnthropic

from migrationguard_ai.core.schemas import Signal, Pattern, RootCauseAnalysis
from migrationguard_ai.core.config import get_settings
from migrationguard_ai.core.logging import get_logger
from migrationguard_ai.core.circuit_breaker import claude_api_circuit_breaker
from migrationguard_ai.core.graceful_degradation import (
    RuleBasedRootCauseAnalyzer,
    get_degradation_manager,
)

logger = get_logger(__name__)
settings = get_settings()


# System prompt for Claude
SYSTEM_PROMPT = """You are an expert system for diagnosing e-commerce platform migration issues.

Your task is to analyze signals and patterns to identify the root cause of issues that occur during headless e-commerce platform migrations.

## Classification Categories

Classify each issue into exactly ONE of these categories:

1. **migration_misstep**: The merchant made an error during the migration process
   - Examples: Incorrect API credentials, missing configuration steps, wrong endpoint URLs
   
2. **platform_regression**: A bug was introduced in the platform code
   - Examples: API breaking changes, new bugs in platform features, performance degradation
   
3. **documentation_gap**: The documentation is missing, unclear, or incorrect
   - Examples: Undocumented API changes, missing migration steps, unclear instructions
   
4. **config_error**: The merchant has incorrect settings or configuration
   - Examples: Wrong environment variables, misconfigured webhooks, invalid API scopes

## Analysis Requirements

For each analysis, you MUST provide:

1. **category**: One of the four categories above
2. **confidence**: A score between 0.0 and 1.0 indicating your certainty
   - 0.9-1.0: Very confident, clear evidence
   - 0.7-0.9: Confident, good evidence
   - 0.5-0.7: Moderate confidence, some uncertainty
   - 0.0-0.5: Low confidence, significant uncertainty
3. **reasoning**: Detailed explanation of your analysis (2-4 paragraphs)
4. **evidence**: List of specific data points that support your conclusion
5. **alternatives_considered**: Other hypotheses you considered and why you rejected them
6. **recommended_actions**: Specific actions to resolve the issue

## Uncertainty Handling

- If confidence < 0.7, explicitly state the limitations and uncertainties
- Always consider multiple hypotheses before settling on one
- Document what additional information would increase confidence
- Be honest about what you don't know

## Output Format

Respond with ONLY a valid JSON object (no markdown, no code blocks) in this exact format:

{
  "category": "migration_misstep|platform_regression|documentation_gap|config_error",
  "confidence": 0.85,
  "reasoning": "Detailed explanation...",
  "evidence": ["Evidence point 1", "Evidence point 2"],
  "alternatives_considered": [
    {"hypothesis": "Alternative explanation", "reason_rejected": "Why it doesn't fit"}
  ],
  "recommended_actions": ["Action 1", "Action 2"]
}
"""


class RootCauseAnalyzer:
    """
    AI-powered root cause analyzer using Claude Sonnet 4.5.
    
    Analyzes signals and patterns to identify the underlying cause of issues
    during e-commerce platform migrations.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the root cause analyzer.
        
        Args:
            api_key: Anthropic API key (uses settings if not provided)
        """
        self.api_key = api_key or settings.anthropic_api_key
        if not self.api_key:
            raise ValueError("Anthropic API key is required")
        
        self.client = AsyncAnthropic(api_key=self.api_key)
        self.model = settings.anthropic_model
        self.max_tokens = settings.anthropic_max_tokens
        self.temperature = 0.3  # Lower temperature for consistent analysis
        
        # Initialize fallback analyzer
        self.fallback_analyzer = RuleBasedRootCauseAnalyzer()
        self.degradation_manager = get_degradation_manager()
        
        logger.info(
            "Root cause analyzer initialized",
            model=self.model,
            max_tokens=self.max_tokens,
        )
    
    @claude_api_circuit_breaker
    async def analyze(
        self,
        signals: list[Signal],
        patterns: list[Pattern],
        merchant_context: Optional[dict] = None,
    ) -> RootCauseAnalysis:
        """
        Analyze signals and patterns to identify root cause.
        
        Args:
            signals: List of signals related to the issue
            patterns: List of detected patterns
            merchant_context: Additional context about the merchant
            
        Returns:
            RootCauseAnalysis: Analysis result with category, confidence, and reasoning
            
        Raises:
            ValueError: If no signals provided
            Exception: If Claude API call fails
        """
        if not signals:
            raise ValueError("At least one signal is required for analysis")
        
        logger.info(
            "Starting root cause analysis",
            signal_count=len(signals),
            pattern_count=len(patterns),
        )
        
        try:
            # Build analysis prompt
            prompt = self._build_analysis_prompt(signals, patterns, merchant_context)
            
            # Call Claude API
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=SYSTEM_PROMPT,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            # Parse response
            analysis = self._parse_analysis(response.content)
            
            # Mark service as not degraded
            self.degradation_manager.set_degraded("claude_api", False)
            
            logger.info(
                "Root cause analysis completed",
                category=analysis.category,
                confidence=analysis.confidence,
            )
            
            return analysis
            
        except Exception as e:
            logger.error(
                "Root cause analysis failed, using fallback",
                error=str(e),
                exc_info=True,
            )
            
            # Mark service as degraded
            self.degradation_manager.set_degraded("claude_api", True)
            
            # Use fallback analyzer
            return await self.fallback_analyzer.analyze(
                signals, patterns, merchant_context
            )
    
    def _build_analysis_prompt(
        self,
        signals: list[Signal],
        patterns: list[Pattern],
        merchant_context: Optional[dict] = None,
    ) -> str:
        """
        Build the analysis prompt for Claude.
        
        Args:
            signals: List of signals
            patterns: List of patterns
            merchant_context: Merchant context
            
        Returns:
            str: Formatted prompt
        """
        prompt_parts = []
        
        # Add merchant context
        if merchant_context:
            prompt_parts.append("## Merchant Context\n")
            prompt_parts.append(f"- Merchant ID: {merchant_context.get('merchant_id', 'unknown')}\n")
            prompt_parts.append(f"- Migration Stage: {merchant_context.get('migration_stage', 'unknown')}\n")
            if merchant_context.get('platform_version'):
                prompt_parts.append(f"- Platform Version: {merchant_context['platform_version']}\n")
            prompt_parts.append("\n")
        
        # Add signals
        prompt_parts.append(f"## Signals ({len(signals)} total)\n\n")
        for i, signal in enumerate(signals[:10], 1):  # Limit to first 10 signals
            prompt_parts.append(f"### Signal {i}\n")
            prompt_parts.append(f"- Source: {signal.source}\n")
            prompt_parts.append(f"- Severity: {signal.severity}\n")
            prompt_parts.append(f"- Timestamp: {signal.timestamp.isoformat()}\n")
            if signal.error_code:
                prompt_parts.append(f"- Error Code: {signal.error_code}\n")
            if signal.error_message:
                prompt_parts.append(f"- Error Message: {signal.error_message}\n")
            if signal.affected_resource:
                prompt_parts.append(f"- Affected Resource: {signal.affected_resource}\n")
            prompt_parts.append("\n")
        
        if len(signals) > 10:
            prompt_parts.append(f"... and {len(signals) - 10} more signals\n\n")
        
        # Add patterns
        if patterns:
            prompt_parts.append(f"## Detected Patterns ({len(patterns)} total)\n\n")
            for i, pattern in enumerate(patterns, 1):
                prompt_parts.append(f"### Pattern {i}\n")
                prompt_parts.append(f"- Type: {pattern.pattern_type}\n")
                prompt_parts.append(f"- Confidence: {pattern.confidence:.2f}\n")
                prompt_parts.append(f"- Frequency: {pattern.frequency}\n")
                prompt_parts.append(f"- Merchants Affected: {len(pattern.merchant_ids)}\n")
                if pattern.characteristics:
                    prompt_parts.append(f"- Characteristics: {json.dumps(pattern.characteristics, indent=2)}\n")
                prompt_parts.append("\n")
        
        # Add analysis instructions
        prompt_parts.append("## Analysis Task\n\n")
        prompt_parts.append("Based on the signals and patterns above, identify the root cause of this issue.\n")
        prompt_parts.append("Provide your analysis in the JSON format specified in the system prompt.\n")
        
        return "".join(prompt_parts)
    
    def _parse_analysis(self, content: list) -> RootCauseAnalysis:
        """
        Parse Claude's response into RootCauseAnalysis.
        
        Args:
            content: Response content from Claude
            
        Returns:
            RootCauseAnalysis: Parsed analysis
            
        Raises:
            ValueError: If response cannot be parsed
        """
        try:
            # Extract text from content blocks
            text = ""
            for block in content:
                if hasattr(block, 'text'):
                    text += block.text
                elif isinstance(block, dict) and 'text' in block:
                    text += block['text']
            
            # Remove markdown code blocks if present
            text = text.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()
            
            # Parse JSON
            data = json.loads(text)
            
            # Create RootCauseAnalysis object
            analysis = RootCauseAnalysis(**data)
            
            return analysis
            
        except json.JSONDecodeError as e:
            logger.error(
                "Failed to parse Claude response as JSON",
                error=str(e),
                content=text[:500],
            )
            raise ValueError(f"Invalid JSON response from Claude: {e}")
        except Exception as e:
            logger.error(
                "Failed to parse Claude response",
                error=str(e),
                exc_info=True,
            )
            raise ValueError(f"Failed to parse analysis: {e}")


# Singleton instance
_analyzer_instance: Optional[RootCauseAnalyzer] = None


async def get_root_cause_analyzer(api_key: Optional[str] = None) -> RootCauseAnalyzer:
    """
    Get or create the root cause analyzer singleton.
    
    Args:
        api_key: Anthropic API key (optional)
        
    Returns:
        RootCauseAnalyzer instance
    """
    global _analyzer_instance
    
    if _analyzer_instance is None:
        _analyzer_instance = RootCauseAnalyzer(api_key=api_key)
    
    return _analyzer_instance
