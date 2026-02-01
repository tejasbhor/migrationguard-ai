"""
Prometheus Metrics Exporter for MigrationGuard AI.

This module implements Prometheus metrics collection and export for monitoring
system performance, decision accuracy, and operational metrics.
"""

from prometheus_client import Counter, Histogram, Gauge, Info, generate_latest, REGISTRY
from typing import Optional
import time


class MetricsExporter:
    """
    Prometheus metrics exporter for MigrationGuard AI.
    
    Tracks:
    - Signal ingestion rate
    - Processing latency
    - Decision accuracy
    - Action success rate
    - Ticket deflection metrics
    - Confidence calibration
    """
    
    def __init__(self):
        """Initialize Prometheus metrics."""
        
        # System info
        self.system_info = Info(
            'migrationguard_system',
            'MigrationGuard AI system information'
        )
        self.system_info.info({
            'version': '1.0.0',
            'component': 'migrationguard-ai'
        })
        
        # Signal ingestion metrics
        self.signals_ingested_total = Counter(
            'migrationguard_signals_ingested_total',
            'Total number of signals ingested',
            ['source', 'severity']
        )
        
        self.signal_ingestion_rate = Gauge(
            'migrationguard_signal_ingestion_rate',
            'Current signal ingestion rate (signals per minute)'
        )
        
        # Processing latency metrics
        self.signal_processing_duration = Histogram(
            'migrationguard_signal_processing_duration_seconds',
            'Time to process a signal through the agent loop',
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0]
        )
        
        self.pattern_detection_duration = Histogram(
            'migrationguard_pattern_detection_duration_seconds',
            'Time to detect patterns',
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
        )
        
        self.root_cause_analysis_duration = Histogram(
            'migrationguard_root_cause_analysis_duration_seconds',
            'Time to perform root cause analysis',
            buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
        )
        
        self.decision_making_duration = Histogram(
            'migrationguard_decision_making_duration_seconds',
            'Time to make a decision',
            buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0]
        )
        
        self.action_execution_duration = Histogram(
            'migrationguard_action_execution_duration_seconds',
            'Time to execute an action',
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
        )
        
        # Decision accuracy metrics
        self.decisions_total = Counter(
            'migrationguard_decisions_total',
            'Total number of decisions made',
            ['action_type', 'risk_level', 'requires_approval']
        )
        
        self.decisions_accurate = Counter(
            'migrationguard_decisions_accurate_total',
            'Number of accurate decisions (validated by human feedback)',
            ['action_type']
        )
        
        self.decision_accuracy_rate = Gauge(
            'migrationguard_decision_accuracy_rate',
            'Current decision accuracy rate (0-1)',
            ['action_type']
        )
        
        # Action execution metrics
        self.actions_executed_total = Counter(
            'migrationguard_actions_executed_total',
            'Total number of actions executed',
            ['action_type', 'status']
        )
        
        self.action_success_rate = Gauge(
            'migrationguard_action_success_rate',
            'Current action success rate (0-1)',
            ['action_type']
        )
        
        # Ticket deflection metrics
        self.tickets_received_total = Counter(
            'migrationguard_tickets_received_total',
            'Total number of tickets received',
            ['source']
        )
        
        self.tickets_deflected_total = Counter(
            'migrationguard_tickets_deflected_total',
            'Total number of tickets deflected (auto-resolved)',
            ['source']
        )
        
        self.ticket_deflection_rate = Gauge(
            'migrationguard_ticket_deflection_rate',
            'Current ticket deflection rate (0-1)'
        )
        
        self.ticket_resolution_duration = Histogram(
            'migrationguard_ticket_resolution_duration_seconds',
            'Time to resolve a ticket',
            buckets=[60, 300, 600, 900, 1800, 3600]  # 1min to 1hour
        )
        
        # Confidence calibration metrics
        self.confidence_scores = Histogram(
            'migrationguard_confidence_scores',
            'Distribution of confidence scores',
            ['stage'],
            buckets=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
        )
        
        self.confidence_calibration_error = Gauge(
            'migrationguard_confidence_calibration_error',
            'Confidence calibration error (difference between predicted and actual accuracy)',
            ['confidence_bucket']
        )
        
        # Human oversight metrics
        self.approvals_pending = Gauge(
            'migrationguard_approvals_pending',
            'Number of actions pending approval'
        )
        
        self.approvals_total = Counter(
            'migrationguard_approvals_total',
            'Total number of approval decisions',
            ['decision']  # approved, rejected
        )
        
        self.approval_wait_duration = Histogram(
            'migrationguard_approval_wait_duration_seconds',
            'Time waiting for human approval',
            buckets=[60, 300, 600, 1800, 3600, 7200, 14400]  # 1min to 4hours
        )
        
        # Error metrics
        self.errors_total = Counter(
            'migrationguard_errors_total',
            'Total number of errors',
            ['component', 'error_type']
        )
        
        # Active issues
        self.active_issues = Gauge(
            'migrationguard_active_issues',
            'Number of currently active issues',
            ['stage']
        )
        
        # Resource usage (will be updated by external monitoring)
        self.cpu_usage = Gauge(
            'migrationguard_cpu_usage_percent',
            'CPU usage percentage'
        )
        
        self.memory_usage = Gauge(
            'migrationguard_memory_usage_bytes',
            'Memory usage in bytes'
        )
    
    # Signal ingestion methods
    
    def record_signal_ingested(self, source: str, severity: str):
        """Record a signal ingestion event."""
        self.signals_ingested_total.labels(source=source, severity=severity).inc()
    
    def update_signal_ingestion_rate(self, rate: float):
        """Update the current signal ingestion rate."""
        self.signal_ingestion_rate.set(rate)
    
    # Processing latency methods
    
    def record_signal_processing_duration(self, duration: float):
        """Record signal processing duration in seconds."""
        self.signal_processing_duration.observe(duration)
    
    def record_pattern_detection_duration(self, duration: float):
        """Record pattern detection duration in seconds."""
        self.pattern_detection_duration.observe(duration)
    
    def record_root_cause_analysis_duration(self, duration: float):
        """Record root cause analysis duration in seconds."""
        self.root_cause_analysis_duration.observe(duration)
    
    def record_decision_making_duration(self, duration: float):
        """Record decision making duration in seconds."""
        self.decision_making_duration.observe(duration)
    
    def record_action_execution_duration(self, duration: float):
        """Record action execution duration in seconds."""
        self.action_execution_duration.observe(duration)
    
    # Decision accuracy methods
    
    def record_decision(self, action_type: str, risk_level: str, requires_approval: bool):
        """Record a decision made by the system."""
        self.decisions_total.labels(
            action_type=action_type,
            risk_level=risk_level,
            requires_approval=str(requires_approval)
        ).inc()
    
    def record_decision_accuracy(self, action_type: str, accurate: bool):
        """Record decision accuracy feedback."""
        if accurate:
            self.decisions_accurate.labels(action_type=action_type).inc()
    
    def update_decision_accuracy_rate(self, action_type: str, rate: float):
        """Update decision accuracy rate for an action type."""
        self.decision_accuracy_rate.labels(action_type=action_type).set(rate)
    
    # Action execution methods
    
    def record_action_executed(self, action_type: str, success: bool):
        """Record an action execution."""
        status = "success" if success else "failure"
        self.actions_executed_total.labels(action_type=action_type, status=status).inc()
    
    def update_action_success_rate(self, action_type: str, rate: float):
        """Update action success rate for an action type."""
        self.action_success_rate.labels(action_type=action_type).set(rate)
    
    # Ticket deflection methods
    
    def record_ticket_received(self, source: str):
        """Record a ticket received."""
        self.tickets_received_total.labels(source=source).inc()
    
    def record_ticket_deflected(self, source: str):
        """Record a ticket deflected (auto-resolved)."""
        self.tickets_deflected_total.labels(source=source).inc()
    
    def update_ticket_deflection_rate(self, rate: float):
        """Update the current ticket deflection rate."""
        self.ticket_deflection_rate.set(rate)
    
    def record_ticket_resolution_duration(self, duration: float):
        """Record ticket resolution duration in seconds."""
        self.ticket_resolution_duration.observe(duration)
    
    # Confidence calibration methods
    
    def record_confidence_score(self, stage: str, confidence: float):
        """Record a confidence score."""
        self.confidence_scores.labels(stage=stage).observe(confidence)
    
    def update_confidence_calibration_error(self, confidence_bucket: str, error: float):
        """Update confidence calibration error for a bucket."""
        self.confidence_calibration_error.labels(confidence_bucket=confidence_bucket).set(error)
    
    # Human oversight methods
    
    def update_approvals_pending(self, count: int):
        """Update the number of pending approvals."""
        self.approvals_pending.set(count)
    
    def record_approval_decision(self, approved: bool):
        """Record an approval decision."""
        decision = "approved" if approved else "rejected"
        self.approvals_total.labels(decision=decision).inc()
    
    def record_approval_wait_duration(self, duration: float):
        """Record approval wait duration in seconds."""
        self.approval_wait_duration.observe(duration)
    
    # Error tracking methods
    
    def record_error(self, component: str, error_type: str):
        """Record an error occurrence."""
        self.errors_total.labels(component=component, error_type=error_type).inc()
    
    # Active issues methods
    
    def update_active_issues(self, stage: str, count: int):
        """Update the number of active issues in a stage."""
        self.active_issues.labels(stage=stage).set(count)
    
    # Resource usage methods
    
    def update_cpu_usage(self, percent: float):
        """Update CPU usage percentage."""
        self.cpu_usage.set(percent)
    
    def update_memory_usage(self, bytes_used: int):
        """Update memory usage in bytes."""
        self.memory_usage.set(bytes_used)
    
    # Export methods
    
    def get_metrics(self) -> bytes:
        """
        Get metrics in Prometheus format.
        
        Returns:
            Metrics in Prometheus text format
        """
        return generate_latest(REGISTRY)


# Singleton instance
_metrics_exporter_instance: Optional[MetricsExporter] = None


def get_metrics_exporter() -> MetricsExporter:
    """Get singleton metrics exporter instance."""
    global _metrics_exporter_instance
    if _metrics_exporter_instance is None:
        _metrics_exporter_instance = MetricsExporter()
    return _metrics_exporter_instance
