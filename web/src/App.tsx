import { useEffect, useState, type FormEvent } from 'react'

type Citation = { source_id: string; version_id: string; section_id: string; label: string; quote: string; start_char: number; end_char: number }
type Claim = { text: string; citations: Citation[] }
type Answer = { answer_id: string; status: 'answered' | 'conflict' | 'abstain' | 'denied'; claims: Claim[]; conflict_summary: string | null; abstention_reason: string | null; recorded_as_of: string; valid_on: string; corpus_or_index_version: string }
type Evidence = { external_label: string; kind: string; status: string; recorded_at: string; valid_from: string; valid_to: string | null; content: string; sha256: string }
type Session = { access_token: string; account: string; tenant: string; role: string }

const examples = [
  { label: 'Known on 10 May', question: 'How many reviewers did Cedar overrides require on May 10?', valid: '2026-05-10', known: '2026-05-10T23:59' },
  { label: 'Corrected record', question: 'How many reviewers did Cedar overrides require on May 10?', valid: '2026-05-10', known: '2026-06-30T00:00' },
  { label: 'After supersession', question: 'Can Cedar still use a manual override on May 21?', valid: '2026-05-21', known: '2026-06-30T00:00' },
  { label: 'Implementation drift', question: 'Does the active test still disagree with the approved override policy?', valid: '2026-06-30', known: '2026-06-30T00:00' },
  { label: 'Missing evidence', question: 'Why did an undocumented exception happen?', valid: '2026-06-30', known: '2026-06-30T00:00' },
]

async function message(response: Response): Promise<string> {
  try { const body: { title?: string } = await response.json(); return body.title || `Request failed (${response.status})` }
  catch { return `Request failed (${response.status})` }
}

