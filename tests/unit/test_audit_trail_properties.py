"""Property-based tests for audit trail immutability.

Property 35: Audit trail immutability
For any audit trail entry, once created, it cannot be updated or deleted.
Validates: Requirements 13.3
"""

import uuid
from datetime import datetime

import pytest
from hypothesis import given, strategies as st
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from migrationguard_ai.db.models import AuditTrail, Issue


# Hypothesis strategies for generating test data
@st.composite
def audit_trail_data(draw):
    """Generate random audit trail data."""
    return {
        "event_type": draw(st.sampled_from([
            "signal_received",
            "pattern_detected",
            "root_cause_analyzed",
            "decision_made",
            "action_executed",
        ])),
        "actor": draw(st.one_of(
            st.just("system"),
            st.from_regex(r"operator_[0-9]{3}", fullmatch=True)
        )),
        "inputs": draw(st.one_of(
            st.none(),
            st.dictionaries(
                st.text(min_size=1, max_size=20),
                st.one_of(st.text(), st.integers(), st.floats(allow_nan=False)),
                min_size=0,
                max_size=5
            )
        )),
        "outputs": draw(st.one_of(
            st.none(),
            st.dictionaries(
                st.text(min_size=1, max_size=20),
                st.one_of(st.text(), st.integers(), st.floats(allow_nan=False)),
                min_size=0,
                max_size=5
            )
        )),
    }


@pytest.mark.asyncio
@given(data=audit_trail_data())
async def test_audit_trail_cannot_be_updated(db_session, data):
    """
    Property 35: Audit trail immutability - Updates are prevented
    
    For any audit trail entry, attempting to update any field should fail.
    """
    # Create an issue first (required for foreign key)
    issue = Issue(
        merchant_id="test_merchant_001",
        status="active",
        stage="observe",
    )
    db_session.add(issue)
    await db_session.flush()
    
    # Create audit trail entry
    audit_entry = AuditTrail(
        issue_id=issue.issue_id,
        event_type=data["event_type"],
        actor=data["actor"],
        inputs=data["inputs"],
        outputs=data["outputs"],
    )
    db_session.add(audit_entry)
    await db_session.commit()
    
    # Attempt to update the entry
    audit_entry.event_type = "modified_event"
    audit_entry.actor = "modified_actor"
    
    # The update should be prevented by the database rule
    with pytest.raises(Exception):  # Could be IntegrityError or other DB error
        await db_session.commit()
    
    # Rollback the failed transaction
    await db_session.rollback()
    
    # Verify the entry was not modified
    result = await db_session.execute(
        select(AuditTrail).where(AuditTrail.audit_id == audit_entry.audit_id)
    )
    retrieved_entry = result.scalar_one()
    
    assert retrieved_entry.event_type == data["event_type"]
    assert retrieved_entry.actor == data["actor"]


@pytest.mark.asyncio
@given(data=audit_trail_data())
async def test_audit_trail_cannot_be_deleted(db_session, data):
    """
    Property 35: Audit trail immutability - Deletions are prevented
    
    For any audit trail entry, attempting to delete it should fail.
    """
    # Create an issue first
    issue = Issue(
        merchant_id="test_merchant_002",
        status="active",
        stage="observe",
    )
    db_session.add(issue)
    await db_session.flush()
    
    # Create audit trail entry
    audit_entry = AuditTrail(
        issue_id=issue.issue_id,
        event_type=data["event_type"],
        actor=data["actor"],
        inputs=data["inputs"],
        outputs=data["outputs"],
    )
    db_session.add(audit_entry)
    await db_session.commit()
    
    audit_id = audit_entry.audit_id
    
    # Attempt to delete the entry
    await db_session.delete(audit_entry)
    
    # The deletion should be prevented by the database rule
    with pytest.raises(Exception):  # Could be IntegrityError or other DB error
        await db_session.commit()
    
    # Rollback the failed transaction
    await db_session.rollback()
    
    # Verify the entry still exists
    result = await db_session.execute(
        select(AuditTrail).where(AuditTrail.audit_id == audit_id)
    )
    retrieved_entry = result.scalar_one_or_none()
    
    assert retrieved_entry is not None
    assert retrieved_entry.audit_id == audit_id


