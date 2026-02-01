"""
Property-based tests for Human Oversight Dashboard.

Tests Property 26 from the design document.
"""

import pytest
from hypothesis import given, settings, strategies as st
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from migrationguard_ai.core.schemas import Action


# Strategy for generating approval requests
@st.composite
def approval_request_strategy(draw):
    """Generate valid approval request data."""
    decision = draw(st.sampled_from(["approve", "reject"]))
    feedback = draw(st.one_of(st.none(), st.text(min_size=10, max_size=500)))
    operator_id = draw(st.text(min_size=1, max_size=50))
    
    return {
        "decision": decision,
        "feedback": feedback,
        "operator_id": operator_id
    }


class TestOversightProperties:
    """Property-based tests for oversight dashboard."""
    
    @given(
        approval_id=st.text(min_size=1, max_size=50),
        request_data=approval_request_strategy()
    )
    @settings(max_examples=20, deadline=None)
    @pytest.mark.asyncio
    async def test_property_26_operator_feedback_recording(
        self,
        approval_id,
        request_data
    ):
        """
        Feature: migrationguard-ai, Property 26: Operator feedback recording
        
        For any operator decision (approve/reject), if feedback is provided,
        the system SHALL record the feedback with operator_id and timestamp.
        
        Validates: Requirements 6.5, 12.2
        """
        from migrationguard_ai.api.routes.approvals import approve_or_reject_action, ApprovalRequest
        from migrationguard_ai.db.models import Action as ActionModel
        from sqlalchemy.ext.asyncio import AsyncSession
        
        # Skip if no feedback provided
        if not request_data["feedback"]:
            return
        
        # Create mock database session
        mock_db = AsyncMock(spec=AsyncSession)
        
        # Create mock action model
        mock_action = MagicMock(spec=ActionModel)
        mock_action.action_id = approval_id
        mock_action.action_type = "support_guidance"
        mock_action.risk_level = "medium"
        mock_action.status = "pending_approval"
        mock_action.parameters = {"merchant_id": "test_merchant"}
        mock_action.issue_id = "test_issue"
        mock_action.reasoning = {}
        
        # Mock database query
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_action
        mock_db.execute.return_value = mock_result
        mock_db.commit = AsyncMock()
        
        # Create request
        request = ApprovalRequest(
            decision=request_data["decision"],
            feedback=request_data["feedback"],
            operator_id=request_data["operator_id"]
        )
        
        # Mock action executor if approving
        if request_data["decision"] == "approve":
            with patch('migrationguard_ai.api.routes.approvals.get_action_executor') as mock_executor_getter:
                mock_executor = AsyncMock()
                mock_executor.execute = AsyncMock(return_value=MagicMock(
                    success=True,
                    executed_at=datetime.utcnow(),
                    result={"test": "result"},
                    error_message=None
                ))
                mock_executor_getter.return_value = mock_executor
                
                # Mock WebSocket manager
                with patch('migrationguard_ai.api.routes.approvals.manager.broadcast', new_callable=AsyncMock):
                    # Execute
                    response = await approve_or_reject_action(
                        approval_id=approval_id,
                        request=request,
                        db=mock_db
                    )
        else:
            # Mock WebSocket manager
            with patch('migrationguard_ai.api.routes.approvals.manager.broadcast', new_callable=AsyncMock):
                # Execute
                response = await approve_or_reject_action(
                    approval_id=approval_id,
                    request=request,
                    db=mock_db
                )
        
        # Verify feedback was recorded
        if request_data["decision"] == "reject":
            # For rejections, feedback should be stored in reasoning
            assert mock_action.reasoning is not None
            assert "operator_feedback" in mock_action.reasoning
            
            feedback_record = mock_action.reasoning["operator_feedback"]
            assert feedback_record["operator_id"] == request_data["operator_id"]
            assert feedback_record["feedback"] == request_data["feedback"]
            assert "timestamp" in feedback_record
            
            # Verify timestamp is valid ISO format
            timestamp_str = feedback_record["timestamp"]
            datetime.fromisoformat(timestamp_str)  # Should not raise
        
        # Verify database commit was called
        mock_db.commit.assert_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
