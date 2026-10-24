import { useEffect, useState } from 'react'

type Citation = { label: string; kind: string; recorded_at: string; valid_from: string; valid_to: string | null; status: string; text: string }
type DemoAnswer = { status: string; answer: string; citations: Citation[]; corpus_version: string }
const examples = [
  { label: 'Known on 10 May', question: 'What manual-override policy was valid for Cedar on 10 May?', valid: '2026-05-10', recorded: '2026-05-10T23:59:59Z' },
  { label: 'Corrected record', question: 'What manual-override policy was valid for Cedar on 10 May?', valid: '2026-05-10', recorded: '2026-06-30T00:00:00Z' },
  { label: 'Current policy', question: 'What does the current approved policy say for Cedar?', valid: '2026-06-30', recorded: '2026-06-30T00:00:00Z' },
  { label: 'Correction timestamp', question: 'When did the corrected meeting record become known?', valid: '2026-05-10', recorded: '2026-06-30T00:00:00Z' },
  { label: 'Superseding decision', question: 'Which approved decision superseded the original?', valid: '2026-06-30', recorded: '2026-06-30T00:00:00Z' },
  { label: 'Implementation drift', question: 'Did the implementation test change after supersession?', valid: '2026-06-30', recorded: '2026-06-30T00:00:00Z' },
  { label: 'Conflicting draft', question: 'What unresolved contradiction exists?', valid: '2026-06-30', recorded: '2026-06-30T00:00:00Z' },
  { label: 'Missing evidence', question: 'Why was an undocumented exception allowed?', valid: '2026-06-30', recorded: '2026-06-30T00:00:00Z' },
]

export default function App() {
  const [ready, setReady] = useState('Checking…')
  const [selected, setSelected] = useState(0)
  const [result, setResult] = useState<DemoAnswer | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    void fetch('/api/health/ready', { cache: 'no-store' })
      .then(response => setReady(response.ok ? 'Ready' : 'Unavailable'))
      .catch(() => setReady('Unavailable'))
  }, [])

  async function run(index: number) {
    setSelected(index); setResult(null); setError(''); setLoading(true)
    const item = examples[index]
    try {
      const response = await fetch('/api/demo/query', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: item.question, tenant: 'cedar', role: 'auditor', valid_on: item.valid, recorded_as_of: item.recorded }),
      })
      if (!response.ok) throw new Error('The local demo query failed.')
      setResult(await response.json() as DemoAnswer)
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'The local demo query failed.') }
    finally { setLoading(false) }
  }

  return <main className="shell">
    <div className="eyebrow">DECISIONTRACE · SYNTHETIC DEMO</div>
    <h1>One decision. Two timelines.</h1>
    <p className="intro">See how a corrected meeting record changes what was known about a Cedar policy without changing when it applied.</p>
    <section className="status-card"><span>Local service</span><strong>{ready}</strong></section>
    <section className="demo-panel" aria-label="Historical answer demo">
      <div className="heading"><div><span className="eyebrow">HISTORICAL ANSWER</span><h2>Trace the override policy</h2></div><span className="pill">Fictional Cedar data</span></div>
      <div className="scenarios" role="group" aria-label="Demo scenarios">
        {examples.map((item, index) => <button key={item.label} type="button" className={selected === index ? 'selected' : ''} onClick={() => void run(index)}>{item.label}</button>)}
      </div>
      <div className="times"><div><span>Policy valid on</span><strong>{examples[selected].valid}</strong></div><div><span>Known as of</span><strong>{examples[selected].recorded.replace('T', ' ').replace('Z', ' UTC')}</strong></div></div>
      {loading && <p role="status">Reading permitted evidence…</p>}
      {error && <p className="error" role="alert">{error}</p>}
      {result && <div className="answer" aria-live="polite"><span className="eyebrow">{result.status === 'answered' ? 'EVIDENCE-BACKED ANSWER' : result.status.toUpperCase()}</span><p>{result.answer}</p><h3>Open the source versions</h3>
        {result.citations.length ? result.citations.map(citation => <details key={citation.label} className="evidence"><summary>{citation.label} <small>{citation.kind} · recorded {citation.recorded_at.slice(0, 10)}</small></summary><p>{citation.text}</p><small>Valid from {citation.valid_from}{citation.valid_to ? ` until ${citation.valid_to}` : ''} · {citation.status}</small></details>) : <p>No permitted supporting source is available.</p>}
        <small>Corpus: {result.corpus_version}</small></div>}
      {!result && !loading && !error && <p className="hint">Choose a scenario to see an answer and inspect its evidence.</p>}
    </section>
    <p className="note">This is a curated synthetic-data slice. Tenant and role values are scenario controls, not authentication. General search, production authorization, and RuleTwin integration are still under development.</p>
  </main>
}