export default function App() {
  const [ready, setReady] = useState('Checking…')
  const [account, setAccount] = useState('cedar_auditor')
  const [passphrase, setPassphrase] = useState('')
  const [session, setSession] = useState<Session | null>(null)
  const [question, setQuestion] = useState(examples[0].question)
  const [validOn, setValidOn] = useState(examples[0].valid)
  const [knownAt, setKnownAt] = useState(examples[0].known)
  const [answer, setAnswer] = useState<Answer | null>(null)
  const [evidence, setEvidence] = useState<Record<string, Evidence>>({})
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    void fetch('/api/health/ready', { cache: 'no-store' })
      .then(response => setReady(response.ok ? 'Ready' : 'Unavailable'))
      .catch(() => setReady('Unavailable'))
  }, [])

  async function login(event: FormEvent) {
    event.preventDefault(); setError(''); setBusy(true)
    try {
      const response = await fetch('/api/demo/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ account, passphrase }) })
      if (!response.ok) throw new Error(await message(response))
      setSession(await response.json() as Session); setPassphrase(''); setAnswer(null); setEvidence({})
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Login failed') }
    finally { setBusy(false) }
  }

  function choose(index: number) {
    const item = examples[index]
    setQuestion(item.question); setValidOn(item.valid); setKnownAt(item.known)
    setAnswer(null); setEvidence({}); setError('')
  }

  async function ask(event: FormEvent) {
    event.preventDefault(); if (!session) return
    setBusy(true); setError(''); setAnswer(null); setEvidence({})
    try {
      const response = await fetch('/api/v1/query', {
        method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${session.access_token}`, 'Idempotency-Key': crypto.randomUUID() },
        body: JSON.stringify({ question, valid_on: validOn, recorded_as_of: `${knownAt}:00Z`, answer_mode: 'structured' }),
      })
      if (!response.ok) throw new Error(await message(response))
      setAnswer(await response.json() as Answer)
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Query failed') }
    finally { setBusy(false) }
  }

  async function open(citation: Citation) {
    if (!session || !answer || evidence[citation.version_id]) return
    try {
      const url = `/api/v1/sources/${citation.source_id}/versions/${citation.version_id}?recorded_as_of=${encodeURIComponent(answer.recorded_as_of)}`
      const response = await fetch(url, { headers: { Authorization: `Bearer ${session.access_token}` }, cache: 'no-store' })
      if (!response.ok) throw new Error(await message(response))
      const item = await response.json() as Evidence
      setEvidence(current => ({ ...current, [citation.version_id]: item }))
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Could not open source') }
  }

  return <main className="shell">
    <div className="eyebrow">DECISIONTRACE · LOCAL SYNTHETIC DEMO</div>
    <h1>Ask what the evidence said.</h1>
    <p className="intro">Choose when a policy applied and what had been recorded by then. Every returned claim opens its exact source version.</p>
    <div className="status-card"><span>Local service</span><strong>{ready}</strong></div>

    {!session ? <section className="panel" aria-label="Demo sign in">
      <h2>Enter the local demo</h2>
      <p className="muted">These are fictional test identities. The shared local passphrase is <code>local-demo-only</code>.</p>
      <form onSubmit={event => void login(event)} className="login-form">
        <label>Demo identity<select value={account} onChange={event => setAccount(event.target.value)}><option value="cedar_auditor">Cedar auditor</option><option value="cedar_viewer">Cedar viewer</option><option value="lumen_auditor">Lumen auditor</option></select></label>
        <label>Passphrase<input type="password" value={passphrase} onChange={event => setPassphrase(event.target.value)} required /></label>
        <button type="submit" disabled={busy}>Enter demo</button>
      </form>
    </section> : <>
      <section className="identity"><div><span className="eyebrow">SIGNED-IN DEMO IDENTITY</span><strong>{session.tenant} · {session.role}</strong></div><button type="button" className="quiet" onClick={() => { setSession(null); setAnswer(null); setEvidence({}); setError('') }}>Switch identity</button></section>
      <section className="panel" aria-label="Decision query">
        <h2>Trace a decision</h2>
        <div className="examples" role="group" aria-label="Example questions">{examples.map((item, index) => <button type="button" className="chip" key={item.label} onClick={() => choose(index)}>{item.label}</button>)}</div>
        <form onSubmit={event => void ask(event)} className="query-form">
          <label>Question<textarea rows={3} value={question} onChange={event => { setQuestion(event.target.value); setAnswer(null) }} minLength={3} maxLength={2000} required /></label>
          <div className="time-grid"><label>Policy valid on<input type="date" value={validOn} onChange={event => { setValidOn(event.target.value); setAnswer(null) }} required /></label><label>Known as of (UTC)<input type="datetime-local" value={knownAt} onChange={event => { setKnownAt(event.target.value); setAnswer(null) }} required /></label></div>
          <button type="submit" disabled={busy || ready !== 'Ready'}>{busy ? 'Checking evidence…' : 'Ask DecisionTrace'}</button>
        </form>
      </section>
    </>}

    {error && <p className="error" role="alert">{error}</p>}
    {answer && <section className="panel result" aria-live="polite"><div className="result-head"><span className={`badge ${answer.status}`}>{answer.status}</span><small>Valid {answer.valid_on} · known {answer.recorded_as_of.replace('T', ' ').slice(0, 16)} UTC</small></div>
      {answer.conflict_summary && <p>{answer.conflict_summary}</p>}
      {answer.abstention_reason && <p>{answer.abstention_reason}</p>}
      {answer.claims.map((claim, claimIndex) => <article className="claim" key={`${answer.answer_id}-${claimIndex}`}><p>{claim.text}</p><div className="citations">{claim.citations.map(citation => <div className="citation" key={citation.version_id}><button type="button" className="source-button" onClick={() => void open(citation)}>{citation.label} · open exact source</button><blockquote>{citation.quote}</blockquote>
        {evidence[citation.version_id] && <div className="source-detail"><span className="eyebrow">AUTHORIZED SOURCE VERSION</span><p>{evidence[citation.version_id].content.slice(0, citation.start_char)}<mark>{evidence[citation.version_id].content.slice(citation.start_char, citation.end_char)}</mark>{evidence[citation.version_id].content.slice(citation.end_char)}</p><small>Recorded {evidence[citation.version_id].recorded_at} · valid from {evidence[citation.version_id].valid_from} · SHA-256 {evidence[citation.version_id].sha256.slice(0, 12)}…</small></div>}</div>)}</div></article>)}
      <small>Source set: {answer.corpus_or_index_version}. This resolver quotes source sentences and abstains outside supported decision questions.</small>
    </section>}
    <p className="note">Local fictional data and shared demo credentials only. Authorization is enforced by the API for these demo identities; this is not production authentication or general question answering.</p>
  </main>
}
