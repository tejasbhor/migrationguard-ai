import { useState, useEffect } from 'react'
import type { PendingApproval } from '@/services/api'
import { ApprovalCard } from '@/components/ApprovalCard'
import { ApprovalDetailModal } from '@/components/ApprovalDetailModal'
import { AlertCircle, Filter, CheckCircle } from 'lucide-react'
import { mockPendingApprovals } from '@/services/mockData'

export function Approvals() {
  const [approvals, setApprovals] = useState<PendingApproval[]>(mockPendingApprovals)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [selectedApproval, setSelectedApproval] = useState<PendingApproval | null>(null)
  const [filterRiskLevel, setFilterRiskLevel] = useState<string>('')
  const [filterMerchant, setFilterMerchant] = useState<string>('')
  const [successMessage, setSuccessMessage] = useState<string | null>(null)

  // Fetch approvals
  const fetchApprovals = async () => {
    try {
      setLoading(true)
      setError(null)
      
      // Simulate API delay
      await new Promise(resolve => setTimeout(resolve, 500))
      
      // Filter approvals
      let filtered = [...mockPendingApprovals]
      if (filterRiskLevel) {
        filtered = filtered.filter(a => a.risk_level === filterRiskLevel)
      }
      if (filterMerchant) {
        filtered = filtered.filter(a => 
          a.merchant_id?.toLowerCase().includes(filterMerchant.toLowerCase())
        )
      }
      
      setApprovals(filtered)
    } catch (err) {
      setError('Failed to load approvals')
      console.error('Error fetching approvals:', err)
    } finally {
      setLoading(false)
    }
  }

  // Initial fetch
  useEffect(() => {
    fetchApprovals()
  }, [filterRiskLevel, filterMerchant])

  // Handle approve/reject
  const handleApprove = async (approvalId: string, _feedback?: string) => {
    try {
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 500))
      
      setApprovals((prev) => prev.filter((a) => a.approval_id !== approvalId))
      setSelectedApproval(null)
      setSuccessMessage('Action approved and executed successfully')
      setTimeout(() => setSuccessMessage(null), 3000)
    } catch (err) {
      console.error('Error approving action:', err)
      alert('Failed to approve action')
    }
  }

  const handleReject = async (approvalId: string, _feedback: string) => {
    try {
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 500))
      
      setApprovals((prev) => prev.filter((a) => a.approval_id !== approvalId))
      setSelectedApproval(null)
      setSuccessMessage('Action rejected successfully')
      setTimeout(() => setSuccessMessage(null), 3000)
    } catch (err) {
      console.error('Error rejecting action:', err)
      alert('Failed to reject action')
    }
  }

  // Sort approvals by risk level and priority
  const sortedApprovals = [...approvals].sort((a, b) => {
    const riskOrder = { critical: 0, high: 1, medium: 2, low: 3 }
    const riskDiff = riskOrder[a.risk_level] - riskOrder[b.risk_level]
    if (riskDiff !== 0) return riskDiff
    
    const priorityOrder = { urgent: 0, high: 1, medium: 2, low: 3 }
    return priorityOrder[a.priority as keyof typeof priorityOrder] - priorityOrder[b.priority as keyof typeof priorityOrder]
  })

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Pending Approvals</h1>
        <div className="flex items-center space-x-3">
          <span className="text-sm text-gray-600">
            {approvals.length} pending approval{approvals.length !== 1 ? 's' : ''}
          </span>
        </div>
      </div>

      {/* Success Message */}
      {successMessage && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4 flex items-center space-x-3 mb-6">
          <CheckCircle className="h-5 w-5 text-green-600" />
          <p className="text-green-800">{successMessage}</p>
        </div>
      )}

      {/* Filters */}
      <div className="bg-white rounded-lg shadow p-4 mb-6">
        <div className="flex items-center space-x-4">
          <Filter className="h-5 w-5 text-gray-400" />
          <div className="flex-1 flex items-center space-x-4">
            <div>
              <label className="text-xs text-gray-500 block mb-1">Risk Level</label>
              <select
                value={filterRiskLevel}
                onChange={(e) => setFilterRiskLevel(e.target.value)}
                className="px-3 py-1.5 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">All</option>
                <option value="critical">Critical</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
              </select>
            </div>
            
            <div>
              <label className="text-xs text-gray-500 block mb-1">Merchant ID</label>
              <input
                type="text"
                value={filterMerchant}
                onChange={(e) => setFilterMerchant(e.target.value)}
                placeholder="Filter by merchant..."
                className="px-3 py-1.5 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            {(filterRiskLevel || filterMerchant) && (
              <button
                onClick={() => {
                  setFilterRiskLevel('')
                  setFilterMerchant('')
                }}
                className="text-sm text-blue-600 hover:text-blue-800"
              >
                Clear filters
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="bg-white rounded-lg shadow p-12 text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-500">Loading approvals...</p>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-center space-x-3">
          <AlertCircle className="h-5 w-5 text-red-600" />
          <p className="text-red-800">{error}</p>
          <button
            onClick={fetchApprovals}
            className="ml-auto px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700"
          >
            Retry
          </button>
        </div>
      )}

      {/* Empty State */}
      {!loading && !error && approvals.length === 0 && (
        <div className="bg-white rounded-lg shadow p-12 text-center">
          <div className="text-gray-400 mb-4">
            <svg className="h-16 w-16 mx-auto" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <h3 className="text-lg font-medium text-gray-900 mb-2">No pending approvals</h3>
          <p className="text-gray-500">All actions have been reviewed</p>
        </div>
      )}

      {/* Approvals List */}
      {!loading && !error && approvals.length > 0 && (
        <div className="space-y-4">
          {sortedApprovals.map((approval) => (
            <ApprovalCard
              key={approval.approval_id}
              approval={approval}
              onApprove={() => handleApprove(approval.approval_id)}
              onReject={() => setSelectedApproval(approval)}
              onViewDetails={() => setSelectedApproval(approval)}
            />
          ))}
        </div>
      )}

      {/* Detail Modal */}
      <ApprovalDetailModal
        approval={selectedApproval}
        onClose={() => setSelectedApproval(null)}
        onApprove={(feedback) => selectedApproval && handleApprove(selectedApproval.approval_id, feedback)}
        onReject={(feedback) => selectedApproval && handleReject(selectedApproval.approval_id, feedback)}
      />
    </div>
  )
}
