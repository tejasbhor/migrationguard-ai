import type { PendingApproval } from '@/services/api'
import { CheckCircle, Clock, XCircle } from 'lucide-react'

interface ApprovalCardProps {
  approval: PendingApproval
  onApprove: () => void
  onReject: () => void
  onViewDetails: () => void
}

const riskConfig = {
  critical: {
    bgColor: 'bg-red-50',
    borderColor: 'border-red-300',
    textColor: 'text-red-700',
    badgeColor: 'bg-red-100 text-red-800',
  },
  high: {
    bgColor: 'bg-orange-50',
    borderColor: 'border-orange-300',
    textColor: 'text-orange-700',
    badgeColor: 'bg-orange-100 text-orange-800',
  },
  medium: {
    bgColor: 'bg-yellow-50',
    borderColor: 'border-yellow-300',
    textColor: 'text-yellow-700',
    badgeColor: 'bg-yellow-100 text-yellow-800',
  },
  low: {
    bgColor: 'bg-blue-50',
    borderColor: 'border-blue-300',
    textColor: 'text-blue-700',
    badgeColor: 'bg-blue-100 text-blue-800',
  },
}

const actionTypeLabels: Record<string, string> = {
  support_guidance: 'Support Guidance',
  proactive_communication: 'Proactive Communication',
  engineering_escalation: 'Engineering Escalation',
  temporary_mitigation: 'Temporary Mitigation',
  documentation_update: 'Documentation Update',
}

export function ApprovalCard({ approval, onApprove, onReject, onViewDetails }: ApprovalCardProps) {
  const config = riskConfig[approval.risk_level]
  const timestamp = new Date(approval.created_at).toLocaleString()

  return (
    <div className={`${config.bgColor} ${config.borderColor} border-2 rounded-lg p-6`}>
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1">
          <div className="flex items-center space-x-3 mb-2">
            <span className={`px-3 py-1 rounded-full text-xs font-semibold ${config.badgeColor}`}>
              {approval.risk_level.toUpperCase()} RISK
            </span>
            <span className="px-3 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-700">
              {approval.priority.toUpperCase()}
            </span>
          </div>
          
          <h3 className="text-lg font-semibold text-gray-900 mb-1">
            {actionTypeLabels[approval.action_type] || approval.action_type}
          </h3>
          
          <div className="flex items-center space-x-4 text-sm text-gray-600">
            <span>Issue: {approval.issue_id.substring(0, 8)}...</span>
            {approval.merchant_id && <span>Merchant: {approval.merchant_id}</span>}
            <span className="flex items-center">
              <Clock className="h-4 w-4 mr-1" />
              {timestamp}
            </span>
          </div>
        </div>
      </div>

      {/* Parameters Preview */}
      <div className="bg-white bg-opacity-50 rounded-lg p-4 mb-4">
        <h4 className="text-sm font-medium text-gray-700 mb-2">Action Parameters</h4>
        <div className="space-y-1">
          {Object.entries(approval.parameters).slice(0, 3).map(([key, value]) => (
            <div key={key} className="text-sm">
              <span className="font-medium text-gray-600">{key}:</span>{' '}
              <span className="text-gray-900">
                {typeof value === 'object' ? JSON.stringify(value) : String(value)}
              </span>
            </div>
          ))}
          {Object.keys(approval.parameters).length > 3 && (
            <button
              onClick={onViewDetails}
              className="text-sm text-blue-600 hover:text-blue-800 font-medium"
            >
              View all parameters...
            </button>
          )}
        </div>
      </div>

      {/* Reasoning Preview */}
      {approval.reasoning && Object.keys(approval.reasoning).length > 0 && (
        <div className="bg-white bg-opacity-50 rounded-lg p-4 mb-4">
          <h4 className="text-sm font-medium text-gray-700 mb-2">Reasoning</h4>
          <button
            onClick={onViewDetails}
            className="text-sm text-blue-600 hover:text-blue-800 font-medium"
          >
            View reasoning chain →
          </button>
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex items-center space-x-3">
        <button
          onClick={onApprove}
          className="flex-1 flex items-center justify-center space-x-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
        >
          <CheckCircle className="h-5 w-5" />
          <span>Approve</span>
        </button>
        
        <button
          onClick={onReject}
          className="flex-1 flex items-center justify-center space-x-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
        >
          <XCircle className="h-5 w-5" />
          <span>Reject</span>
        </button>
        
        <button
          onClick={onViewDetails}
          className="px-4 py-2 border-2 border-gray-300 text-gray-700 rounded-lg hover:bg-white transition-colors"
        >
          Details
        </button>
      </div>
    </div>
  )
}
