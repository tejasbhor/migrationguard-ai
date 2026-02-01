import type { PendingApproval } from '@/services/api'
import { X, CheckCircle, XCircle } from 'lucide-react'
import { useState } from 'react'

interface ApprovalDetailModalProps {
  approval: PendingApproval | null
  onClose: () => void
  onApprove: (feedback?: string) => void
  onReject: (feedback: string) => void
}

export function ApprovalDetailModal({ approval, onClose, onApprove, onReject }: ApprovalDetailModalProps) {
  const [decision, setDecision] = useState<'approve' | 'reject' | null>(null)
  const [feedback, setFeedback] = useState('')

  if (!approval) return null

  const handleSubmit = () => {
    if (decision === 'approve') {
      onApprove(feedback || undefined)
    } else if (decision === 'reject') {
      if (!feedback.trim()) {
        alert('Feedback is required when rejecting an action')
        return
      }
      onReject(feedback)
    }
    setDecision(null)
    setFeedback('')
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <h2 className="text-xl font-semibold text-gray-900">Approval Details</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <X className="h-6 w-6" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[calc(90vh-200px)]">
          <div className="space-y-6">
            {/* Basic Info */}
            <div>
              <h3 className="text-sm font-medium text-gray-500 mb-3">Basic Information</h3>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-xs text-gray-500">Approval ID</label>
                  <p className="text-sm font-mono text-gray-900">{approval.approval_id}</p>
                </div>
                <div>
                  <label className="text-xs text-gray-500">Issue ID</label>
                  <p className="text-sm font-mono text-gray-900">{approval.issue_id}</p>
                </div>
                <div>
                  <label className="text-xs text-gray-500">Action Type</label>
                  <p className="text-sm text-gray-900">{approval.action_type}</p>
                </div>
                <div>
                  <label className="text-xs text-gray-500">Risk Level</label>
                  <p className="text-sm text-gray-900 capitalize">{approval.risk_level}</p>
                </div>
                <div>
                  <label className="text-xs text-gray-500">Priority</label>
                  <p className="text-sm text-gray-900 capitalize">{approval.priority}</p>
                </div>
                <div>
                  <label className="text-xs text-gray-500">Created At</label>
                  <p className="text-sm text-gray-900">
                    {new Date(approval.created_at).toLocaleString()}
                  </p>
                </div>
              </div>
            </div>

            {/* Parameters */}
            <div>
              <h3 className="text-sm font-medium text-gray-500 mb-3">Action Parameters</h3>
              <pre className="text-xs bg-gray-50 p-4 rounded-lg overflow-x-auto">
                {JSON.stringify(approval.parameters, null, 2)}
              </pre>
            </div>

            {/* Reasoning Chain */}
            {approval.reasoning && Object.keys(approval.reasoning).length > 0 && (
              <div>
                <h3 className="text-sm font-medium text-gray-500 mb-3">Reasoning Chain</h3>
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                  <pre className="text-xs text-gray-900 whitespace-pre-wrap">
                    {JSON.stringify(approval.reasoning, null, 2)}
                  </pre>
                </div>
              </div>
            )}

            {/* Decision Section */}
            {!decision && (
              <div className="flex items-center space-x-3 pt-4">
                <button
                  onClick={() => setDecision('approve')}
                  className="flex-1 flex items-center justify-center space-x-2 px-4 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
                >
                  <CheckCircle className="h-5 w-5" />
                  <span>Approve Action</span>
                </button>
                
                <button
                  onClick={() => setDecision('reject')}
                  className="flex-1 flex items-center justify-center space-x-2 px-4 py-3 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
                >
                  <XCircle className="h-5 w-5" />
                  <span>Reject Action</span>
                </button>
              </div>
            )}

            {/* Feedback Form */}
            {decision && (
              <div className="bg-gray-50 rounded-lg p-4">
                <h3 className="text-sm font-medium text-gray-900 mb-3">
                  {decision === 'approve' ? 'Approval Feedback (Optional)' : 'Rejection Feedback (Required)'}
                </h3>
                <textarea
                  value={feedback}
                  onChange={(e) => setFeedback(e.target.value)}
                  placeholder={
                    decision === 'approve'
                      ? 'Add any notes about this approval...'
                      : 'Please explain why you are rejecting this action...'
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 min-h-[100px]"
                  required={decision === 'reject'}
                />
                <div className="flex items-center space-x-3 mt-4">
                  <button
                    onClick={handleSubmit}
                    className={`flex-1 px-4 py-2 rounded-lg text-white transition-colors ${
                      decision === 'approve'
                        ? 'bg-green-600 hover:bg-green-700'
                        : 'bg-red-600 hover:bg-red-700'
                    }`}
                  >
                    Confirm {decision === 'approve' ? 'Approval' : 'Rejection'}
                  </button>
                  <button
                    onClick={() => {
                      setDecision(null)
                      setFeedback('')
                    }}
                    className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
