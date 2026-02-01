"""
Unit Tests for Prometheus Metrics Exporter.

This module tests the metrics exporter functionality for monitoring
and observability.
"""

import pytest
from prometheus_client import REGISTRY
from migrationguard_ai.services.metrics_exporter import MetricsExporter, get_metrics_exporter


@pytest.fixture(autouse=True)
def clear_prometheus_registry():
    """Clear Prometheus registry before each test to avoid duplicate metrics."""
    # Get list of collectors to remove
    collectors = list(REGISTRY._collector_to_names.keys())
    for collector in collectors:
        try:
            REGISTRY.unregister(collector)
        except Exception:
            pass
    yield
    # Clean up after test
    collectors = list(REGISTRY._collector_to_names.keys())
    for collector in collectors:
        try:
            REGISTRY.unregister(collector)
        except Exception:
            pass


class TestMetricsExporter:
    """Test metrics exporter functionality."""
    
    def test_metrics_exporter_initialization(self):
        """Test that metrics exporter initializes correctly."""
        exporter = MetricsExporter()
        
        assert exporter is not None
        assert exporter.signals_ingested_total is not None
        assert exporter.signal_processing_duration is not None
        assert exporter.decisions_total is not None
    
    def test_record_signal_ingested(self):
        """Test recording signal ingestion."""
        exporter = MetricsExporter()
        
        # Record signal ingestion
        exporter.record_signal_ingested(source="zendesk", severity="high")
        
        # Verify metric was recorded (counter should be > 0)
        metrics = exporter.get_metrics().decode('utf-8')
        assert 'migrationguard_signals_ingested_total' in metrics
    
    def test_record_processing_durations(self):
        """Test recording processing durations."""
        exporter = MetricsExporter()
        
        # Record various durations
        exporter.record_signal_processing_duration(1.5)
        exporter.record_pattern_detection_duration(0.8)
        exporter.record_root_cause_analysis_duration(5.2)
        exporter.record_decision_making_duration(0.3)
        exporter.record_action_execution_duration(2.1)
        
        # Verify metrics were recorded
        metrics = exporter.get_metrics().decode('utf-8')
        assert 'migrationguard_signal_processing_duration_seconds' in metrics
        assert 'migrationguard_pattern_detection_duration_seconds' in metrics
        assert 'migrationguard_root_cause_analysis_duration_seconds' in metrics
        assert 'migrationguard_decision_making_duration_seconds' in metrics
        assert 'migrationguard_action_execution_duration_seconds' in metrics
    
    def test_record_decision(self):
        """Test recording decisions."""
        exporter = MetricsExporter()
        
        # Record decision
        exporter.record_decision(
            action_type="support_guidance",
            risk_level="low",
            requires_approval=False
        )
        
        # Verify metric was recorded
        metrics = exporter.get_metrics().decode('utf-8')
        assert 'migrationguard_decisions_total' in metrics
    
    def test_record_action_executed(self):
        """Test recording action execution."""
        exporter = MetricsExporter()
        
        # Record successful action
        exporter.record_action_executed(action_type="support_guidance", success=True)
        
        # Record failed action
        exporter.record_action_executed(action_type="engineering_escalation", success=False)
        
        # Verify metrics were recorded
        metrics = exporter.get_metrics().decode('utf-8')
        assert 'migrationguard_actions_executed_total' in metrics
    
    def test_record_ticket_metrics(self):
        """Test recording ticket deflection metrics."""
        exporter = MetricsExporter()
        
        # Record tickets
        exporter.record_ticket_received(source="zendesk")
        exporter.record_ticket_deflected(source="zendesk")
        exporter.update_ticket_deflection_rate(0.65)
        exporter.record_ticket_resolution_duration(450.0)
        
        # Verify metrics were recorded
        metrics = exporter.get_metrics().decode('utf-8')
        assert 'migrationguard_tickets_received_total' in metrics
        assert 'migrationguard_tickets_deflected_total' in metrics
        assert 'migrationguard_ticket_deflection_rate' in metrics
        assert 'migrationguard_ticket_resolution_duration_seconds' in metrics
    
    def test_record_confidence_score(self):
        """Test recording confidence scores."""
        exporter = MetricsExporter()
        
        # Record confidence scores
        exporter.record_confidence_score(stage="root_cause", confidence=0.85)
        exporter.record_confidence_score(stage="decision", confidence=0.92)
        
        # Verify metrics were recorded
        metrics = exporter.get_metrics().decode('utf-8')
        assert 'migrationguard_confidence_scores' in metrics
    
    def test_update_confidence_calibration_error(self):
        """Test updating confidence calibration error."""
        exporter = MetricsExporter()
        
        # Update calibration error
        exporter.update_confidence_calibration_error(confidence_bucket="0.8-0.9", error=0.05)
        
        # Verify metric was updated
        metrics = exporter.get_metrics().decode('utf-8')
        assert 'migrationguard_confidence_calibration_error' in metrics
    
    def test_record_approval_metrics(self):
        """Test recording approval metrics."""
        exporter = MetricsExporter()
        
        # Record approval metrics
        exporter.update_approvals_pending(5)
        exporter.record_approval_decision(approved=True)
        exporter.record_approval_decision(approved=False)
        exporter.record_approval_wait_duration(1200.0)
        
        # Verify metrics were recorded
        metrics = exporter.get_metrics().decode('utf-8')
        assert 'migrationguard_approvals_pending' in metrics
        assert 'migrationguard_approvals_total' in metrics
        assert 'migrationguard_approval_wait_duration_seconds' in metrics
    
    def test_record_error(self):
        """Test recording errors."""
        exporter = MetricsExporter()
        
        # Record errors
        exporter.record_error(component="pattern_detector", error_type="timeout")
        exporter.record_error(component="decision_engine", error_type="validation_error")
        
        # Verify metrics were recorded
        metrics = exporter.get_metrics().decode('utf-8')
        assert 'migrationguard_errors_total' in metrics
    
    def test_update_active_issues(self):
        """Test updating active issues count."""
        exporter = MetricsExporter()
        
        # Update active issues
        exporter.update_active_issues(stage="analyze", count=3)
        exporter.update_active_issues(stage="wait_approval", count=2)
        
        # Verify metrics were updated
        metrics = exporter.get_metrics().decode('utf-8')
        assert 'migrationguard_active_issues' in metrics
    
    def test_update_resource_usage(self):
        """Test updating resource usage metrics."""
        exporter = MetricsExporter()
        
        # Update resource usage
        exporter.update_cpu_usage(45.5)
        exporter.update_memory_usage(1024 * 1024 * 512)  # 512 MB
        
        # Verify metrics were updated
        metrics = exporter.get_metrics().decode('utf-8')
        assert 'migrationguard_cpu_usage_percent' in metrics
        assert 'migrationguard_memory_usage_bytes' in metrics
    
    def test_get_metrics_returns_prometheus_format(self):
        """Test that get_metrics returns data in Prometheus format."""
        exporter = MetricsExporter()
        
        # Record some metrics
        exporter.record_signal_ingested(source="zendesk", severity="high")
        exporter.record_decision(action_type="support_guidance", risk_level="low", requires_approval=False)
        
        # Get metrics
        metrics = exporter.get_metrics()
        
        # Verify format
        assert isinstance(metrics, bytes)
        metrics_str = metrics.decode('utf-8')
        
        # Should contain Prometheus format elements
        assert '# HELP' in metrics_str
        assert '# TYPE' in metrics_str
        assert 'migrationguard_' in metrics_str
    
    def test_singleton_pattern(self):
        """Test that get_metrics_exporter returns singleton instance."""
        exporter1 = get_metrics_exporter()
        exporter2 = get_metrics_exporter()
        
        assert exporter1 is exporter2
    
    def test_update_decision_accuracy_rate(self):
        """Test updating decision accuracy rate."""
        exporter = MetricsExporter()
        
        # Update accuracy rate
        exporter.update_decision_accuracy_rate(action_type="support_guidance", rate=0.92)
        
        # Verify metric was updated
        metrics = exporter.get_metrics().decode('utf-8')
        assert 'migrationguard_decision_accuracy_rate' in metrics
    
    def test_update_action_success_rate(self):
        """Test updating action success rate."""
        exporter = MetricsExporter()
        
        # Update success rate
        exporter.update_action_success_rate(action_type="support_guidance", rate=0.95)
        
        # Verify metric was updated
        metrics = exporter.get_metrics().decode('utf-8')
        assert 'migrationguard_action_success_rate' in metrics
    
    def test_update_signal_ingestion_rate(self):
        """Test updating signal ingestion rate."""
        exporter = MetricsExporter()
        
        # Update ingestion rate
        exporter.update_signal_ingestion_rate(8500.0)
        
        # Verify metric was updated
        metrics = exporter.get_metrics().decode('utf-8')
        assert 'migrationguard_signal_ingestion_rate' in metrics
