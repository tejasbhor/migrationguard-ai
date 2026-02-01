import type { Signal } from '@/services/api'
import { X } from 'lucide-react'

interface SignalDetailModalProps {
  signal: Signal | null
  onClose: () => void
}

export function SignalDetailModal({ signal, onClose }: SignalDetailModalProps) {
  if (!signal) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-3xl w-full max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <h2 className="text-xl font-semibold text-gray-900">Signal Details</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <X className="h-6 w-6" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[calc(90vh-80px)]">
          <div className="space-y-6">
            {/* Basic Info */}
            <div>
              <h3 className="text-sm font-medium text-gray-500 mb-3">Basic Information</h3>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-xs text-gray-500">Signal ID</label>
                  <p className="text-sm font-mono text-gray-900">{signal.signal_id}</p>
                </div>
                <div>
                  <label className="text-xs text-gray-500">Timestamp</label>
                  <p className="text-sm text-gray-900">
                    {new Date(signal.timestamp).toLocaleString()}
                  </p>
                </div>
                <div>
                  <label className="text-xs text-gray-500">Source</label>
                  <p className="text-sm text-gray-900">{signal.source}</p>
                </div>
                <div>
                  <label className="text-xs text-gray-500">Severity</label>
                  <p className="text-sm text-gray-900 capitalize">{signal.severity}</p>
                </div>
                <div>
                  <label className="text-xs text-gray-500">Merchant ID</label>
                  <p className="text-sm text-gray-900">{signal.merchant_id}</p>
                </div>
                {signal.migration_stage && (
                  <div>
                    <label className="text-xs text-gray-500">Migration Stage</label>
                    <p className="text-sm text-gray-900">{signal.migration_stage}</p>
                  </div>
                )}
              </div>
            </div>

            {/* Error Details */}
            {(signal.error_message || signal.error_code || signal.affected_resource) && (
              <div>
                <h3 className="text-sm font-medium text-gray-500 mb-3">Error Details</h3>
                <div className="space-y-3">
                  {signal.error_message && (
                    <div>
                      <label className="text-xs text-gray-500">Error Message</label>
                      <p className="text-sm text-gray-900">{signal.error_message}</p>
                    </div>
                  )}
                  {signal.error_code && (
                    <div>
                      <label className="text-xs text-gray-500">Error Code</label>
                      <p className="text-sm font-mono text-gray-900">{signal.error_code}</p>
                    </div>
                  )}
                  {signal.affected_resource && (
                    <div>
                      <label className="text-xs text-gray-500">Affected Resource</label>
                      <p className="text-sm text-gray-900">{signal.affected_resource}</p>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Context */}
            {Object.keys(signal.context).length > 0 && (
              <div>
                <h3 className="text-sm font-medium text-gray-500 mb-3">Context</h3>
                <pre className="text-xs bg-gray-50 p-4 rounded-lg overflow-x-auto">
                  {JSON.stringify(signal.context, null, 2)}
                </pre>
              </div>
            )}

            {/* Raw Data */}
            <div>
              <h3 className="text-sm font-medium text-gray-500 mb-3">Raw Data</h3>
              <pre className="text-xs bg-gray-50 p-4 rounded-lg overflow-x-auto">
                {JSON.stringify(signal.raw_data, null, 2)}
              </pre>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
