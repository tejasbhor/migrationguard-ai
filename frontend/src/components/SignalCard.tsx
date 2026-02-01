import type { Signal } from '@/services/api'
import { AlertCircle, AlertTriangle, Info, XCircle } from 'lucide-react'

interface SignalCardProps {
  signal: Signal
  onClick?: () => void
}

const severityConfig = {
  critical: {
    icon: XCircle,
    bgColor: 'bg-red-50',
    borderColor: 'border-red-200',
    textColor: 'text-red-700',
    iconColor: 'text-red-500',
  },
  high: {
    icon: AlertCircle,
    bgColor: 'bg-orange-50',
    borderColor: 'border-orange-200',
    textColor: 'text-orange-700',
    iconColor: 'text-orange-500',
  },
  medium: {
    icon: AlertTriangle,
    bgColor: 'bg-yellow-50',
    borderColor: 'border-yellow-200',
    textColor: 'text-yellow-700',
    iconColor: 'text-yellow-500',
  },
  low: {
    icon: Info,
    bgColor: 'bg-blue-50',
    borderColor: 'border-blue-200',
    textColor: 'text-blue-700',
    iconColor: 'text-blue-500',
  },
}

const sourceLabels = {
  support_ticket: 'Support Ticket',
  api_failure: 'API Failure',
  checkout_error: 'Checkout Error',
  webhook_failure: 'Webhook Failure',
}

export function SignalCard({ signal, onClick }: SignalCardProps) {
  const config = severityConfig[signal.severity]
  const Icon = config.icon
  const timestamp = new Date(signal.timestamp).toLocaleString()

  return (
    <div
      onClick={onClick}
      className={`
        ${config.bgColor} ${config.borderColor} border rounded-lg p-4 
        cursor-pointer hover:shadow-md transition-shadow
      `}
    >
      <div className="flex items-start justify-between">
        <div className="flex items-start space-x-3 flex-1">
          <Icon className={`${config.iconColor} h-5 w-5 mt-0.5`} />
          <div className="flex-1 min-w-0">
            <div className="flex items-center space-x-2 mb-1">
              <span className={`text-xs font-medium ${config.textColor} uppercase`}>
                {signal.severity}
              </span>
              <span className="text-xs text-gray-500">•</span>
              <span className="text-xs text-gray-600">
                {sourceLabels[signal.source]}
              </span>
            </div>
            
            <p className="text-sm font-medium text-gray-900 mb-1">
              {signal.error_message || 'No error message'}
            </p>
            
            <div className="flex items-center space-x-4 text-xs text-gray-500">
              <span>Merchant: {signal.merchant_id}</span>
              {signal.error_code && <span>Code: {signal.error_code}</span>}
              {signal.affected_resource && <span>Resource: {signal.affected_resource}</span>}
            </div>
          </div>
        </div>
        
        <div className="text-xs text-gray-500 ml-4 whitespace-nowrap">
          {timestamp}
        </div>
      </div>
    </div>
  )
}
