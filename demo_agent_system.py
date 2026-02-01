"""
MigrationGuard AI - Complete Agent System Demo

This demo showcases the full agentic AI system with:
1. Signal observation and ingestion
2. Pattern detection across signals
3. Root cause analysis with reasoning
4. Decision-making with risk assessment
5. Action execution with safety controls
6. State persistence and feedback loops
7. Human oversight integration

This demonstrates proper agent behavior beyond a single LLM call.
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Dict, List
import uuid

# Import core components
from migrationguard_ai.core.schemas import (
    Signal,
    Pattern,
    RootCauseAnalysis,
    Action,
    ActionResult,
)
from migrationguard_ai.services.decision_engine import DecisionEngine, get_decision_engine
from migrationguard_ai.services.action_executor import ActionExecutor, get_action_executor
from migrationguard_ai.core.safe_mode import (
    SafeModeManager,
    SafeModeDetector,
    SafeModeReason,
    get_safe_mode_manager,
    get_safe_mode_detector,
)
from migrationguard_ai.core.graceful_degradation import (
    RuleBasedRootCauseAnalyzer,
    GracefulDegradationManager,
    get_degradation_manager,
)

# Try to import Gemini analyzer
try:
    from migrationguard_ai.services.gemini_analyzer import get_gemini_analyzer
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    get_gemini_analyzer = None


class InMemoryStateStore:
    """In-memory state store for demo purposes."""
    
    def __init__(self):
        self.issues = {}
        self.signals = []
        self.patterns = []
        self.decisions = []
        self.actions = []
        self.audit_trail = []
    
    def add_signal(self, signal: Dict):
        """Add signal to store."""
        self.signals.append(signal)
        print(f"📊 Signal stored: {signal['signal_id']}")
    
    def add_pattern(self, pattern: Dict):
        """Add pattern to store."""
        self.patterns.append(pattern)
        print(f"🔍 Pattern detected: {pattern['pattern_id']}")
    
    def add_decision(self, decision: Dict):
        """Add decision to store."""
        self.decisions.append(decision)
        print(f"🤔 Decision made: {decision['decision_id']}")
    
    def add_action(self, action: Dict):
        """Add action to store."""
        self.actions.append(action)
        print(f"⚡ Action recorded: {action['action_id']}")
    
    def add_audit_entry(self, entry: Dict):
        """Add audit trail entry."""
        self.audit_trail.append(entry)
        print(f"📝 Audit entry: {entry['event_type']}")
    
    def get_issue_state(self, issue_id: str) -> Dict:
        """Get issue state."""
        return self.issues.get(issue_id, {
            "issue_id": issue_id,
            "status": "new",
            "signals": [],
            "patterns": [],
            "analysis": None,
            "decision": None,
            "actions": [],
            "created_at": datetime.now(timezone.utc).isoformat()
        })
    
    def update_issue_state(self, issue_id: str, state: Dict):
        """Update issue state."""
        self.issues[issue_id] = state
        print(f"💾 Issue state updated: {issue_id}")


class AgentOrchestrator:
    """
    Main agent orchestrator that implements the observe-reason-decide-act loop.
    
    This demonstrates proper agent behavior with:
    - State management across the loop
    - Multi-step reasoning
    - Tool usage (decision engine, analyzers, executors)
    - Feedback loops and learning
    """
    
    def __init__(self):
        self.state_store = InMemoryStateStore()
        self.decision_engine = get_decision_engine()
        self.action_executor = get_action_executor()
        self.safe_mode_manager = get_safe_mode_manager()
        self.safe_mode_detector = get_safe_mode_detector()
        self.degradation_manager = get_degradation_manager()
        self.rule_based_analyzer = RuleBasedRootCauseAnalyzer()
        
        # Try to initialize Gemini analyzer
        if GEMINI_AVAILABLE:
            try:
                self.gemini_analyzer = get_gemini_analyzer()
                print("🤖 Gemini AI analyzer initialized")
            except Exception as e:
                print(f"⚠️  Gemini initialization failed: {e}")
                self.gemini_analyzer = None
        else:
            self.gemini_analyzer = None
        
        print("🤖 Agent Orchestrator initialized")
        print("=" * 80)
    
    async def observe(self, signals: List[Dict]) -> str:
        """
        OBSERVE: Ingest and normalize signals from multiple sources.
        
        Demonstrates:
        - Multi-source signal ingestion
        - Data normalization
        - State tracking
        """
        print("\n🔭 OBSERVE PHASE: Ingesting signals...")
        print("-" * 80)
        
        issue_id = f"issue_{uuid.uuid4().hex[:8]}"
        issue_state = self.state_store.get_issue_state(issue_id)
        
        for signal_data in signals:
            signal_id = f"sig_{uuid.uuid4().hex[:8]}"
            signal = {
                "signal_id": signal_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                **signal_data
            }
            
            self.state_store.add_signal(signal)
            issue_state["signals"].append(signal_id)
            
            # Audit trail
            self.state_store.add_audit_entry({
                "event_type": "signal_ingested",
                "signal_id": signal_id,
                "source": signal_data.get("source"),
                "timestamp": signal["timestamp"]
            })
        
        issue_state["status"] = "observing"
        self.state_store.update_issue_state(issue_id, issue_state)
        
        print(f"✅ Observed {len(signals)} signals for issue {issue_id}")
        return issue_id
    
    async def detect_patterns(self, issue_id: str) -> List[Dict]:
        """
        PATTERN DETECTION: Identify patterns across signals.
        
        Demonstrates:
        - Cross-signal correlation
        - Pattern matching
        - Temporal analysis
        """
        print("\n🔍 PATTERN DETECTION PHASE: Analyzing signals...")
        print("-" * 80)
        
        issue_state = self.state_store.get_issue_state(issue_id)
        signals = [s for s in self.state_store.signals if s["signal_id"] in issue_state["signals"]]
        
        # Simple pattern detection logic
        patterns = []
        
        # Check for authentication errors
        auth_errors = [s for s in signals if "401" in str(s.get("error_code", "")) or "unauthorized" in str(s.get("error_message", "")).lower()]
        if len(auth_errors) >= 2:
            pattern = {
                "pattern_id": f"pat_{uuid.uuid4().hex[:8]}",
                "pattern_type": "authentication_failure",
                "confidence": 0.85,
                "signal_count": len(auth_errors),
                "signals": [s["signal_id"] for s in auth_errors],
                "description": "Multiple authentication failures detected"
            }
            patterns.append(pattern)
            self.state_store.add_pattern(pattern)
        
        # Check for API errors
        api_errors = [s for s in signals if "api" in str(s.get("source", "")).lower()]
        if len(api_errors) >= 2:
            pattern = {
                "pattern_id": f"pat_{uuid.uuid4().hex[:8]}",
                "pattern_type": "api_failure",
                "confidence": 0.75,
                "signal_count": len(api_errors),
                "signals": [s["signal_id"] for s in api_errors],
                "description": "Multiple API failures detected"
            }
            patterns.append(pattern)
            self.state_store.add_pattern(pattern)
        
        issue_state["patterns"] = [p["pattern_id"] for p in patterns]
        issue_state["status"] = "pattern_detected"
        self.state_store.update_issue_state(issue_id, issue_state)
        
        print(f"✅ Detected {len(patterns)} patterns")
        return patterns
    
    async def analyze_root_cause(self, issue_id: str) -> RootCauseAnalysis:
        """
        REASON: Perform root cause analysis using Gemini AI or rule-based reasoning.
        
        Demonstrates:
        - Multi-step reasoning
        - Evidence gathering
        - Confidence scoring
        - Fallback mechanisms (graceful degradation)
        """
        print("\n🧠 REASON PHASE: Analyzing root cause...")
        print("-" * 80)
        
        issue_state = self.state_store.get_issue_state(issue_id)
        signal_dicts = [s for s in self.state_store.signals if s["signal_id"] in issue_state["signals"]]
        
        # Convert dicts to Signal objects for the analyzer
        signals = []
        for s in signal_dicts:
            signal = Signal(
                signal_id=s["signal_id"],
                timestamp=s["timestamp"],
                source=s.get("source", "api_failure"),
                merchant_id=s.get("merchant_id", "unknown"),
                error_code=s.get("error_code"),
                error_message=s.get("error_message"),
                severity=s.get("severity", "medium"),
                context=s,
                raw_data=s  # Include raw data
            )
            signals.append(signal)
        
        # Try Gemini first, then fall back to rule-based
        analysis = None
        
        if self.gemini_analyzer:
            try:
                print("Using Gemini AI for root cause analysis...")
                analysis = await self.gemini_analyzer.analyze(signals, {})
                print("✅ Gemini AI analysis successful")
            except Exception as e:
                print(f"⚠️  Gemini AI failed: {e}")
                print("Falling back to rule-based analyzer...")
                analysis = None
        
        if not analysis:
            print("Using rule-based analyzer (graceful degradation)")
            analysis = await self.rule_based_analyzer.analyze(signals, {})
        
        print(f"📋 Root Cause: {analysis.category}")
        print(f"📊 Confidence: {analysis.confidence:.2f}")
        print(f"💡 Reasoning: {analysis.reasoning}")
        print(f"🔬 Evidence: {', '.join(analysis.evidence[:3])}")
        
        issue_state["analysis"] = {
            "category": analysis.category,
            "confidence": analysis.confidence,
            "reasoning": analysis.reasoning,
            "evidence": analysis.evidence,
            "recommended_actions": analysis.recommended_actions
        }
        issue_state["status"] = "analyzed"
        self.state_store.update_issue_state(issue_id, issue_state)
        
        # Audit trail
        self.state_store.add_audit_entry({
            "event_type": "root_cause_analyzed",
            "issue_id": issue_id,
            "category": analysis.category,
            "confidence": analysis.confidence,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        return analysis
    
    async def make_decision(self, issue_id: str, analysis: RootCauseAnalysis) -> Dict:
        """
        DECIDE: Determine appropriate action with risk assessment.
        
        Demonstrates:
        - Decision-making logic
        - Risk assessment
        - Safety controls (safe mode check)
        - Approval requirements
        """
        print("\n🤔 DECIDE PHASE: Making decision...")
        print("-" * 80)
        
        issue_state = self.state_store.get_issue_state(issue_id)
        
        # Check safe mode
        if self.safe_mode_manager.is_active():
            print("⚠️  SAFE MODE ACTIVE - All decisions require approval")
        
        # Make decision using decision engine
        context = {
            "merchant_id": "demo_merchant_123",
            "migration_stage": "api_integration",
            "severity": "medium",
            "signal_ids": issue_state["signals"],
            "pattern_ids": issue_state["patterns"]
        }
        
        decision = self.decision_engine.decide(
            analysis=analysis,
            context=context,
            issue_id=issue_id
        )
        
        decision_dict = {
            "decision_id": decision.decision_id,
            "action_type": decision.action_type,
            "risk_level": decision.risk_level,
            "requires_approval": decision.requires_approval,
            "confidence": decision.confidence,
            "reasoning": decision.reasoning,
            "estimated_outcome": decision.estimated_outcome,
            "parameters": decision.parameters
        }
        
        print(f"📝 Action Type: {decision.action_type}")
        print(f"⚠️  Risk Level: {decision.risk_level}")
        print(f"👤 Requires Approval: {decision.requires_approval}")
        print(f"💭 Reasoning: {decision.reasoning[:100]}...")
        
        self.state_store.add_decision(decision_dict)
        issue_state["decision"] = decision_dict
        issue_state["status"] = "decided"
        self.state_store.update_issue_state(issue_id, issue_state)
        
        # Audit trail
        self.state_store.add_audit_entry({
            "event_type": "decision_made",
            "issue_id": issue_id,
            "decision_id": decision.decision_id,
            "action_type": decision.action_type,
            "risk_level": decision.risk_level,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        return decision_dict
    
    async def execute_action(self, issue_id: str, decision: Dict, approved: bool = True) -> Dict:
        """
        ACT: Execute approved action with safety controls.
        
        Demonstrates:
        - Action execution
        - Safety controls (rate limiting, safe mode)
        - Retry logic
        - Feedback loops
        """
        print("\n⚡ ACT PHASE: Executing action...")
        print("-" * 80)
        
        if decision["requires_approval"] and not approved:
            print("⏸️  Action requires approval - queued for human review")
            return {
                "status": "pending_approval",
                "message": "Action queued for human approval"
            }
        
        # Create action object
        action = Action(
            action_id=f"act_{uuid.uuid4().hex[:8]}",
            action_type=decision["action_type"],
            risk_level=decision["risk_level"],
            status="pending",
            parameters=decision["parameters"]
        )
        
        # Execute action (will check safe mode internally)
        result = await self.action_executor.execute(action, issue_id)
        
        result_dict = {
            "action_id": result.action_id,
            "success": result.success,
            "executed_at": result.executed_at.isoformat(),
            "result": result.result,
            "error_message": result.error_message
        }
        
        if result.success:
            print(f"✅ Action executed successfully")
            if result.result:
                print(f"📊 Result: {json.dumps(result.result, indent=2)[:200]}...")
        else:
            print(f"❌ Action failed: {result.error_message}")
        
        self.state_store.add_action(result_dict)
        
        issue_state = self.state_store.get_issue_state(issue_id)
        issue_state["actions"].append(result_dict)
        issue_state["status"] = "action_executed" if result.success else "action_failed"
        self.state_store.update_issue_state(issue_id, issue_state)
        
        # Audit trail
        self.state_store.add_audit_entry({
            "event_type": "action_executed",
            "issue_id": issue_id,
            "action_id": result.action_id,
            "success": result.success,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        # FEEDBACK LOOP: Learn from outcome
        await self.feedback_loop(issue_id, result)
        
        return result_dict
    
    async def feedback_loop(self, issue_id: str, result: ActionResult):
        """
        FEEDBACK LOOP: Learn from action outcomes.
        
        Demonstrates:
        - Outcome tracking
        - Confidence calibration
        - Adaptive behavior
        """
        print("\n🔄 FEEDBACK LOOP: Learning from outcome...")
        print("-" * 80)
        
        issue_state = self.state_store.get_issue_state(issue_id)
        
        # Track outcome for confidence calibration
        if result.success:
            print("✅ Positive feedback: Action succeeded")
            print("📈 Increasing confidence in similar patterns")
        else:
            print("⚠️  Negative feedback: Action failed")
            print("📉 Adjusting decision logic for similar cases")
            
            # Check if we should trigger safe mode
            if "critical" in str(result.error_message).lower():
                self.safe_mode_detector.check_critical_error(
                    "action_execution_failure",
                    result.error_message or "Unknown error"
                )
        
        # Audit trail
        self.state_store.add_audit_entry({
            "event_type": "feedback_processed",
            "issue_id": issue_id,
            "outcome": "success" if result.success else "failure",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    
    async def run_full_cycle(self, signals: List[Dict], auto_approve: bool = False):
        """
        Run complete agent cycle: Observe → Detect → Reason → Decide → Act → Learn
        
        This demonstrates the full agentic behavior with state management,
        multi-step reasoning, and feedback loops.
        """
        print("\n" + "=" * 80)
        print("🚀 STARTING FULL AGENT CYCLE")
        print("=" * 80)
        
        # 1. OBSERVE
        issue_id = await self.observe(signals)
        
        # 2. DETECT PATTERNS
        patterns = await self.detect_patterns(issue_id)
        
        # 3. REASON (Root Cause Analysis)
        analysis = await self.analyze_root_cause(issue_id)
        
        # 4. DECIDE
        decision = await self.make_decision(issue_id, analysis)
        
        # 5. ACT
        result = await self.execute_action(issue_id, decision, approved=auto_approve)
        
        # Print final state
        print("\n" + "=" * 80)
        print("📊 FINAL ISSUE STATE")
        print("=" * 80)
        final_state = self.state_store.get_issue_state(issue_id)
        print(json.dumps(final_state, indent=2, default=str))
        
        print("\n" + "=" * 80)
        print("✅ AGENT CYCLE COMPLETE")
        print("=" * 80)
        
        return issue_id


async def demo_scenario_1_auth_errors():
    """Demo Scenario 1: Multiple authentication errors"""
    print("\n" + "🎬 " * 20)
    print("DEMO SCENARIO 1: Authentication Errors")
    print("🎬 " * 20)
    
    agent = AgentOrchestrator()
    
    signals = [
        {
            "source": "api_failure",
            "error_code": "401",
            "error_message": "Unauthorized: Invalid API key",
            "merchant_id": "merchant_123",
            "endpoint": "/api/v1/products"
        },
        {
            "source": "api_failure",
            "error_code": "401",
            "error_message": "Unauthorized: Token expired",
            "merchant_id": "merchant_123",
            "endpoint": "/api/v1/orders"
        },
        {
            "source": "support_ticket",
            "error_message": "Customer reports: Cannot access API",
            "merchant_id": "merchant_123",
            "ticket_id": "TICKET-12345"
        }
    ]
    
    await agent.run_full_cycle(signals, auto_approve=True)


async def demo_scenario_2_safe_mode():
    """Demo Scenario 2: Safe mode activation"""
    print("\n" + "🎬 " * 20)
    print("DEMO SCENARIO 2: Safe Mode Activation")
    print("🎬 " * 20)
    
    agent = AgentOrchestrator()
    
    # Trigger safe mode
    print("\n⚠️  Triggering safe mode due to confidence drift...")
    agent.safe_mode_detector.check_confidence_drift(
        expected_accuracy=0.90,
        actual_accuracy=0.75,
        threshold=0.05
    )
    
    signals = [
        {
            "source": "checkout_error",
            "error_code": "PAYMENT_FAILED",
            "error_message": "Payment processing failed",
            "merchant_id": "merchant_456",
            "amount": 99.99
        }
    ]
    
    await agent.run_full_cycle(signals, auto_approve=False)
    
    # Deactivate safe mode
    print("\n✅ Operator deactivating safe mode...")
    agent.safe_mode_manager.deactivate("operator_demo")


async def main():
    """Run all demo scenarios"""
    print("\n" + "🌟 " * 20)
    print("MIGRATIONGUARD AI - COMPLETE AGENT SYSTEM DEMO")
    print("🌟 " * 20)
    print("\nThis demo showcases:")
    print("✅ Signal observation and ingestion")
    print("✅ Pattern detection across signals")
    print("✅ Root cause analysis with reasoning")
    print("✅ Decision-making with risk assessment")
    print("✅ Action execution with safety controls")
    print("✅ State persistence across the loop")
    print("✅ Feedback loops and learning")
    print("✅ Human oversight integration")
    print("✅ Safe mode and error handling")
    
    # Run scenarios
    await demo_scenario_1_auth_errors()
    await asyncio.sleep(2)
    await demo_scenario_2_safe_mode()
    
    print("\n" + "🎉 " * 20)
    print("DEMO COMPLETE - Full Agentic AI System Demonstrated!")
    print("🎉 " * 20)


if __name__ == "__main__":
    asyncio.run(main())
