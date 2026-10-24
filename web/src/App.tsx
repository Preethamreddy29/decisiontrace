import { useEffect, useState } from 'react'

type Readiness = 'checking' | 'ready' | 'unavailable'

export default function App() {
  const [readiness, setReadiness] = useState<Readiness>('checking')
  const [version, setVersion] = useState('—')

  async function refresh() {
    setReadiness('checking')
    try {
      const [readyResponse, versionResponse] = await Promise.all([
        fetch('/api/health/ready', { cache: 'no-store' }),
        fetch('/api/version', { cache: 'no-store' }),
      ])
      if (!readyResponse.ok || !versionResponse.ok) throw new Error('Service unavailable')
      const versionData: { version: string } = await versionResponse.json()
      setVersion(versionData.version)
      setReadiness('ready')
    } catch {
      setReadiness('unavailable')
    }
  }

  useEffect(() => { void refresh() }, [])

  return (
    <main className="shell">
      <div className="eyebrow">LOCAL FOUNDATION · PHASE 2</div>
      <h1>DecisionTrace</h1>
      <p className="intro">A place to trace product decisions back to versioned evidence.</p>
      <section className="card" aria-label="Service readiness">
        <div>
          <span className="label">Service status</span>
          <div className={`status ${readiness}`} role="status">
            <span className="dot" />
            {readiness === 'checking' ? 'Checking…' : readiness === 'ready' ? 'Ready for foundation work' : 'Service unavailable'}
          </div>
        </div>
        <div>
          <span className="label">API version</span>
          <strong>{version}</strong>
        </div>
        <button type="button" onClick={() => void refresh()}>Check again</button>
      </section>
      <p className="note">The historical answer workflow is under development. This page confirms the local services only.</p>
    </main>
  )
}
