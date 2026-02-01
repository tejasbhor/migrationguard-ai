import { useState } from 'react'
import { AlertCircle, Brain, CheckCircle, Clock } from 'lucide-react'
import { mockIssues } from '@/services/mockData'

export function Issues() {
  const issues = mockIssues
  const [selectedIssue, setSelectedIssue] = useState(mockIssues[0])
  const [filter, setFilter] = useState<'all' | 'active' | 'pending_approval' | 'resolved'>('all')

  const filteredIssues = issues.filter(issue => {
    if (filter === 'all') return true
    return issue.status === filter
  })

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return 'bg-red-100 text-red-800 border-red-200'
      case 'high': return 'bg-orange-100 text-orange-800 border-orange-200'
      case 'medium': return 'bg-yellow-100 text-yellow-800 border-yellow-200'
      case 'low': return 'bg-blue-100 text-blue-800 border-blue-200'
      default: return 'bg-gray-100 text-gray-800 border-gray-200'
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'active': return <AlertCircle className="h-5 w-5 text-red-600" />
      case 'pending_approval': return <Clock className="h-5 w-5 text-yellow-600" />
      case 'resolved': return <CheckCircle className="h-5 w-5 text-green-600" />
      default: return <AlertCircle className="h-5 w-5 text-gray-600" />
    }
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'active': return 'bg-red-100 text-red-800'
      case 'pending_approval': return 'bg-yellow-100 text-yellow-800'
      case 'resolved': return 'bg-green-100 text-green-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  const formatTimeAgo = (timestamp: string) => {
    const seconds = Math.floor((Date.now() - new Date(timestamp).getTime()) / 1000)
    if (seconds < 60) return `${seconds}s ago`
    const minutes = Math.floor(seconds / 60)
    if (minutes < 60) return `${minutes}m ago`
    const hours = Math.floor(minutes / 60)
    if (hours < 24) return `${hours}h ago`
    const days = Math.floor(hours / 24)
    return `${days}d ago`
  }

  const getCategoryColor = (category: string) => {
    switch (category) {
      case 'migration_misstep': return 'text-purple-700 bg-purple-50'
      case 'platform_regression': return 'text-red-700 bg-red-50'
      case 'documentation_gap': return 'text-blue-700 bg-blue-50'
      case 'config_error': return 'text-orange-700 bg-orange-50'
      default: return 'text-gray-700 bg-gray-50'
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Issues & Analysis</h1>
        <div className="flex items-center space-x-2">
          <Brain className="h-5 w-5 text-blue-600" />
          <span className="text-sm text-gray-600">AI-Powered Root Cause Analysis</span>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="bg-white rounded-lg shadow mb-6">
        <div className="border-b border-gray-200">
          <nav className="flex space-x-8 px-6" aria-label="Tabs">
            {[
              { key: 'all', label: 'All Issues', count: issues.length },
              { key: 'active', label: 'Active', count: issues.filter(i => i.status === 'active').length },
              { key: 'pending_approval', label: 'Pending Approval', count: issues.filter(i => i.status === 'pending_approval').length },
              { key: 'resolved', label: 'Resolved', count: issues.filter(i => i.status === 'resolved').length },
            ].map((tab) => (
              <button
                key={tab.key}
                onClick={() => setFilter(tab.key as any)}
                className={`
                  py-4 px-1 border-b-2 font-medium text-sm transition-colors
                  ${filter === tab.key
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }
                `}
              >
                {tab.label}
                <span className="ml-2 py-0.5 px-2 rounded-full text-xs bg-gray-100">
                  {tab.count}
                </span>
              </button>
            ))}
          </nav>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Issue List */}
        <div className="lg:col-span-1 space-y-3">
          {filteredIssues.map((issue) => (
            <div
              key={issue.issue_id}
              onClick={() => setSelectedIssue(issue)}
              className={`
                bg-white rounded-lg shadow p-4 cursor-pointer transition-all
                ${selectedIssue?.issue_id === issue.issue_id ? 'ring-2 ring-blue-500' : 'hover:shadow-md'}
              `}
            >
              <div className="flex items-start justify-between mb-2">
                <div className="flex items-center space-x-2">
                  {getStatusIcon(issue.status)}
                  <span className={`text-xs px-2 py-1 rounded-full font-medium ${getStatusBadge(issue.status)}`}>
                    {issue.status.replace('_', ' ')}
                  </span>
                </div>
                <span className={`text-xs px-2 py-1 rounded border font-medium ${getSeverityColor(issue.severity)}`}>
                  {issue.severity}
                </span>
              </div>
              
              <h3 className="font-semibold text-gray-900 text-sm mb-1">{issue.title}</h3>
              <p className="text-xs text-gray-500 mb-2">{issue.merchant_id}</p>
              
              <div className="flex items-center justify-between text-xs text-gray-500">
                <span>{issue.signal_count} signals</span>
                <span>{formatTimeAgo(issue.updated_at)}</span>
              </div>
            </div>
          ))}
        </div>

        {/* Issue Detail */}
        <div className="lg:col-span-2">
          {selectedIssue ? (
            <div className="bg-white rounded-lg shadow">
              {/* Header */}
              <div className="p-6 border-b border-gray-200">
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <h2 className="text-xl font-bold text-gray-900 mb-2">{selectedIssue.title}</h2>
                    <div className="flex items-center space-x-3">
                      <span className={`text-xs px-2 py-1 rounded-full font-medium ${getStatusBadge(selectedIssue.status)}`}>
                        {selectedIssue.status.replace('_', ' ')}
                      </span>
                      <span className={`text-xs px-2 py-1 rounded border font-medium ${getSeverityColor(selectedIssue.severity)}`}>
                        {selectedIssue.severity}
                      </span>
                      <span className="text-xs text-gray-500">
                        {selectedIssue.signal_count} signals • {selectedIssue.pattern_type.replace('_', ' ')}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-gray-500">Merchant:</span>
                    <span className="ml-2 font-medium text-gray-900">{selectedIssue.merchant_id}</span>
                  </div>
                  <div>
                    <span className="text-gray-500">Created:</span>
                    <span className="ml-2 font-medium text-gray-900">{formatTimeAgo(selectedIssue.created_at)}</span>
                  </div>
                </div>
              </div>

              {/* AI Analysis */}
              <div className="p-6 border-b border-gray-200 bg-gradient-to-br from-blue-50 to-purple-50">
                <div className="flex items-center space-x-2 mb-4">
                  <Brain className="h-5 w-5 text-blue-600" />
                  <h3 className="text-lg font-semibold text-gray-900">AI Root Cause Analysis</h3>
                </div>

                {/* Category & Confidence */}
                <div className="grid grid-cols-2 gap-4 mb-4">
                  <div className="bg-white rounded-lg p-4">
                    <div className="text-sm text-gray-500 mb-1">Category</div>
                    <div className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${getCategoryColor(selectedIssue.analysis.category)}`}>
                      {selectedIssue.analysis.category.replace('_', ' ')}
                    </div>
                  </div>
                  <div className="bg-white rounded-lg p-4">
                    <div className="text-sm text-gray-500 mb-1">Confidence</div>
                    <div className="flex items-center space-x-2">
                      <div className="flex-1 bg-gray-200 rounded-full h-2">
                        <div
                          className="bg-blue-600 h-2 rounded-full transition-all"
                          style={{ width: `${selectedIssue.analysis.confidence * 100}%` }}
                        ></div>
                      </div>
                      <span className="text-sm font-semibold text-gray-900">
                        {(selectedIssue.analysis.confidence * 100).toFixed(0)}%
                      </span>
                    </div>
                  </div>
                </div>

                {/* Reasoning */}
                <div className="bg-white rounded-lg p-4 mb-4">
                  <h4 className="text-sm font-semibold text-gray-900 mb-2">Reasoning</h4>
                  <p className="text-sm text-gray-700 leading-relaxed">{selectedIssue.analysis.reasoning}</p>
                </div>

                {/* Evidence */}
                <div className="bg-white rounded-lg p-4 mb-4">
                  <h4 className="text-sm font-semibold text-gray-900 mb-2">Evidence</h4>
                  <ul className="space-y-2">
                    {selectedIssue.analysis.evidence.map((evidence, idx) => (
                      <li key={idx} className="flex items-start space-x-2 text-sm text-gray-700">
                        <CheckCircle className="h-4 w-4 text-green-600 mt-0.5 flex-shrink-0" />
                        <span>{evidence}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                {/* Alternatives Considered */}
                {selectedIssue.analysis.alternatives_considered && selectedIssue.analysis.alternatives_considered.length > 0 && (
                  <div className="bg-white rounded-lg p-4 mb-4">
                    <h4 className="text-sm font-semibold text-gray-900 mb-2">Alternatives Considered</h4>
                    <div className="space-y-2">
                      {selectedIssue.analysis.alternatives_considered.map((alt, idx) => (
                        <div key={idx} className="text-sm">
                          <div className="flex items-center justify-between mb-1">
                            <span className="font-medium text-gray-700">{alt.hypothesis}</span>
                            <span className="text-xs text-gray-500">{(alt.confidence * 100).toFixed(0)}% confidence</span>
                          </div>
                          <p className="text-xs text-gray-600">Rejected: {alt.rejected_reason}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Recommended Actions */}
                <div className="bg-white rounded-lg p-4">
                  <h4 className="text-sm font-semibold text-gray-900 mb-2">Recommended Actions</h4>
                  <ol className="space-y-2">
                    {selectedIssue.analysis.recommended_actions.map((action, idx) => (
                      <li key={idx} className="flex items-start space-x-2 text-sm text-gray-700">
                        <span className="flex-shrink-0 w-5 h-5 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center text-xs font-semibold">
                          {idx + 1}
                        </span>
                        <span>{action}</span>
                      </li>
                    ))}
                  </ol>
                </div>
              </div>

              {/* Actions Taken */}
              {selectedIssue.actions && selectedIssue.actions.length > 0 && (
                <div className="p-6">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">Actions Taken</h3>
                  <div className="space-y-3">
                    {selectedIssue.actions.map((action) => (
                      <div key={action.action_id} className="bg-gray-50 rounded-lg p-4">
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-sm font-medium text-gray-900">
                            {action.action_type.replace('_', ' ')}
                          </span>
                          <span className={`text-xs px-2 py-1 rounded-full font-medium ${
                            action.status === 'completed' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                          }`}>
                            {action.status}
                          </span>
                        </div>
                        <div className="text-xs text-gray-500">
                          Executed: {new Date(action.executed_at).toLocaleString()}
                        </div>
                        {action.result && (
                          <div className="mt-2 text-xs text-gray-600">
                            {Object.entries(action.result).map(([key, value]) => (
                              <div key={key}>
                                <span className="font-medium">{key}:</span> {String(value)}
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="bg-white rounded-lg shadow p-8 text-center">
              <AlertCircle className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <p className="text-gray-500">Select an issue to view details</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
