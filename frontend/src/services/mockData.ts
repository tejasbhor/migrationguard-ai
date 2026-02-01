/**
 * Mock data service for demonstration purposes
 * This simulates real API responses with realistic data
 */

import type { Signal, PendingApproval } from './api'

// Generate realistic timestamps
const now = Date.now()
const minute = 60 * 1000
const hour = 60 * minute

// Mock Signals
export const mockSignals: Signal[] = [
  {
    signal_id: 'sig_001',
    timestamp: new Date(now - 2 * minute).toISOString(),
    source: 'api_failure',
    merchant_id: 'merchant_acme_corp',
    migration_stage: 'api_integration',
    severity: 'critical',
    error_message: 'Unauthorized: Invalid API key',
    error_code: '401',
    affected_resource: '/api/v1/products',
    raw_data: {
      endpoint: '/api/v1/products',
      method: 'GET',
      status_code: 401,
      response_time_ms: 145,
    },
    context: {
      user_agent: 'AcmeCorp/1.0',
      ip_address: '192.168.1.100',
      retry_count: 0,
    },
  },
  {
    signal_id: 'sig_002',
    timestamp: new Date(now - 5 * minute).toISOString(),
    source: 'webhook_failure',
    merchant_id: 'merchant_techstart',
    migration_stage: 'webhook_setup',
    severity: 'high',
    error_message: 'Webhook endpoint returned 404 Not Found',
    error_code: 'WEBHOOK_404',
    affected_resource: '/webhooks/order_created',
    raw_data: {
      webhook_url: 'https://old-domain.techstart.com/webhooks/orders',
      status_code: 404,
      retry_count: 3,
      last_attempt: new Date(now - 1 * minute).toISOString(),
    },
    context: {
      event_type: 'order.created',
      payload_size_bytes: 2048,
    },
  },
  {
    signal_id: 'sig_003',
    timestamp: new Date(now - 8 * minute).toISOString(),
    source: 'checkout_error',
    merchant_id: 'merchant_fashion_hub',
    migration_stage: 'payment_integration',
    severity: 'critical',
    error_message: 'Payment gateway timeout after 30 seconds',
    error_code: 'GATEWAY_TIMEOUT',
    affected_resource: '/checkout/payment',
    raw_data: {
      gateway: 'stripe',
      timeout_seconds: 30,
      amount: 149.99,
      currency: 'USD',
      customer_id: 'cust_abc123',
    },
    context: {
      cart_items: 3,
      shipping_country: 'US',
      payment_method: 'card',
    },
  },
  {
    signal_id: 'sig_004',
    timestamp: new Date(now - 12 * minute).toISOString(),
    source: 'support_ticket',
    merchant_id: 'merchant_acme_corp',
    severity: 'high',
    error_message: 'Customer reports: Cannot access product catalog',
    error_code: 'SUPPORT_TICKET',
    affected_resource: '/products',
    raw_data: {
      ticket_id: 'TICKET-12345',
      customer_email: 'support@acmecorp.com',
      subject: 'API Access Issues',
      priority: 'high',
    },
    context: {
      ticket_created_at: new Date(now - 15 * minute).toISOString(),
      assigned_to: 'support_team',
    },
  },
  {
    signal_id: 'sig_005',
    timestamp: new Date(now - 18 * minute).toISOString(),
    source: 'api_failure',
    merchant_id: 'merchant_techstart',
    migration_stage: 'api_integration',
    severity: 'medium',
    error_message: 'Rate limit exceeded: 1000 requests per hour',
    error_code: 'RATE_LIMIT_EXCEEDED',
    affected_resource: '/api/v1/orders',
    raw_data: {
      limit: 1000,
      current: 1050,
      window: '1h',
      reset_at: new Date(now + 42 * minute).toISOString(),
    },
    context: {
      endpoint: '/api/v1/orders',
      method: 'POST',
    },
  },
  {
    signal_id: 'sig_006',
    timestamp: new Date(now - 25 * minute).toISOString(),
    source: 'checkout_error',
    merchant_id: 'merchant_fashion_hub',
    migration_stage: 'payment_integration',
    severity: 'high',
    error_message: 'Payment declined: Insufficient funds',
    error_code: 'PAYMENT_DECLINED',
    affected_resource: '/checkout/payment',
    raw_data: {
      gateway: 'stripe',
      decline_code: 'insufficient_funds',
      amount: 299.99,
      currency: 'USD',
    },
    context: {
      customer_id: 'cust_xyz789',
      payment_method: 'card',
    },
  },
  {
    signal_id: 'sig_007',
    timestamp: new Date(now - 32 * minute).toISOString(),
    source: 'api_failure',
    merchant_id: 'merchant_global_trade',
    migration_stage: 'api_integration',
    severity: 'low',
    error_message: 'Deprecated API endpoint used',
    error_code: 'DEPRECATED_ENDPOINT',
    affected_resource: '/api/v1/legacy/products',
    raw_data: {
      deprecated_endpoint: '/api/v1/legacy/products',
      new_endpoint: '/api/v2/products',
      sunset_date: '2026-06-01',
    },
    context: {
      migration_guide_url: 'https://docs.example.com/migration',
    },
  },
  {
    signal_id: 'sig_008',
    timestamp: new Date(now - 45 * minute).toISOString(),
    source: 'webhook_failure',
    merchant_id: 'merchant_techstart',
    migration_stage: 'webhook_setup',
    severity: 'medium',
    error_message: 'Webhook signature verification failed',
    error_code: 'INVALID_SIGNATURE',
    affected_resource: '/webhooks/payment_success',
    raw_data: {
      webhook_url: 'https://techstart.com/webhooks/payment',
      expected_signature: 'sha256=abc123...',
      received_signature: 'sha256=xyz789...',
    },
    context: {
      event_type: 'payment.success',
    },
  },
]

