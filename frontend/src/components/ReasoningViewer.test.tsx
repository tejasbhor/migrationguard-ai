import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ReasoningViewer } from './ReasoningViewer'

const mockReasoningChain = [
  {
    stage: 'signals',
    timestamp: '2026-02-01T10:00:00Z',
    data: {
      signal_id: 'sig-001',
      source: 'api_failure',
      error_message: 'Authentication failed',
    },
    confidence: 1.0,
  },
  {
    stage: 'root_cause',
    timestamp: '2026-02-01T10:01:00Z',
    data: {
      category: 'migration_misstep',
      root_cause: 'API key format changed',
      explanation: 'The merchant is using old API key format',
      alternatives: ['Platform regression', 'Configuration error'],
    },
    confidence: 0.85,
  },
  {
    stage: 'decision',
    timestamp: '2026-02-01T10:02:00Z',
    data: {
      action_type: 'support_guidance',
      risk_level: 'low',
      rationale: 'Can be resolved with guidance',
    },
    confidence: 0.90,
    uncertainty: 'Low confidence due to limited data',
  },
]

describe('ReasoningViewer', () => {
  it('renders reasoning chain steps', () => {
    render(<ReasoningViewer reasoningChain={mockReasoningChain} />)

    // Use getAllByText for elements that appear multiple times
    const signalsElements = screen.getAllByText(/signals/i)
    expect(signalsElements.length).toBeGreaterThan(0)
    
    const rootCauseElements = screen.getAllByText(/root cause/i)
    expect(rootCauseElements.length).toBeGreaterThan(0)
    
    const decisionElements = screen.getAllByText(/decision/i)
    expect(decisionElements.length).toBeGreaterThan(0)
  })

  it('displays confidence scores', () => {
    render(<ReasoningViewer reasoningChain={mockReasoningChain} />)

    expect(screen.getByText('Confidence: 100.0%')).toBeInTheDocument()
    expect(screen.getByText('Confidence: 85.0%')).toBeInTheDocument()
    expect(screen.getByText('Confidence: 90.0%')).toBeInTheDocument()
  })

  it('shows uncertainty warnings when present', () => {
    render(<ReasoningViewer reasoningChain={mockReasoningChain} />)

    expect(screen.getByText('Uncertainty Detected')).toBeInTheDocument()
    expect(screen.getByText('Low confidence due to limited data')).toBeInTheDocument()
  })

  it('displays signal data correctly', () => {
    render(<ReasoningViewer reasoningChain={mockReasoningChain} />)

    expect(screen.getByText('sig-001')).toBeInTheDocument()
    expect(screen.getByText('api_failure')).toBeInTheDocument()
    expect(screen.getByText('Authentication failed')).toBeInTheDocument()
  })

  it('shows alternatives considered', () => {
    render(<ReasoningViewer reasoningChain={mockReasoningChain} />)

    expect(screen.getByText('Alternatives Considered:')).toBeInTheDocument()
    expect(screen.getByText(/Platform regression/)).toBeInTheDocument()
    expect(screen.getByText(/Configuration error/)).toBeInTheDocument()
  })

  it('renders empty state when no reasoning chain provided', () => {
    render(<ReasoningViewer reasoningChain={[]} />)

    expect(screen.getByText('No reasoning chain available')).toBeInTheDocument()
  })

  it('hides uncertainty warning when showUncertainty is false', () => {
    render(<ReasoningViewer reasoningChain={mockReasoningChain} showUncertainty={false} />)

    expect(screen.queryByText('Uncertainty Detected')).not.toBeInTheDocument()
  })

  it('displays timestamps for each step', () => {
    render(<ReasoningViewer reasoningChain={mockReasoningChain} />)

    // Check that timestamps are rendered (format may vary by locale)
    const timestamps = screen.getAllByText(/2\/1\/2026|2026/)
    expect(timestamps.length).toBeGreaterThan(0)
  })
})
