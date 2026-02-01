import { useState, useEffect } from 'react'
import { Search, RefreshCw } from 'lucide-react'
import type { Signal, SignalSearchParams } from '@/services/api'
import { SignalCard } from '@/components/SignalCard'
import { SignalDetailModal } from '@/components/SignalDetailModal'
import { mockSignals, generateNewSignal } from '@/services/mockData'

export function SignalFeed() {
  const [signals, setSignals] = useState<Signal[]>(mockSignals)
  const [loading, setLoading] = useState(false)
  const [selectedSignal, setSelectedSignal] = useState<Signal | null>(null)
  const [searchParams, setSearchParams] = useState<SignalSearchParams>({
    limit: 50,
    offset: 0,
  })
  const [filters, setFilters] = useState({
    source: '',
    severity: '',
    merchant_id: '',
  })

  const loadSignals = async () => {
    setLoading(true)
    try {
      // Simulate API delay
      await new Promise(resolve => setTimeout(resolve, 500))
      
      // Filter signals based on search params
      let filteredSignals = [...mockSignals]
      
      if (filters.source) {
        filteredSignals = filteredSignals.filter(s => s.source === filters.source)
      }
      if (filters.severity) {
        filteredSignals = filteredSignals.filter(s => s.severity === filters.severity)
      }
      if (filters.merchant_id) {
        filteredSignals = filteredSignals.filter(s => 
          s.merchant_id.toLowerCase().includes(filters.merchant_id.toLowerCase())
        )
      }
      
      setSignals(filteredSignals)
    } catch (error) {
      console.error('Failed to load signals:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadSignals()
    
    // Simulate real-time signal updates
    const interval = setInterval(() => {
      if (Math.random() > 0.7) { // 30% chance of new signal
        const newSignal = generateNewSignal()
        setSignals(prev => [newSignal, ...prev].slice(0, 50))
      }
    }, 10000) // Every 10 seconds
    
    return () => clearInterval(interval)
  }, [searchParams])

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    loadSignals()
  }

  const handleReset = () => {
    setFilters({ source: '', severity: '', merchant_id: '' })
    setSearchParams({ limit: 50, offset: 0 })
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Signal Feed</h1>
        <button
          onClick={loadSignals}
          disabled={loading}
          className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow p-4 mb-6">
        <form onSubmit={handleSearch} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Source
              </label>
              <select
                value={filters.source}
                onChange={(e) => setFilters({ ...filters, source: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">All Sources</option>
                <option value="support_ticket">Support Ticket</option>
                <option value="api_failure">API Failure</option>
                <option value="checkout_error">Checkout Error</option>
                <option value="webhook_failure">Webhook Failure</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Severity
              </label>
              <select
                value={filters.severity}
                onChange={(e) => setFilters({ ...filters, severity: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">All Severities</option>
                <option value="critical">Critical</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Merchant ID
              </label>
              <input
                type="text"
                value={filters.merchant_id}
                onChange={(e) => setFilters({ ...filters, merchant_id: e.target.value })}
                placeholder="Search merchant..."
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div className="flex items-end space-x-2">
              <button
                type="submit"
                className="flex-1 flex items-center justify-center space-x-2 px-4 py-2 bg-gray-900 text-white rounded-md hover:bg-gray-800 transition-colors"
              >
                <Search className="h-4 w-4" />
                <span>Search</span>
              </button>
              <button
                type="button"
                onClick={handleReset}
                className="px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 transition-colors"
              >
                Reset
              </button>
            </div>
          </div>
        </form>
      </div>

      {/* Signal List */}
      <div className="space-y-3">
        {loading && signals.length === 0 ? (
          <div className="bg-white rounded-lg shadow p-8 text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
            <p className="mt-4 text-gray-500">Loading signals...</p>
          </div>
        ) : signals.length === 0 ? (
          <div className="bg-white rounded-lg shadow p-8 text-center">
            <p className="text-gray-500">No signals found</p>
          </div>
        ) : (
          signals.map((signal) => (
            <SignalCard
              key={signal.signal_id}
              signal={signal}
              onClick={() => setSelectedSignal(signal)}
            />
          ))
        )}
      </div>

      {/* Signal Detail Modal */}
      <SignalDetailModal
        signal={selectedSignal}
        onClose={() => setSelectedSignal(null)}
      />
    </div>
  )
}