// Mock Issues with AI Analysis
export const mockIssues = [
  {
    issue_id: 'issue_001',
    title: 'Authentication Failures - ACME Corp',
    merchant_id: 'merchant_acme_corp',
    status: 'active',
    severity: 'critical',
    created_at: new Date(now - 15 * minute).toISOString(),
    updated_at: new Date(now - 2 * minute).toISOString(),
    signal_count: 3,
    pattern_type: 'authentication_failure',
    analysis: {
      category: 'migration_misstep',
      confidence: 0.92,
      reasoning: 'Multiple 401 Unauthorized errors indicate that the merchant is using an invalid or expired API key. This is a common issue during platform migration when API credentials are not properly updated. The pattern shows consistent authentication failures across multiple endpoints, suggesting a systemic configuration problem rather than isolated incidents.',
      evidence: [
        'Signal 1: API failure with 401 error code',
        'Signal 2: Support ticket reporting API access issues',
        'Signal 3: Multiple retry attempts with same error',
        'Pattern: All errors from same merchant within 15-minute window',
      ],
      alternatives_considered: [
        {
          hypothesis: 'Platform API outage',
          confidence: 0.15,
          rejected_reason: 'No other merchants reporting similar issues',
        },
        {
          hypothesis: 'Network connectivity issue',
          confidence: 0.10,
          rejected_reason: 'Errors are authentication-specific, not connection failures',
        },
      ],
      recommended_actions: [
        'Verify API key is correctly configured in merchant system',
        'Check if API key has been regenerated during migration',
        'Provide merchant with updated API credentials',
        'Send migration guide with API authentication steps',
        'Schedule follow-up call to verify resolution',
      ],
    },
    actions: [
      {
        action_id: 'act_001',
        action_type: 'support_guidance',
        status: 'completed',
        executed_at: new Date(now - 5 * minute).toISOString(),
        result: {
          ticket_created: true,
          ticket_id: 'TICKET-12346',
          merchant_notified: true,
        },
      },
    ],
  },
  {
    issue_id: 'issue_002',
    title: 'Webhook Configuration - TechStart',
    merchant_id: 'merchant_techstart',
    status: 'pending_approval',
    severity: 'high',
    created_at: new Date(now - 25 * minute).toISOString(),
    updated_at: new Date(now - 5 * minute).toISOString(),
    signal_count: 2,
    pattern_type: 'webhook_problem',
    analysis: {
      category: 'config_error',
      confidence: 0.88,
      reasoning: 'Webhook endpoint returning 404 errors indicates that the webhook URL is pointing to an old or incorrect domain. This is typical during migration when webhook configurations are not updated. The signature verification failure suggests additional configuration issues with webhook secrets.',
      evidence: [
        'Webhook 404 errors to old-domain.techstart.com',
        'Signature verification failures',
        'Multiple retry attempts',
        'Migration stage: webhook_setup',
      ],
      alternatives_considered: [
        {
          hypothesis: 'Temporary DNS issue',
          confidence: 0.20,
          rejected_reason: 'Errors persist across multiple attempts over 20 minutes',
        },
      ],
      recommended_actions: [
        'Update webhook URL to new domain',
        'Regenerate webhook signing secret',
        'Test webhook delivery with sample payload',
        'Update webhook configuration documentation',
      ],
    },
    actions: [],
  },
  {
    issue_id: 'issue_003',
    title: 'Payment Gateway Timeouts - Fashion Hub',
    merchant_id: 'merchant_fashion_hub',
    status: 'resolved',
    severity: 'critical',
    created_at: new Date(now - 2 * hour).toISOString(),
    updated_at: new Date(now - 30 * minute).toISOString(),
    signal_count: 5,
    pattern_type: 'checkout_issue',
    analysis: {
      category: 'platform_regression',
      confidence: 0.75,
      reasoning: 'Payment gateway timeouts occurring consistently suggest a performance issue with the payment integration. The 30-second timeout threshold is being exceeded, which may indicate network latency or payment processor issues.',
      evidence: [
        'Multiple gateway timeout errors',
        'Consistent 30-second timeout pattern',
        'Affects multiple customers',
        'Started after migration',
      ],
      alternatives_considered: [],
      recommended_actions: [
        'Investigate payment gateway response times',
        'Check network connectivity to payment processor',
        'Review payment integration configuration',
        'Consider increasing timeout threshold',
      ],
    },
    actions: [
      {
        action_id: 'act_002',
        action_type: 'engineering_escalation',
        status: 'completed',
        executed_at: new Date(now - 45 * minute).toISOString(),
        result: {
          escalated_to: 'platform_engineering',
          ticket_id: 'ENG-789',
          resolved: true,
        },
      },
    ],
  },
]

