import { useEffect, useState, type FormEvent } from 'react'

type Citation = { source_id: string; version_id: string; section_id: string; label: string; quote: string; start_char: number; end_char: number }
type Claim = { text: string; citations: Citation[]; decision_version_id?: string }
type Answer = { answer_id: string; status: 'answered' | 'conflict' | 'abstain' | 'denied'; claims: Claim[]; conflict_summary: string | null; abstention_reason: string | null; recorded_as_of: string; valid_on: string; corpus_or_index_version: string }
type Evidence = { external_label: string; kind: string; status: string; recorded_at: string; valid_from: string; valid_to: string | null; content: string; sha256: string }
type Session = { access_token: string; account: string; tenant: string; role: string }
type WorkflowSource = { source_id: string; version_id: string; version: number; kind: string; status: string; external_label: string; content: string; origin: string; created_by: string; valid_from: string; recorded_at: string; sha256: string; etag: string; superseded_at: string | null }
type Decision = { decision_id: string; version_id: string; version: number; title: string; status: string; valid_from: string; recorded_at: string; owner_id: string; approver_id: string | null; evidence_version_ids: string[]; etag: string }

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
  const [sources, setSources] = useState<WorkflowSource[]>([])
  const [decisions, setDecisions] = useState<Decision[]>([])
  const [decisionHistory, setDecisionHistory] = useState<Record<string, Decision[]>>({})
  const [selectedSource, setSelectedSource] = useState('')
  const [history, setHistory] = useState<WorkflowSource[]>([])
  const [sourceOrigin, setSourceOrigin] = useState('Fictional Cedar policy note')
  const [sourceContent, setSourceContent] = useState('Manual overrides require three independent reviewers for Cedar invoices starting July 1.')
  const [sourceValidFrom, setSourceValidFrom] = useState('2026-07-01')
  const [decisionTitle, setDecisionTitle] = useState('Manual overrides require three reviewers from July 1')
  const [workflowNotice, setWorkflowNotice] = useState('')

  useEffect(() => {
    void fetch('/api/health/ready', { cache: 'no-store' })
      .then(response => setReady(response.ok ? 'Ready' : 'Unavailable'))
      .catch(() => setReady('Unavailable'))
  }, [])

  useEffect(() => { if (session) void refreshWorkflow(session) }, [session])

  async function authorized(path: string, options: RequestInit = {}, active = session): Promise<Response> {
    if (!active) throw new Error('Sign in first')
    return fetch(`/api${path}`, {
      ...options,
      headers: { Authorization: `Bearer ${active.access_token}`, ...(options.headers || {}) },
      cache: 'no-store',
    })
  }

  async function refreshWorkflow(active = session) {
    if (!active) return
    try {
      const sourceResponse = await authorized('/v1/sources', {}, active)
      if (!sourceResponse.ok) throw new Error(await message(sourceResponse))
      const nextSources = await sourceResponse.json() as WorkflowSource[]
      setSources(nextSources)
      if (active.role === 'auditor' || active.role === 'owner') {
        const decisionResponse = await authorized('/v1/decision-contracts', {}, active)
        if (!decisionResponse.ok) throw new Error(await message(decisionResponse))
        setDecisions(await decisionResponse.json() as Decision[])
      } else setDecisions([])
      if (selectedSource) {
        const historyResponse = await authorized(`/v1/sources/${selectedSource}/versions`, {}, active)
        setHistory(historyResponse.ok ? await historyResponse.json() as WorkflowSource[] : [])
      }
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Could not load workflow') }
  }

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
        body: JSON.stringify({ question, valid_on: validOn, recorded_as_of: `${knownAt}${knownAt.length === 16 ? ':00' : ''}Z`, answer_mode: 'structured' }),
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

  async function selectSource(sourceId: string) {
    setSelectedSource(sourceId); setHistory([]); setWorkflowNotice('')
    const source = sources.find(item => item.source_id === sourceId)
    if (source) { setSourceOrigin(source.origin); setSourceContent(source.content); setSourceValidFrom(source.valid_from) }
    if (!sourceId) return
    try {
      const response = await authorized(`/v1/sources/${sourceId}/versions`)
      if (!response.ok) throw new Error(await message(response))
      setHistory(await response.json() as WorkflowSource[])
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Could not load source history') }
  }

  async function saveSource(append = false) {
    if (!session) return
    const current = sources.find(item => item.source_id === selectedSource)
    if (append && !current) return
    setBusy(true); setError(''); setWorkflowNotice('')
    try {
      const response = await authorized(append ? `/v1/sources/${selectedSource}/versions` : '/v1/sources', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Idempotency-Key': crypto.randomUUID(), ...(append ? { 'If-Match': current!.etag } : {}) },
        body: JSON.stringify({ kind: 'markdown', origin: sourceOrigin, content: sourceContent, valid_from: sourceValidFrom, permissions: ['auditor', 'owner'] }),
      })
      if (!response.ok) throw new Error(await message(response))
      const saved = await response.json() as WorkflowSource
      setSelectedSource(saved.source_id)
      setWorkflowNotice(`${saved.external_label} saved. Its earlier version remains in history.`)
      await refreshWorkflow()
      const historyResponse = await authorized(`/v1/sources/${saved.source_id}/versions`)
      if (historyResponse.ok) setHistory(await historyResponse.json() as WorkflowSource[])
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Could not save source') }
    finally { setBusy(false) }
  }

  async function createDraft() {
    if (!session) return
    const current = sources.find(item => item.source_id === selectedSource)
    if (!current) { setError('Choose or add a source first'); return }
    setBusy(true); setError(''); setWorkflowNotice('')
    try {
      const response = await authorized('/v1/decision-contracts', {
        method: 'POST', headers: { 'Content-Type': 'application/json', 'Idempotency-Key': crypto.randomUUID() },
        body: JSON.stringify({ title: decisionTitle, valid_from: sourceValidFrom, evidence_version_ids: [current.version_id] }),
      })
      if (!response.ok) throw new Error(await message(response))
      const draft = await response.json() as Decision
      setWorkflowNotice(`Draft ${draft.decision_id.slice(0, 8)} created. Switch to another Cedar auditor identity to review it.`)
      await refreshWorkflow()
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Could not create draft') }
    finally { setBusy(false) }
  }

  async function review(decision: Decision, action: 'approve' | 'reject') {
    setBusy(true); setError(''); setWorkflowNotice('')
    try {
      const response = await authorized(`/v1/decision-contracts/${decision.decision_id}/review`, {
        method: 'POST', headers: { 'Content-Type': 'application/json', 'Idempotency-Key': crypto.randomUUID(), 'If-Match': decision.etag },
        body: JSON.stringify({ action }),
      })
      if (!response.ok) throw new Error(await message(response))
      const reviewed = await response.json() as Decision
      setWorkflowNotice(`Decision ${reviewed.status}. Ask again with a recorded-time cutoff after this review.`)
      if (action === 'approve') {
        setQuestion(`What does the approved manual override policy require for ${session?.tenant} on ${reviewed.valid_from}?`)
        setValidOn(reviewed.valid_from)
        setKnownAt(new Date(new Date(reviewed.recorded_at).getTime() + 1000).toISOString().slice(0, 19))
        setAnswer(null)
      }
      await refreshWorkflow()
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Could not review decision') }
    finally { setBusy(false) }
  }

  async function showDecisionHistory(decisionId: string) {
    try {
      const response = await authorized(`/v1/decision-contracts/${decisionId}/history`)
      if (!response.ok) throw new Error(await message(response))
      const versions = await response.json() as Decision[]
      setDecisionHistory(current => ({ ...current, [decisionId]: versions }))
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Could not load decision history') }
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
        <label>Demo identity<select value={account} onChange={event => setAccount(event.target.value)}><option value="cedar_auditor">Cedar author / auditor</option><option value="cedar_reviewer">Cedar independent reviewer</option><option value="cedar_viewer">Cedar viewer</option><option value="lumen_auditor">Lumen auditor</option></select></label>
        <label>Passphrase<input type="password" value={passphrase} onChange={event => setPassphrase(event.target.value)} required /></label>
        <button type="submit" disabled={busy}>Enter demo</button>
      </form>
    </section> : <>
      <section className="identity"><div><span className="eyebrow">SIGNED-IN DEMO IDENTITY</span><strong>{session.tenant} · {session.role} · {session.account}</strong></div><button type="button" className="quiet" onClick={() => { setSession(null); setAnswer(null); setEvidence({}); setSources([]); setDecisions([]); setDecisionHistory({}); setHistory([]); setSelectedSource(''); setError('') }}>Switch identity</button></section>
      <section className="panel" aria-label="Decision query">
        <h2>Trace a decision</h2>
        <div className="examples" role="group" aria-label="Example questions">{examples.map((item, index) => <button type="button" className="chip" key={item.label} onClick={() => choose(index)}>{item.label}</button>)}</div>
        <form onSubmit={event => void ask(event)} className="query-form">
          <label>Question<textarea rows={3} value={question} onChange={event => { setQuestion(event.target.value); setAnswer(null) }} minLength={3} maxLength={2000} required /></label>
          <div className="time-grid"><label>Policy valid on<input type="date" value={validOn} onChange={event => { setValidOn(event.target.value); setAnswer(null) }} required /></label><label>Known as of (UTC)<input type="datetime-local" step="1" value={knownAt} onChange={event => { setKnownAt(event.target.value); setAnswer(null) }} required /></label></div>
          <button type="submit" disabled={busy || ready !== 'Ready'}>{busy ? 'Checking evidence…' : 'Ask DecisionTrace'}</button>
        </form>
      </section>
      {(session.role === 'auditor' || session.role === 'owner') && <section className="panel workflow" aria-label="Evidence and decision workflow">
        <div className="workflow-heading"><div><span className="eyebrow">V0.3 · GOVERNED WORKFLOW</span><h2>Take new evidence through review</h2></div><span className="badge">Local fictional data</span></div>
        <p className="muted">Add a policy note, save a corrected version if needed, create a decision draft, then switch to a different Cedar auditor to approve it. The answer changes only after approval.</p>
        <div className="workflow-grid">
          <div className="workflow-step"><span className="step-number">1</span><h3>Source and version</h3>
            <label>Existing source<select value={selectedSource} onChange={event => void selectSource(event.target.value)}><option value="">Create a new source</option>{sources.map(item => <option value={item.source_id} key={item.source_id}>{item.external_label} · {item.origin}</option>)}</select></label>
            <form onSubmit={event => { event.preventDefault(); void saveSource() }} className="workflow-form">
              <label>Origin<input value={sourceOrigin} onChange={event => setSourceOrigin(event.target.value)} maxLength={500} required /></label>
              <label>Policy valid from<input type="date" value={sourceValidFrom} onChange={event => setSourceValidFrom(event.target.value)} required /></label>
              <label>Exact source text<textarea rows={4} value={sourceContent} onChange={event => setSourceContent(event.target.value)} minLength={15} maxLength={10000} required /></label>
              <div className="button-row"><button type="submit" disabled={busy}>Add source</button><button type="button" className="quiet" disabled={busy || !selectedSource} onClick={() => void saveSource(true)}>Save corrected version</button></div>
            </form>
            {history.length > 0 && <div className="history"><strong>Source history</strong>{history.map(item => <div className="history-item" key={item.version_id}><small>{item.external_label} · recorded {item.recorded_at.replace('T', ' ').slice(0, 16)} UTC · {item.superseded_at ? 'earlier version' : 'current'}</small><p>{item.content}</p></div>)}</div>}
          </div>
          <div className="workflow-step"><span className="step-number">2</span><h3>Draft and review</h3>
            <label>Decision statement<input value={decisionTitle} onChange={event => setDecisionTitle(event.target.value)} maxLength={300} minLength={8} /></label>
            <p className="muted">The draft binds the current source version. It cannot become approved without another identity.</p>
            <button type="button" disabled={busy || !selectedSource} onClick={() => void createDraft()}>Create decision draft</button>
            <div className="history"><strong>Decisions</strong>{decisions.length === 0 && <p className="muted">No decisions yet for this tenant.</p>}{decisions.map(item => <div className="history-item" key={item.decision_id}><div className="decision-row"><span className={`badge ${item.status}`}>{item.status}</span><small>v{item.version} · {item.valid_from}</small></div><p>{item.title}</p><small>Evidence version {item.evidence_version_ids[0]?.slice(0, 8)} · recorded {item.recorded_at.replace('T', ' ').slice(0, 16)} UTC</small><div className="button-row"><button type="button" className="quiet" onClick={() => void showDecisionHistory(item.decision_id)}>View version history</button>{item.status === 'draft' && <><button type="button" disabled={busy} onClick={() => void review(item, 'approve')}>Approve</button><button type="button" className="quiet" disabled={busy} onClick={() => void review(item, 'reject')}>Reject</button></>}</div>{decisionHistory[item.decision_id] && <div className="version-list">{decisionHistory[item.decision_id].map(version => <p key={version.version_id}><strong>v{version.version} · {version.status}</strong><small>Recorded {version.recorded_at.replace('T', ' ').slice(0, 16)} UTC · {version.approver_id ? `reviewer ${version.approver_id.slice(0, 8)}` : `author ${version.owner_id.slice(0, 8)}`}</small></p>)}</div>}</div>)}</div>
          </div>
        </div>
        {workflowNotice && <p className="success" role="status">{workflowNotice}</p>}
      </section>}
    </>}

    {error && <p className="error" role="alert">{error}</p>}
    {answer && <section className="panel result" aria-live="polite"><div className="result-head"><span className={`badge ${answer.status}`}>{answer.status}</span><small>Valid {answer.valid_on} · known {answer.recorded_as_of.replace('T', ' ').slice(0, 16)} UTC</small></div>
      {answer.conflict_summary && <p>{answer.conflict_summary}</p>}
      {answer.abstention_reason && <p>{answer.abstention_reason}</p>}
      {answer.claims.map((claim, claimIndex) => <article className="claim" key={`${answer.answer_id}-${claimIndex}`}><p>{claim.text}</p>{claim.decision_version_id && <small>Approved decision version {claim.decision_version_id.slice(0, 8)}</small>}<div className="citations">{claim.citations.map(citation => <div className="citation" key={citation.version_id}><button type="button" className="source-button" onClick={() => void open(citation)}>{citation.label} · open exact source</button><blockquote>{citation.quote}</blockquote>
        {evidence[citation.version_id] && <div className="source-detail"><span className="eyebrow">AUTHORIZED SOURCE VERSION</span><p>{evidence[citation.version_id].content.slice(0, citation.start_char)}<mark>{evidence[citation.version_id].content.slice(citation.start_char, citation.end_char)}</mark>{evidence[citation.version_id].content.slice(citation.end_char)}</p><small>Recorded {evidence[citation.version_id].recorded_at} · valid from {evidence[citation.version_id].valid_from} · SHA-256 {evidence[citation.version_id].sha256.slice(0, 12)}…</small></div>}</div>)}</div></article>)}
      <small>Source set: {answer.corpus_or_index_version}. This resolver quotes source sentences and abstains outside supported decision questions.</small>
    </section>}
    <p className="note">Local fictional data and shared demo credentials only. Authorization is enforced by the API for these demo identities; this is not production authentication or general question answering.</p>
  </main>
}
