import { useState, useEffect } from 'react'
import { Activity, TrendingUp, Zap, Target, BarChart3 } from 'lucide-react'
import { mockMetrics } from '@/services/mockData'

export function Metrics() {
  const [metrics, setMetrics] = useState(mockMetrics)
  const [timeRange, setTimeRange] = useState<'1h' | '24h' | '7d' | '30d'>('24h')

  useEffect(() => {
    // Simulate real-time metric updates
    const interval = setInterval(() => {
      setMetrics(prev => ({
        ...prev,
        performance: {
          ...prev.performance,
          signal_ingestion_rate: prev.performance.signal_ingestion_rate + (Math.random() - 0.5) * 10,
          timestamp: new Date().toISOString(),
        },
      }))
    }, 5000)

    return () => clearInterval(interval)
  }, [])

  const formatNumber = (num: number, decimals: number = 0) => {
    return num.toFixed(decimals)
  }

  const formatPercentage = (num: number) => {
    return `${(num * 100).toFixed(1)}%`
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">System Metrics</h1>
        <div className="flex items-center space-x-2">
          {(['1h', '24h', '7d', '30d'] as const).map((range) => (
            <button
              key={range}
              onClick={() => setTimeRange(range)}
              className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                timeRange === range
                  ? 'bg-blue-600 text-white'
                  : 'bg-white text-gray-700 hover:bg-gray-50 border border-gray-300'
              }`}
            >
              {range}
            </button>
          ))}
        </div>
      </div>

      {/* Performance Metrics */}
      <div className="mb-8">
        <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
          <Zap className="h-5 w-5 mr-2 text-blue-600" />
          Performance Metrics
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-gray-500">Signal Ingestion Rate</span>
              <Activity className="h-5 w-5 text-gray-400" />
            </div>
            <div className="text-3xl font-bold text-gray-900">
              {formatNumber(metrics.performance.signal_ingestion_rate, 1)}
            </div>
            <div className="text-sm text-gray-500 mt-1">signals/minute</div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-gray-500">Processing Latency (P50)</span>
              <Activity className="h-5 w-5 text-gray-400" />
            </div>
            <div className="text-3xl font-bold text-gray-900">
              {formatNumber(metrics.performance.processing_latency_p50)}
            </div>
            <div className="text-sm text-gray-500 mt-1">milliseconds</div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-gray-500">Processing Latency (P95)</span>
              <Activity className="h-5 w-5 text-gray-400" />
            </div>
            <div className="text-3xl font-bold text-gray-900">
              {formatNumber(metrics.performance.processing_latency_p95)}
            </div>
            <div className="text-sm text-gray-500 mt-1">milliseconds</div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-gray-500">Processing Latency (P99)</span>
              <Activity className="h-5 w-5 text-gray-400" />
            </div>
            <div className="text-3xl font-bold text-gray-900">
              {formatNumber(metrics.performance.processing_latency_p99)}
            </div>
            <div className="text-sm text-gray-500 mt-1">milliseconds</div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-gray-500">Decision Accuracy</span>
              <Target className="h-5 w-5 text-gray-400" />
            </div>
            <div className="text-3xl font-bold text-gray-900">
              {formatPercentage(metrics.performance.decision_accuracy)}
            </div>
            <div className="text-sm text-green-600 mt-1 flex items-center">
              <TrendingUp className="h-4 w-4 mr-1" />
              Above target
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-gray-500">Action Success Rate</span>
              <Target className="h-5 w-5 text-gray-400" />
            </div>
            <div className="text-3xl font-bold text-gray-900">
              {formatPercentage(metrics.performance.action_success_rate)}
            </div>
            <div className="text-sm text-green-600 mt-1 flex items-center">
              <TrendingUp className="h-4 w-4 mr-1" />
              Excellent
            </div>
          </div>
        </div>
      </div>

      {/* Deflection Metrics */}
      <div className="mb-8">
        <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
          <BarChart3 className="h-5 w-5 mr-2 text-green-600" />
          Support Deflection Metrics
        </h2>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-sm font-semibold text-gray-900 mb-4">Overall Performance</h3>
            <div className="space-y-4">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-gray-600">Total Tickets</span>
                  <span className="text-lg font-bold text-gray-900">{metrics.deflection.total_tickets}</span>
                </div>
              </div>
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-gray-600">Deflected Tickets</span>
                  <span className="text-lg font-bold text-green-600">{metrics.deflection.deflected_tickets}</span>
                </div>
              </div>
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-gray-600">Deflection Rate</span>
                  <span className="text-2xl font-bold text-green-600">
                    {formatPercentage(metrics.deflection.deflection_rate)}
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-green-600 h-2 rounded-full transition-all"
                    style={{ width: `${metrics.deflection.deflection_rate * 100}%` }}
                  ></div>
                </div>
              </div>
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-gray-600">Avg Resolution Time</span>
                  <span className="text-lg font-bold text-blue-600">
                    {formatNumber(metrics.deflection.avg_resolution_time_minutes, 1)}m
                  </span>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-sm font-semibold text-gray-900 mb-4">Deflection by Category</h3>
            <div className="space-y-3">
              {Object.entries(metrics.deflection.by_category).map(([category, data]) => (
                <div key={category} className="border-b border-gray-100 pb-3 last:border-0 last:pb-0">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-gray-700 capitalize">{category}</span>
                    <span className="text-sm font-bold text-gray-900">
                      {formatPercentage(data.deflection_rate)}
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-xs text-gray-500 mb-1">
                    <span>{data.deflected} / {data.total} tickets</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-1.5">
                    <div
                      className={`h-1.5 rounded-full transition-all ${
                        data.deflection_rate > 0.9 ? 'bg-green-600' :
                        data.deflection_rate > 0.8 ? 'bg-blue-600' :
                        'bg-yellow-600'
                      }`}
                      style={{ width: `${data.deflection_rate * 100}%` }}
                    ></div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Confidence Calibration */}
      <div>
        <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
          <Target className="h-5 w-5 mr-2 text-purple-600" />
          AI Confidence Calibration
        </h2>
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-sm text-gray-600 mb-4">
            Measures how well the AI's confidence scores match actual accuracy. Perfect calibration means predicted confidence equals actual accuracy.
          </p>
          <div className="space-y-4">
            {metrics.confidence_calibration.map((bucket) => (
              <div key={bucket.confidence_bucket} className="border-b border-gray-100 pb-4 last:border-0 last:pb-0">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-gray-700">
                    Confidence: {bucket.confidence_bucket}
                  </span>
                  <span className="text-xs text-gray-500">
                    {bucket.sample_count} samples
                  </span>
                </div>
                <div className="grid grid-cols-3 gap-4 text-sm">
                  <div>
                    <div className="text-xs text-gray-500 mb-1">Predicted</div>
                    <div className="font-semibold text-gray-900">
                      {formatPercentage(bucket.predicted_confidence)}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-500 mb-1">Actual</div>
                    <div className="font-semibold text-gray-900">
                      {formatPercentage(bucket.actual_accuracy)}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-500 mb-1">Error</div>
                    <div className={`font-semibold ${
                      Math.abs(bucket.calibration_error) < 0.05 ? 'text-green-600' : 'text-yellow-600'
                    }`}>
                      {bucket.calibration_error > 0 ? '+' : ''}{formatPercentage(bucket.calibration_error)}
                    </div>
                  </div>
                </div>
                <div className="mt-2 flex space-x-2">
                  <div className="flex-1">
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div
                        className="bg-blue-600 h-2 rounded-full"
                        style={{ width: `${bucket.predicted_confidence * 100}%` }}
                      ></div>
                    </div>
                  </div>
                  <div className="flex-1">
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div
                        className="bg-green-600 h-2 rounded-full"
                        style={{ width: `${bucket.actual_accuracy * 100}%` }}
                      ></div>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
          <div className="mt-4 p-3 bg-green-50 rounded-lg">
            <p className="text-sm text-green-800">
              ✓ Overall calibration is excellent. The AI's confidence scores are well-aligned with actual performance.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
