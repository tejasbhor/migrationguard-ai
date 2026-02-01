"""Root cause analyzer using Google Gemini API."""

import json
from typing import Dict, List

from google import genai

from migrationguard_ai.core.schemas import RootCauseAnalysis, Signal
from migrationguard_ai.core.config import get_settings


class GeminiRootCauseAnalyzer:
    """Root cause analyzer using Google Gemini API."""
    
    def __init__(self, api_key: str = None):
        """Initialize Gemini analyzer.
        
        Args:
            api_key: Google AI Studio API key. If not provided, will use GEMINI_API_KEY env var.
        """
        settings = get_settings()
        self.api_key = api_key or settings.gemini_api_key
        
        if self.api_key:
            self.client = genai.Client(api_key=self.api_key)
            self.model = settings.gemini_model or "gemini-2.5-flash"  # Stable model as of Feb 2026
        else:
            self.client = None
            self.model = None
    
    async def analyze(self, signals: List[Signal], context: Dict) -> RootCauseAnalysis:
        """Analyze signals to determine root cause.
        
        Args:
            signals: List of signals to analyze
            context: Additional context for analysis
            
        Returns:
            RootCauseAnalysis with category, confidence, reasoning, and recommendations
        """
        if not self.client:
            raise ValueError("Gemini API key not configured")
        
        # Prepare signal data for analysis
        signal_data = []
        for signal in signals:
            signal_data.append({
                "source": signal.source,
                "error_code": signal.error_code,
                "error_message": signal.error_message,
                "severity": signal.severity,
                "merchant_id": signal.merchant_id,
                "timestamp": signal.timestamp
            })
        
        # Create prompt for Gemini
        prompt = self._create_analysis_prompt(signal_data, context)
        
        # Call Gemini API
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt
            )
            
            # Parse response
            analysis_text = response.text
            
            # Extract structured data from response
            analysis = self._parse_analysis_response(analysis_text, signals)
            
            return analysis
            
        except Exception as e:
            # If Gemini fails, raise error so fallback can be used
            raise RuntimeError(f"Gemini API error: {str(e)}")
    
    def _create_analysis_prompt(self, signal_data: List[Dict], context: Dict) -> str:
        """Create analysis prompt for Gemini.
        
        Args:
            signal_data: List of signal dictionaries
            context: Additional context
            
        Returns:
            Formatted prompt string
        """
        prompt = """You are an expert system analyzing e-commerce platform migration issues.

Analyze the following signals and provide a root cause analysis:

SIGNALS:
"""
        for i, signal in enumerate(signal_data, 1):
            prompt += f"\nSignal {i}:\n"
            prompt += f"  Source: {signal['source']}\n"
            prompt += f"  Error Code: {signal.get('error_code', 'N/A')}\n"
            prompt += f"  Error Message: {signal.get('error_message', 'N/A')}\n"
            prompt += f"  Severity: {signal['severity']}\n"
            prompt += f"  Merchant: {signal['merchant_id']}\n"
        
        if context:
            prompt += f"\nCONTEXT:\n{json.dumps(context, indent=2)}\n"
        
        prompt += """
Please provide a root cause analysis in the following JSON format:

{
  "category": "<one of: migration_misstep, platform_regression, documentation_gap, config_error>",
  "confidence": <float between 0.0 and 1.0>,
  "reasoning": "<detailed explanation of the root cause>",
  "evidence": ["<evidence point 1>", "<evidence point 2>", ...],
  "alternatives_considered": [{"hypothesis": "<alternative 1>", "confidence": <float>, "rejected_reason": "<reason>"}],
  "recommended_actions": ["<action 1>", "<action 2>", ...]
}

Category definitions:
- migration_misstep: Issues caused by incomplete or incorrect migration steps
- platform_regression: New bugs or issues in the platform itself
- documentation_gap: Issues caused by unclear or missing documentation
- config_error: Configuration problems (API keys, webhooks, settings, etc.)

Focus on:
1. Identifying patterns across signals
2. Determining the most likely root cause
3. Providing actionable recommendations
4. Assigning appropriate confidence based on evidence strength

Respond ONLY with the JSON object, no additional text.
"""
        return prompt
    
    def _parse_analysis_response(self, response_text: str, signals: List[Signal]) -> RootCauseAnalysis:
        """Parse Gemini response into RootCauseAnalysis.
        
        Args:
            response_text: Raw response from Gemini
            signals: Original signals for reference
            
        Returns:
            RootCauseAnalysis object
        """
        try:
            # Try to extract JSON from response
            # Gemini might wrap JSON in markdown code blocks
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                json_text = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                json_text = response_text[json_start:json_end].strip()
            else:
                json_text = response_text.strip()
            
            # Parse JSON
            data = json.loads(json_text)
            
            # Create RootCauseAnalysis object
            return RootCauseAnalysis(
                category=data.get("category", "config_error"),
                confidence=float(data.get("confidence", 0.5)),
                reasoning=data.get("reasoning", "Analysis completed"),
                evidence=data.get("evidence", []),
                alternatives_considered=data.get("alternatives_considered", []),
                recommended_actions=data.get("recommended_actions", [])
            )
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            # If parsing fails, create a basic analysis
            return RootCauseAnalysis(
                category="config_error",
                confidence=0.5,
                reasoning=f"Unable to parse Gemini response: {str(e)}. Raw response: {response_text[:200]}",
                evidence=["Gemini API returned unparseable response"],
                alternatives_considered=[],
                recommended_actions=["Review signals manually", "Check Gemini API configuration"]
            )


def get_gemini_analyzer(api_key: str = None) -> GeminiRootCauseAnalyzer:
    """Get Gemini root cause analyzer instance.
    
    Args:
        api_key: Optional API key override
        
    Returns:
        GeminiRootCauseAnalyzer instance
    """
    return GeminiRootCauseAnalyzer(api_key=api_key)
