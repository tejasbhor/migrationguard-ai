import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Signal types
export interface Signal {
  signal_id: string
  timestamp: string
  source: 'support_ticket' | 'api_failure' | 'checkout_error' | 'webhook_failure'
  merchant_id: string
  migration_stage?: string
  severity: 'low' | 'medium' | 'high' | 'critical'
  error_message?: string
  error_code?: string
  affected_resource?: string
  raw_data: Record<string, any>
  context: Record<string, any>
}

export interface SignalSearchParams {
  source?: string
  merchant_id?: string
  severity?: string
  start_time?: string
  end_time?: string
  limit?: number
  offset?: number
}

// Approval types
export interface PendingApproval {
  approval_id: string
  issue_id: string
  action_type: string
  risk_level: 'low' | 'medium' | 'high' | 'critical'
  parameters: Record<string, any>
  reasoning: Record<string, any>
  created_at: string
  merchant_id?: string
  priority: string
}

export interface ApprovalRequest {
  decision: 'approve' | 'reject'
  feedback?: string
  operator_id: string
}

export interface ApprovalResponse {
  approval_id: string
  decision: string
  executed: boolean
  result?: Record<string, any>
  error?: string
  timestamp: string
}

// API functions
export const signalsApi = {
  search: async (params: SignalSearchParams) => {
    const response = await api.get<Signal[]>('/api/v1/signals/search', { params })
    return response.data
  },
  
  getById: async (signalId: string) => {
    const response = await api.get<Signal>(`/api/v1/signals/${signalId}`)
    return response.data
  },
}

export const approvalsApi = {
  getPending: async (params?: { merchant_id?: string; risk_level?: string; limit?: number }) => {
    const response = await api.get<PendingApproval[]>('/api/v1/approvals', { params })
    return response.data
  },
  
  approveOrReject: async (approvalId: string, request: ApprovalRequest) => {
    const response = await api.post<ApprovalResponse>(`/api/v1/approvals/${approvalId}`, request)
    return response.data
  },
}

// WebSocket connection for real-time updates
export const createApprovalsWebSocket = (onMessage: (data: any) => void) => {
  const wsUrl = API_BASE_URL.replace('http', 'ws') + '/api/v1/approvals/ws'
  const ws = new WebSocket(wsUrl)
  
  ws.onmessage = (event) => {
    const data = JSON.parse(event.data)
    onMessage(data)
  }
  
  ws.onerror = (error) => {
    console.error('WebSocket error:', error)
  }
  
  return ws
}

// Metrics types
export interface PerformanceMetrics {
  signal_ingestion_rate: number
  processing_latency_p50: number
  processing_latency_p95: number
  processing_latency_p99: number
  decision_accuracy: number
  action_success_rate: number
  timestamp: string
}

export interface DeflectionMetrics {
  total_tickets: number
  deflected_tickets: number
  deflection_rate: number
  avg_resolution_time_minutes: number
  by_category: Record<string, {
    total: number
    deflected: number
    deflection_rate: number
  }>
  timestamp: string
}

export interface ConfidenceCalibration {
  confidence_bucket: string
  predicted_confidence: number
  actual_accuracy: number
  sample_count: number
  calibration_error: number
}

export interface MetricsParams {
  start_time?: string
  end_time?: string
  merchant_id?: string
}

// Metrics API
export const metricsApi = {
  getPerformance: async (params?: MetricsParams) => {
    const response = await api.get<PerformanceMetrics>('/api/v1/metrics/performance', { params })
    return response.data
  },
  
  getDeflection: async (params?: MetricsParams) => {
    const response = await api.get<DeflectionMetrics>('/api/v1/metrics/deflection', { params })
    return response.data
  },
  
  getConfidenceCalibration: async (params?: MetricsParams) => {
    const response = await api.get<ConfidenceCalibration[]>('/api/v1/metrics/confidence-calibration', { params })
    return response.data
  },
}
