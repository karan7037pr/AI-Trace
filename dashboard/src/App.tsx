import { Link, Route, Routes } from 'react-router-dom'
import OverviewPage from './pages/OverviewPage'
import TraceDetailPage from './pages/TraceDetailPage'
import DemoPage from './pages/DemoPage'

export default function App() {
  return (
    <div className="app-shell">
      <header className="topbar">
        <Link className="brand" to="/">
          <span className="brand-mark">✦</span>
          <span>AITrace</span>
          <span className="brand-tag">RAG OBSERVABILITY</span>
        </Link>
        <div className="connection-pill"><span className="pulse-dot" /> local telemetry</div>
      </header>
      <main className="page-container">
        <Routes>
          <Route path="/" element={<DemoPage />} />
          <Route path="/observability" element={<OverviewPage />} />
          <Route path="/traces/:traceId" element={<TraceDetailPage />} />
        </Routes>
      </main>
    </div>
  )
}
