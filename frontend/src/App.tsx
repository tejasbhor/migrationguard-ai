import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { Layout } from '@/components/Layout'
import { Dashboard } from '@/pages/Dashboard'
import { SignalFeed } from '@/pages/SignalFeed'
import { Approvals } from '@/pages/Approvals'
import { Issues } from '@/pages/Issues'
import { Metrics } from '@/pages/Metrics'
import { Settings } from '@/pages/Settings'

function App() {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/signals" element={<SignalFeed />} />
          <Route path="/approvals" element={<Approvals />} />
          <Route path="/issues" element={<Issues />} />
          <Route path="/metrics" element={<Metrics />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </Layout>
    </Router>
  )
}

export default App