// Mock Pending Approvals
export const mockPendingApprovals: PendingApproval[] = [
  {
    approval_id: 'approval_001',
    issue_id: 'issue_002',
    action_type: 'proactive_communication',
    risk_level: 'medium',
    parameters: {
      merchant_id: 'merchant_techstart',
      message: 'We detected webhook configuration issues and have prepared a fix...',
      communication_channel: 'email',
    },
    reasoning: {
      category: 'config_error',
      confidence: 0.88,
      analysis: 'Webhook misconfiguration detected',
    },
    created_at: new Date(now - 10 * minute).toISOString(),
    merchant_id: 'merchant_techstart',
    priority: 'high',
  },
  {
    approval_id: 'approval_002',
    issue_id: 'issue_004',
    action_type: 'temporary_mitigation',
    risk_level: 'high',
    parameters: {
      merchant_id: 'merchant_global_trade',
      mitigation_type: 'rate_limit_increase',
      duration_hours: 24,
    },
    reasoning: {
      category: 'migration_misstep',
      confidence: 0.82,
      analysis: 'Temporary rate limit increase needed during migration',
    },
    created_at: new Date(now - 5 * minute).toISOString(),
    merchant_id: 'merchant_global_trade',
    priority: 'high',
  },
]

// Mock Metrics
export const mockMetrics = {
  performance: {
    signal_ingestion_rate: 127.5,
    processing_latency_p50: 145,
    processing_latency_p95: 320,
    processing_latency_p99: 580,
    decision_accuracy: 0.89,
    action_success_rate: 0.94,
    timestamp: new Date().toISOString(),
  },
  deflection: {
    total_tickets: 156,
    deflected_tickets: 136,
    deflection_rate: 0.87,
    avg_resolution_time_minutes: 4.2,
    by_category: {
      authentication: {
        total: 45,
        deflected: 42,
        deflection_rate: 0.93,
      },
      webhook: {
        total: 38,
        deflected: 35,
        deflection_rate: 0.92,
      },
      payment: {
        total: 42,
        deflected: 34,
        deflection_rate: 0.81,
      },
      api: {
        total: 31,
        deflected: 25,
        deflection_rate: 0.81,
      },
    },
    timestamp: new Date().toISOString(),
  },
  confidence_calibration: [
    {
      confidence_bucket: '0.9-1.0',
      predicted_confidence: 0.95,
      actual_accuracy: 0.93,
      sample_count: 45,
      calibration_error: 0.02,
    },
    {
      confidence_bucket: '0.8-0.9',
      predicted_confidence: 0.85,
      actual_accuracy: 0.87,
      sample_count: 67,
      calibration_error: -0.02,
    },
    {
      confidence_bucket: '0.7-0.8',
      predicted_confidence: 0.75,
      actual_accuracy: 0.76,
      sample_count: 52,
      calibration_error: -0.01,
    },
    {
      confidence_bucket: '0.6-0.7',
      predicted_confidence: 0.65,
      actual_accuracy: 0.68,
      sample_count: 34,
      calibration_error: -0.03,
    },
  ],
}

