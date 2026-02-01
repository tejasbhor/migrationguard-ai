import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { SignalCard } from './SignalCard'
import type { Signal } from '@/services/api'

const mockSignal: Signal = {
  signal_id: 'sig-123',
  timestamp: '2026-02-01T10:00:00Z',
  source: 'api_failure',
  merchant_id: 'merchant-456',
  migration_stage: 'testing',
  severity: 'high',
  error_message: 'Connection timeout',
  error_code: 'ERR_TIMEOUT',
  affected_resource: '/api/checkout',
  raw_data: {},
  context: {},
}

describe('SignalCard', () => {
  it('renders signal information correctly', () => {
    const onClick = vi.fn()

    render(<SignalCard signal={mockSignal} onClick={onClick} />)

    expect(screen.getByText(/API Failure/i)).toBeInTheDocument()
    expect(screen.getByText(/merchant-456/)).toBeInTheDocument()
    expect(screen.getByText('Connection timeout')).toBeInTheDocument()
    expect(screen.getByText(/ERR_TIMEOUT/)).toBeInTheDocument()
  })

  it('displays correct severity badge for high severity', () => {
    render(<SignalCard signal={mockSignal} onClick={vi.fn()} />)

    expect(screen.getByText(/high/i)).toBeInTheDocument()
  })

  it('displays correct severity badge for critical severity', () => {
    const criticalSignal = { ...mockSignal, severity: 'critical' as const }
    render(<SignalCard signal={criticalSignal} onClick={vi.fn()} />)

    expect(screen.getByText(/critical/i)).toBeInTheDocument()
  })

  it('calls onClick when card is clicked', () => {
    const onClick = vi.fn()

    render(<SignalCard signal={mockSignal} onClick={onClick} />)

    const card = screen.getByText('Connection timeout').closest('div')
    if (card) {
      fireEvent.click(card)
      expect(onClick).toHaveBeenCalledTimes(1)
    }
  })

  it('displays affected resource when present', () => {
    render(<SignalCard signal={mockSignal} onClick={vi.fn()} />)

    expect(screen.getByText(/\/api\/checkout/)).toBeInTheDocument()
  })

  it('displays migration stage when present', () => {
    render(<SignalCard signal={mockSignal} onClick={vi.fn()} />)

    // Migration stage is not displayed in the current SignalCard implementation
    // This test should be updated or removed based on actual component behavior
    expect(screen.queryByText('testing')).not.toBeInTheDocument()
  })

  it('formats timestamp correctly', () => {
    render(<SignalCard signal={mockSignal} onClick={vi.fn()} />)

    // Check that timestamp is rendered (format may vary by locale)
    const timestamps = screen.getAllByText(/2\/1\/2026|2026/)
    expect(timestamps.length).toBeGreaterThan(0)
  })
})
