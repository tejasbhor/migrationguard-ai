"""Test Gemini API integration."""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from migrationguard_ai.core.config import get_settings
from migrationguard_ai.core.schemas import Signal
from migrationguard_ai.services.gemini_analyzer import get_gemini_analyzer


async def test_gemini_connection():
    """Test basic Gemini API connection."""
    print("=" * 60)
    print("Testing Gemini API Connection")
    print("=" * 60)
    print()
    
    settings = get_settings()
    
    if not settings.gemini_api_key:
        print("❌ GEMINI_API_KEY not set in .env file")
        print()
        print("To get your free API key:")
        print("1. Visit: https://aistudio.google.com/apikey")
        print("2. Sign in with Google account")
        print("3. Click 'Create API Key'")
        print("4. Copy the key and add to .env file:")
        print("   GEMINI_API_KEY=\"your-key-here\"")
        print()
        return False
    
    print(f"✓ API Key found: {settings.gemini_api_key[:20]}...")
    print(f"✓ Model: {settings.gemini_model}")
    print()
    
    try:
        analyzer = get_gemini_analyzer()
        print("✓ Gemini analyzer initialized")
        print()
        
        # Create test signals
        print("Creating test signals...")
        signals = [
            Signal(
                signal_id="test_1",
                timestamp="2026-02-01T10:00:00Z",
                source="api_failure",
                merchant_id="test_merchant",
                error_code="401",
                error_message="Unauthorized: Invalid API key",
                severity="high",
                context={},
                raw_data={}
            ),
            Signal(
                signal_id="test_2",
                timestamp="2026-02-01T10:01:00Z",
                source="api_failure",
                merchant_id="test_merchant",
                error_code="401",
                error_message="Unauthorized: Token expired",
                severity="high",
                context={},
                raw_data={}
            )
        ]
        print(f"✓ Created {len(signals)} test signals")
        print()
        
        # Test analysis
        print("Calling Gemini API for root cause analysis...")
        print("-" * 60)
        
        analysis = await analyzer.analyze(signals, {})
        
        print()
        print("✅ Gemini API Response:")
        print("-" * 60)
        print(f"Category: {analysis.category}")
        print(f"Confidence: {analysis.confidence:.2f}")
        print(f"Reasoning: {analysis.reasoning}")
        print(f"Evidence: {', '.join(analysis.evidence)}")
        print(f"Recommended Actions:")
        for action in analysis.recommended_actions:
            print(f"  - {action}")
        print()
        
        print("=" * 60)
        print("✅ Gemini API Integration Test PASSED")
        print("=" * 60)
        return True
        
    except Exception as e:
        print()
        print("=" * 60)
        print(f"❌ Gemini API Integration Test FAILED")
        print("=" * 60)
        print(f"Error: {str(e)}")
        print()
        print("Troubleshooting:")
        print("1. Check your API key is correct")
        print("2. Verify you have internet connection")
        print("3. Check rate limits (15 requests/minute for free tier)")
        print("4. Visit https://aistudio.google.com/apikey to verify key")
        print()
        return False


async def main():
    """Run Gemini API tests."""
    success = await test_gemini_connection()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