// Mock Dashboard Stats
export const mockDashboardStats = {
  active_issues: 12,
  active_issues_change: -8,
  pending_approvals: 3,
  deflection_rate: 87,
  deflection_rate_change: 3,
  avg_resolution_time: 4.2,
  avg_resolution_time_change: -12,
  total_signals_today: 1247,
  critical_issues: 2,
  high_priority_issues: 5,
  medium_priority_issues: 3,
  low_priority_issues: 2,
}

// Mock Recent Activity
export const mockRecentActivity = [
  {
    id: 'activity_001',
    type: 'issue_resolved',
    title: 'Payment Gateway Timeouts - Fashion Hub',
    description: 'Issue automatically resolved by engineering escalation',
    timestamp: new Date(now - 30 * minute).toISOString(),
    severity: 'critical',
  },
  {
    id: 'activity_002',
    type: 'approval_pending',
    title: 'Webhook Configuration - TechStart',
    description: 'Proactive communication requires approval',
    timestamp: new Date(now - 10 * minute).toISOString(),
    severity: 'high',
  },
  {
    id: 'activity_003',
    type: 'signal_detected',
    title: 'Authentication Failures - ACME Corp',
    description: 'Multiple API authentication errors detected',
    timestamp: new Date(now - 2 * minute).toISOString(),
    severity: 'critical',
  },
  {
    id: 'activity_004',
    type: 'action_executed',
    title: 'Support Guidance Sent - ACME Corp',
    description: 'Automated support ticket created and merchant notified',
    timestamp: new Date(now - 5 * minute).toISOString(),
    severity: 'high',
  },
  {
    id: 'activity_005',
    type: 'pattern_detected',
    title: 'Rate Limit Pattern - Global Trade',
    description: 'Recurring rate limit issues detected across multiple endpoints',
    timestamp: new Date(now - 45 * minute).toISOString(),
    severity: 'medium',
  },
]

// Helper function to simulate real-time updates
export function generateNewSignal(): Signal {
  const sources: Signal['source'][] = ['api_failure', 'webhook_failure', 'checkout_error', 'support_ticket']
  const severities: Signal['severity'][] = ['low', 'medium', 'high', 'critical']
  const merchants = ['merchant_acme_corp', 'merchant_techstart', 'merchant_fashion_hub', 'merchant_global_trade']
  
  const source = sources[Math.floor(Math.random() * sources.length)]
  const severity = severities[Math.floor(Math.random() * severities.length)]
  const merchant = merchants[Math.floor(Math.random() * merchants.length)]
  
  return {
    signal_id: `sig_${Date.now()}`,
    timestamp: new Date().toISOString(),
    source,
    merchant_id: merchant,
    severity,
    error_message: `Simulated ${source} error`,
    error_code: `ERR_${Math.floor(Math.random() * 1000)}`,
    affected_resource: '/api/v1/test',
    raw_data: {},
    context: {},
  }
}
