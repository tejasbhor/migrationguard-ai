import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { ApprovalCard } from './ApprovalCard'
import type { PendingApproval } from '@/services/api'

const mockApproval: PendingApproval = {
  approval_id: 'approval-123',
  issue_id: 'issue-456',
  action_type: 'support_guidance',
  risk_level: 'high',
  parameters: {
    ticket_id: 'ticket-789',
    response: 'Please update your API key',
  },
  reasoning: {
    confidence: 0.85,
    rationale: 'High confidence in diagnosis',
  },
  created_at: '2026-02-01T10:00:00Z',
  merchant_id: 'merchant-123',
  priority: 'high',
}

describe('ApprovalCard', () => {
  it('renders approval information correctly', () => {
    const onApprove = vi.fn()
    const onReject = vi.fn()
    const onViewDetails = vi.fn()

    render(
      <ApprovalCard
        approval={mockApproval}
        onApprove={onApprove}
        onReject={onReject}
        onViewDetails={onViewDetails}
      />
    )

    expect(screen.getByText('Support Guidance')).toBeInTheDocument()
    expect(screen.getByText('HIGH RISK')).toBeInTheDocument()
    expect(screen.getByText('HIGH')).toBeInTheDocument()
    expect(screen.getByText(/merchant-123/)).toBeInTheDocument()
  })

  it('displays correct risk level styling for critical risk', () => {
    const criticalApproval = { ...mockApproval, risk_level: 'critical' as const }
    const { container } = render(
      <ApprovalCard
        approval={criticalApproval}
        onApprove={vi.fn()}
        onReject={vi.fn()}
        onViewDetails={vi.fn()}
      />
    )

    expect(screen.getByText('CRITICAL RISK')).toBeInTheDocument()
    expect(container.querySelector('.bg-red-50')).toBeInTheDocument()
  })

  it('calls onApprove when approve button is clicked', () => {
    const onApprove = vi.fn()
    const onReject = vi.fn()
    const onViewDetails = vi.fn()

    render(
      <ApprovalCard
        approval={mockApproval}
        onApprove={onApprove}
        onReject={onReject}
        onViewDetails={onViewDetails}
      />
    )

    const approveButton = screen.getByText('Approve')
    fireEvent.click(approveButton)

    expect(onApprove).toHaveBeenCalledTimes(1)
  })

  it('calls onReject when reject button is clicked', () => {
    const onApprove = vi.fn()
    const onReject = vi.fn()
    const onViewDetails = vi.fn()

    render(
      <ApprovalCard
        approval={mockApproval}
        onApprove={onApprove}
        onReject={onReject}
        onViewDetails={onViewDetails}
      />
    )

    const rejectButton = screen.getByText('Reject')
    fireEvent.click(rejectButton)

    expect(onReject).toHaveBeenCalledTimes(1)
  })

  it('calls onViewDetails when details button is clicked', () => {
    const onApprove = vi.fn()
    const onReject = vi.fn()
    const onViewDetails = vi.fn()

    render(
      <ApprovalCard
        approval={mockApproval}
        onApprove={onApprove}
        onReject={onReject}
        onViewDetails={onViewDetails}
      />
    )

    const detailsButton = screen.getByText('Details')
    fireEvent.click(detailsButton)

    expect(onViewDetails).toHaveBeenCalledTimes(1)
  })

  it('displays action parameters preview', () => {
    render(
      <ApprovalCard
        approval={mockApproval}
        onApprove={vi.fn()}
        onReject={vi.fn()}
        onViewDetails={vi.fn()}
      />
    )

    expect(screen.getByText('Action Parameters')).toBeInTheDocument()
    expect(screen.getByText(/ticket_id/)).toBeInTheDocument()
  })

  it('shows reasoning preview when reasoning exists', () => {
    render(
      <ApprovalCard
        approval={mockApproval}
        onApprove={vi.fn()}
        onReject={vi.fn()}
        onViewDetails={vi.fn()}
      />
    )

    expect(screen.getByText('Reasoning')).toBeInTheDocument()
    expect(screen.getByText('View reasoning chain →')).toBeInTheDocument()
  })
})
