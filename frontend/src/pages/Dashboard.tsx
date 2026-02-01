import { useState, useEffect } from 'react'
import { Activity, TrendingDown, TrendingUp, AlertCircle, CheckCircle, Clock } from 'lucide-react'
import { mockDashboardStats, mockRecentActivity, mockIssues } from '@/services/mockData'

export function Dashboard() {
  const [stats, setStats] = useState(mockDashboardStats)
  const recentActivity = mockRecentActivity
  const issues = mockIssues

  useEffect(() => {
    // Simulate real-time updates
    const interval = setInterval(() => {
      setStats(prev => ({
        ...prev,
        total_signals_today: prev.total_signals_today + Math.floor(Math.random() * 3),
      }))
    }, 5000)

    return () => clearInterval(interval)
  }, [])

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return 'text-red-600 bg-red-50'
      case 'high': return 'text-orange-600 bg-orange-50'
      case 'medium': return 'text-yellow-600 bg-yellow-50'
      case 'low': return 'text-blue-600 bg-blue-50'
      default: return 'text-gray-600 bg-gray-50'
    }
  }

  const getActivityIcon = (type: string) => {
    switch (type) {
      case 'issue_resolved': return <CheckCircle className="h-5 w-5 text-green-600" />
      case 'approval_pending': return <Clock className="h-5 w-5 text-yellow-600" />
      case 'signal_detected': return <AlertCircle className="h-5 w-5 text-red-600" />
      case 'action_executed': return <Activity className="h-5 w-5 text-blue-600" />
      case 'pattern_detected': return <Activity className="h-5 w-5 text-purple-600" />
      default: return <Activity className="h-5 w-5 text-gray-600" />
    }
  }

  const formatTimeAgo = (timestamp: string) => {
    const seconds = Math.floor((Date.now() - new Date(timestamp).getTime()) / 1000)
    if (seconds < 60) return `${seconds}s ago`
    const minutes = Math.floor(seconds / 60)
    if (minutes < 60) return `${minutes}m ago`
    const hours = Math.floor(minutes / 60)
    return `${hours}h ago`
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Dashboard Overview</h1>
        <div className="text-sm text-gray-500">
          Last updated: {new Date().toLocaleTimeString()}
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div className="text-sm font-medium text-gray-500">Active Issues</div>
            <AlertCircle className="h-5 w-5 text-gray-400" />
          </div>
          <div className="mt-2 text-3xl font-bold text-gray-900">{stats.active_issues}</div>
          <div className="mt-2 flex items-center text-sm text-green-600">
            <TrendingDown className="h-4 w-4 mr-1" />
            {Math.abs(stats.active_issues_change)}% from last hour
          </div>
        </div>
        
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div className="text-sm font-medium text-gray-500">Pending Approvals</div>
            <Clock className="h-5 w-5 text-gray-400" />
          </div>
          <div className="mt-2 text-3xl font-bold text-gray-900">{stats.pending_approvals}</div>
          <div className="mt-2 text-sm text-yellow-600">Requires attention</div>
        </div>
        
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div className="text-sm font-medium text-gray-500">Deflection Rate</div>
            <CheckCircle className="h-5 w-5 text-gray-400" />
          </div>
          <div className="mt-2 text-3xl font-bold text-gray-900">{stats.deflection_rate}%</div>
          <div className="mt-2 flex items-center text-sm text-green-600">
            <TrendingUp className="h-4 w-4 mr-1" />
            {stats.deflection_rate_change}% from yesterday
          </div>
        </div>
        
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div className="text-sm font-medium text-gray-500">Avg Resolution Time</div>
            <Activity className="h-5 w-5 text-gray-400" />
          </div>
          <div className="mt-2 text-3xl font-bold text-gray-900">{stats.avg_resolution_time}m</div>
          <div className="mt-2 flex items-center text-sm text-green-600">
            <TrendingDown className="h-4 w-4 mr-1" />
            {Math.abs(stats.avg_resolution_time_change)}% improvement
          </div>
        </div>
      </div>

      {/* Secondary Stats */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Issue Breakdown</h2>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <div className="w-3 h-3 rounded-full bg-red-500 mr-2"></div>
                <span className="text-sm text-gray-700">Critical</span>
              </div>
              <span className="text-sm font-semibold text-gray-900">{stats.critical_issues}</span>
            </div>
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <div className="w-3 h-3 rounded-full bg-orange-500 mr-2"></div>
                <span className="text-sm text-gray-700">High Priority</span>
              </div>
              <span className="text-sm font-semibold text-gray-900">{stats.high_priority_issues}</span>
            </div>
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <div className="w-3 h-3 rounded-full bg-yellow-500 mr-2"></div>
                <span className="text-sm text-gray-700">Medium Priority</span>
              </div>
              <span className="text-sm font-semibold text-gray-900">{stats.medium_priority_issues}</span>
            </div>
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <div className="w-3 h-3 rounded-full bg-blue-500 mr-2"></div>
                <span className="text-sm text-gray-700">Low Priority</span>
              </div>
              <span className="text-sm font-semibold text-gray-900">{stats.low_priority_issues}</span>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Today's Activity</h2>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-700">Total Signals</span>
              <span className="text-sm font-semibold text-gray-900">{stats.total_signals_today}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-700">Issues Created</span>
              <span className="text-sm font-semibold text-gray-900">{stats.active_issues}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-700">Actions Executed</span>
              <span className="text-sm font-semibold text-gray-900">18</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-700">Approvals Processed</span>
              <span className="text-sm font-semibold text-gray-900">7</span>
            </div>
          </div>
        </div>
      </div>

      {/* Recent Activity */}
      <div className="bg-white rounded-lg shadow p-6 mb-8">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Recent Activity</h2>
        <div className="space-y-4">
          {recentActivity.map((activity) => (
            <div key={activity.id} className="flex items-start space-x-3 pb-4 border-b border-gray-100 last:border-0 last:pb-0">
              <div className="flex-shrink-0 mt-1">
                {getActivityIcon(activity.type)}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-900">{activity.title}</p>
                <p className="text-sm text-gray-500 mt-1">{activity.description}</p>
                <p className="text-xs text-gray-400 mt-1">{formatTimeAgo(activity.timestamp)}</p>
              </div>
              <div>
                <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getSeverityColor(activity.severity)}`}>
                  {activity.severity}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Active Issues Summary */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Active Issues</h2>
        <div className="space-y-3">
          {issues.filter(i => i.status === 'active' || i.status === 'pending_approval').map((issue) => (
            <div key={issue.issue_id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
              <div className="flex-1">
                <div className="flex items-center space-x-2">
                  <span className="text-sm font-medium text-gray-900">{issue.title}</span>
                  <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${getSeverityColor(issue.severity)}`}>
                    {issue.severity}
                  </span>
                </div>
                <p className="text-xs text-gray-500 mt-1">
                  {issue.signal_count} signals • {issue.pattern_type.replace('_', ' ')}
                </p>
              </div>
              <div className="text-right">
                <div className="text-xs text-gray-500">{formatTimeAgo(issue.updated_at)}</div>
                {issue.status === 'pending_approval' && (
                  <span className="text-xs text-yellow-600 font-medium">Pending Approval</span>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
