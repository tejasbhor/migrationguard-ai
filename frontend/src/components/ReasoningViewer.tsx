import { AlertCircle, CheckCircle, TrendingUp, Lightbulb, Target, AlertTriangle } from 'lucide-react'

interface ReasoningChainStep {
  stage: string
  timestamp: string
  data: any
  confidence?: number
  uncertainty?: string
}

interface ReasoningViewerProps {
  reasoningChain: ReasoningChainStep[]
  showUncertainty?: boolean
}

export function ReasoningViewer({ reasoningChain, showUncertainty = true }: ReasoningViewerProps) {
  const getStageIcon = (stage: string) => {
    switch (stage.toLowerCase()) {
      case 'signal':
      case 'signals':
        return <AlertCircle className="h-5 w-5 text-blue-600" />
      case 'pattern':
      case 'patterns':
        return <TrendingUp className="h-5 w-5 text-purple-600" />
      case 'root_cause':
      case 'analysis':
        return <Lightbulb className="h-5 w-5 text-yellow-600" />
      case 'decision':
        return <Target className="h-5 w-5 text-green-600" />
      default:
        return <CheckCircle className="h-5 w-5 text-gray-600" />
    }
  }

  const getStageColor = (stage: string) => {
    switch (stage.toLowerCase()) {
      case 'signal':
      case 'signals':
        return 'border-blue-200 bg-blue-50'
      case 'pattern':
      case 'patterns':
        return 'border-purple-200 bg-purple-50'
      case 'root_cause':
      case 'analysis':
        return 'border-yellow-200 bg-yellow-50'
      case 'decision':
        return 'border-green-200 bg-green-50'
      default:
        return 'border-gray-200 bg-gray-50'
    }
  }

  const formatConfidence = (confidence?: number) => {
    if (confidence === undefined) return null
    const percentage = (confidence * 100).toFixed(1)
    const color = confidence >= 0.8 ? 'text-green-600' : confidence >= 0.7 ? 'text-yellow-600' : 'text-red-600'
    return (
      <span className={`text-sm font-medium ${color}`}>
        Confidence: {percentage}%
      </span>
    )
  }

  const renderDataContent = (data: any) => {
    if (typeof data === 'string') {
      return <p className="text-sm text-gray-900">{data}</p>
    }

    if (Array.isArray(data)) {
      return (
        <ul className="space-y-2">
          {data.map((item, idx) => (
            <li key={idx} className="text-sm text-gray-900">
              {typeof item === 'object' ? (
                <pre className="text-xs bg-white p-2 rounded border border-gray-200 overflow-x-auto">
                  {JSON.stringify(item, null, 2)}
                </pre>
              ) : (
                String(item)
              )}
            </li>
          ))}
        </ul>
      )
    }

    if (typeof data === 'object' && data !== null) {
      // Special handling for common data structures
      if (data.signal_id || data.source) {
        return (
          <div className="space-y-2">
            {data.signal_id && (
              <div>
                <span className="text-xs font-medium text-gray-500">Signal ID:</span>
                <span className="text-sm text-gray-900 ml-2 font-mono">{data.signal_id}</span>
              </div>
            )}
            {data.source && (
              <div>
                <span className="text-xs font-medium text-gray-500">Source:</span>
                <span className="text-sm text-gray-900 ml-2">{data.source}</span>
              </div>
            )}
            {data.error_message && (
              <div>
                <span className="text-xs font-medium text-gray-500">Error:</span>
                <p className="text-sm text-gray-900 mt-1">{data.error_message}</p>
              </div>
            )}
            {data.merchant_id && (
              <div>
                <span className="text-xs font-medium text-gray-500">Merchant:</span>
                <span className="text-sm text-gray-900 ml-2">{data.merchant_id}</span>
              </div>
            )}
          </div>
        )
      }

      if (data.category || data.root_cause) {
        return (
          <div className="space-y-2">
            {data.category && (
              <div>
                <span className="text-xs font-medium text-gray-500">Category:</span>
                <span className="text-sm text-gray-900 ml-2">{data.category}</span>
              </div>
            )}
            {data.root_cause && (
              <div>
                <span className="text-xs font-medium text-gray-500">Root Cause:</span>
                <p className="text-sm text-gray-900 mt-1">{data.root_cause}</p>
              </div>
            )}
            {data.explanation && (
              <div>
                <span className="text-xs font-medium text-gray-500">Explanation:</span>
                <p className="text-sm text-gray-900 mt-1">{data.explanation}</p>
              </div>
            )}
            {data.alternatives && Array.isArray(data.alternatives) && (
              <div>
                <span className="text-xs font-medium text-gray-500">Alternatives Considered:</span>
                <ul className="mt-1 space-y-1">
                  {data.alternatives.map((alt: any, idx: number) => (
                    <li key={idx} className="text-sm text-gray-700 ml-4">
                      • {typeof alt === 'object' ? alt.description || JSON.stringify(alt) : alt}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )
      }

      if (data.action_type || data.rationale) {
        return (
          <div className="space-y-2">
            {data.action_type && (
              <div>
                <span className="text-xs font-medium text-gray-500">Action Type:</span>
                <span className="text-sm text-gray-900 ml-2">{data.action_type}</span>
              </div>
            )}
            {data.risk_level && (
              <div>
                <span className="text-xs font-medium text-gray-500">Risk Level:</span>
                <span className="text-sm text-gray-900 ml-2 capitalize">{data.risk_level}</span>
              </div>
            )}
            {data.rationale && (
              <div>
                <span className="text-xs font-medium text-gray-500">Rationale:</span>
                <p className="text-sm text-gray-900 mt-1">{data.rationale}</p>
              </div>
            )}
            {data.expected_outcome && (
              <div>
                <span className="text-xs font-medium text-gray-500">Expected Outcome:</span>
                <p className="text-sm text-gray-900 mt-1">{data.expected_outcome}</p>
              </div>
            )}
          </div>
        )
      }

      // Fallback to JSON display
      return (
        <pre className="text-xs bg-white p-3 rounded border border-gray-200 overflow-x-auto">
          {JSON.stringify(data, null, 2)}
        </pre>
      )
    }

    return <p className="text-sm text-gray-900">{String(data)}</p>
  }

  if (!reasoningChain || reasoningChain.length === 0) {
    return (
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-6 text-center">
        <p className="text-gray-500">No reasoning chain available</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {showUncertainty && reasoningChain.some(step => step.uncertainty) && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 flex items-start space-x-3">
          <AlertTriangle className="h-5 w-5 text-yellow-600 flex-shrink-0 mt-0.5" />
          <div>
            <h4 className="text-sm font-medium text-yellow-900 mb-1">Uncertainty Detected</h4>
            <p className="text-sm text-yellow-800">
              This decision contains uncertain elements. Review the reasoning chain carefully.
            </p>
          </div>
        </div>
      )}

      <div className="relative">
        {/* Timeline line */}
        <div className="absolute left-6 top-8 bottom-8 w-0.5 bg-gray-200"></div>

        {/* Reasoning steps */}
        <div className="space-y-6">
          {reasoningChain.map((step, index) => (
            <div key={index} className="relative">
              {/* Timeline dot */}
              <div className="absolute left-6 top-6 w-3 h-3 bg-white border-2 border-gray-400 rounded-full transform -translate-x-1/2"></div>

              {/* Step content */}
              <div className="ml-16">
                <div className={`border-2 rounded-lg p-4 ${getStageColor(step.stage)}`}>
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center space-x-3">
                      {getStageIcon(step.stage)}
                      <div>
                        <h3 className="text-sm font-semibold text-gray-900 capitalize">
                          {step.stage.replace(/_/g, ' ')}
                        </h3>
                        <p className="text-xs text-gray-500">
                          {new Date(step.timestamp).toLocaleString()}
                        </p>
                      </div>
                    </div>
                    {formatConfidence(step.confidence)}
                  </div>

                  <div className="mt-3">
                    {renderDataContent(step.data)}
                  </div>

                  {step.uncertainty && (
                    <div className="mt-3 pt-3 border-t border-yellow-300">
                      <div className="flex items-start space-x-2">
                        <AlertTriangle className="h-4 w-4 text-yellow-600 flex-shrink-0 mt-0.5" />
                        <div>
                          <span className="text-xs font-medium text-yellow-900">Uncertainty:</span>
                          <p className="text-sm text-yellow-800 mt-1">{step.uncertainty}</p>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
