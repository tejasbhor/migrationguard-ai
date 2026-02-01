import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { Layout } from './Layout'

describe('Layout', () => {
  it('renders navigation items', () => {
    render(
      <BrowserRouter>
        <Layout />
      </BrowserRouter>
    )

    expect(screen.getByText('Dashboard')).toBeInTheDocument()
    expect(screen.getByText('Signal Feed')).toBeInTheDocument()
    expect(screen.getByText('Approvals')).toBeInTheDocument()
    expect(screen.getByText('Issues')).toBeInTheDocument()
    expect(screen.getByText('Metrics')).toBeInTheDocument()
    expect(screen.getByText('Settings')).toBeInTheDocument()
  })

  it('renders MigrationGuard AI title', () => {
    render(
      <BrowserRouter>
        <Layout />
      </BrowserRouter>
    )

    expect(screen.getByText('MigrationGuard AI')).toBeInTheDocument()
  })

  it('renders user profile section', () => {
    render(
      <BrowserRouter>
        <Layout />
      </BrowserRouter>
    )

    expect(screen.getByText('Operator')).toBeInTheDocument()
    expect(screen.getByText('Admin')).toBeInTheDocument()
  })

  it('renders system status indicator', () => {
    render(
      <BrowserRouter>
        <Layout />
      </BrowserRouter>
    )

    expect(screen.getByText(/System Online/i)).toBeInTheDocument()
  })

  it('renders outlet for child routes', () => {
    const { container } = render(
      <BrowserRouter>
        <Layout />
      </BrowserRouter>
    )

    // Check that the main content area exists
    const mainContent = container.querySelector('main')
    expect(mainContent).toBeInTheDocument()
  })
})