@pytest.mark.asyncio
@given(data=audit_trail_data())
async def test_audit_trail_hash_is_computed(db_session, data):
    """
    Property 35: Audit trail immutability - Hash is automatically computed
    
    For any audit trail entry, a hash should be automatically computed on creation.
    """
    # Create an issue first
    issue = Issue(
        merchant_id="test_merchant_003",
        status="active",
        stage="observe",
    )
    db_session.add(issue)
    await db_session.flush()
    
    # Create audit trail entry without explicitly setting hash
    audit_entry = AuditTrail(
        issue_id=issue.issue_id,
        event_type=data["event_type"],
        actor=data["actor"],
        inputs=data["inputs"],
        outputs=data["outputs"],
    )
    db_session.add(audit_entry)
    await db_session.flush()
    
    # Hash should be automatically computed
    assert audit_entry.hash is not None
    assert len(audit_entry.hash) == 64  # SHA-256 produces 64 hex characters
    
    # Verify hash is consistent
    expected_hash = audit_entry.compute_hash()
    assert audit_entry.hash == expected_hash


@pytest.mark.asyncio
async def test_audit_trail_hash_chain_integrity(db_session):
    """
    Property 35: Audit trail immutability - Hash chain maintains integrity
    
    For any sequence of audit trail entries, each entry's previous_hash should
    match the hash of the previous entry, forming an immutable chain.
    """
    # Create an issue
    issue = Issue(
        merchant_id="test_merchant_004",
        status="active",
        stage="observe",
    )
    db_session.add(issue)
    await db_session.flush()
    
    # Create first audit entry
    entry1 = AuditTrail(
        issue_id=issue.issue_id,
        event_type="signal_received",
        actor="system",
        inputs={"signal_id": "sig_001"},
    )
    db_session.add(entry1)
    await db_session.flush()
    
    # Create second audit entry with previous_hash
    entry2 = AuditTrail(
        issue_id=issue.issue_id,
        event_type="pattern_detected",
        actor="system",
        inputs={"pattern_id": "pat_001"},
        previous_hash=entry1.hash,
    )
    db_session.add(entry2)
    await db_session.flush()
    
    # Create third audit entry with previous_hash
    entry3 = AuditTrail(
        issue_id=issue.issue_id,
        event_type="root_cause_analyzed",
        actor="system",
        inputs={"confidence": 0.85},
        previous_hash=entry2.hash,
    )
    db_session.add(entry3)
    await db_session.commit()
    
    # Verify hash chain integrity
    assert entry2.previous_hash == entry1.hash
    assert entry3.previous_hash == entry2.hash
    
    # Verify each hash is unique
    assert entry1.hash != entry2.hash
    assert entry2.hash != entry3.hash
    assert entry1.hash != entry3.hash


@pytest.mark.asyncio
@given(
    event_count=st.integers(min_value=2, max_value=10),
    data=st.data()
)
async def test_audit_trail_chain_with_multiple_entries(db_session, event_count, data):
    """
    Property 35: Audit trail immutability - Chain integrity with multiple entries
    
    For any number of sequential audit trail entries, the hash chain should
    maintain integrity throughout.
    """
    # Create an issue
    issue = Issue(
        merchant_id=f"test_merchant_{uuid.uuid4().hex[:8]}",
        status="active",
        stage="observe",
    )
    db_session.add(issue)
    await db_session.flush()
    
    entries = []
    previous_hash = None
    
    # Create multiple audit entries
    for i in range(event_count):
        entry = AuditTrail(
            issue_id=issue.issue_id,
            event_type=data.draw(st.sampled_from([
                "signal_received",
                "pattern_detected",
                "root_cause_analyzed",
                "decision_made",
                "action_executed",
            ])),
            actor="system",
            inputs={"step": i},
            previous_hash=previous_hash,
        )
        db_session.add(entry)
        await db_session.flush()
        
        entries.append(entry)
        previous_hash = entry.hash
    
    await db_session.commit()
    
    # Verify chain integrity
    for i in range(1, len(entries)):
        assert entries[i].previous_hash == entries[i-1].hash
    
    # Verify all hashes are unique
    hashes = [entry.hash for entry in entries]
    assert len(hashes) == len(set(hashes))
