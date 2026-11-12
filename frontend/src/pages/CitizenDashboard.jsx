import { useEffect, useMemo, useState } from 'react'
import { api, downloadGrievanceAttachment, jsonRequest } from '../api'
import { Notice, PageIntro } from '../components/Layout'
import { Timeline } from './PublicPages'

const DISTRICTS = ['Alappuzha', 'Ernakulam', 'Idukki', 'Kannur', 'Kasaragod', 'Kollam', 'Kottayam', 'Kozhikode', 'Malappuram', 'Palakkad', 'Pathanamthitta', 'Thiruvananthapuram', 'Thrissur', 'Wayanad']
const titleCase = (value = '') => value.toLowerCase().replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase())

function GrievanceForm({ onCreated, onDone }) {
  const [form, setForm] = useState({ district: '', category: '', subject: '', description: '' })
  const [files, setFiles] = useState([])
  const [suggestion, setSuggestion] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [submitted, setSubmitted] = useState(null)
  const [copied, setCopied] = useState(false)
  function update(event) { setForm((old) => ({ ...old, [event.target.name]: event.target.value })) }

  async function analyze() {
    setBusy(true); setError(''); setSuggestion(null)
    try {
      setSuggestion(await api('/ai/analyze/', jsonRequest('POST', { description: form.description })))
    } catch (err) {
      setError(err.status === 503 ? `${err.message} You can still submit without AI analysis.` : `${err.message} You can still submit without AI analysis.`)
    } finally { setBusy(false) }
  }

  async function submit(event) {
    event.preventDefault()
    setBusy(true); setError('')
    try {
      const payload = new FormData()
      Object.entries(form).forEach(([key, value]) => payload.append(key, value))
      if (suggestion?.recommendation_token) payload.append('ai_recommendation_token', suggestion.recommendation_token)
      files.forEach((file) => payload.append('attachments', file))
      const result = await api('/grievances/', { method: 'POST', body: payload })
      setSubmitted(result)
      setForm({ district: '', category: '', subject: '', description: '' }); setFiles([]); setSuggestion(null)
      onCreated(result)
    } catch (err) { setError(err.message) }
    finally { setBusy(false) }
  }

  if (submitted) return <section className="submission-success" aria-labelledby="submission-success-title">
    <span className="success-mark" aria-hidden="true">✓</span><p className="eyebrow">Submission received</p><h2 id="submission-success-title">Your grievance is on record.</h2>
    <p>Keep this reference number to check public status updates.</p>
    <div className="reference-copy"><code>{submitted.reference_number}</code><button className="button button-outline button-small" type="button" onClick={async () => { try { await navigator.clipboard.writeText(submitted.reference_number); setCopied(true) } catch { setCopied(false); setError('Copy is unavailable in this browser. Select the reference number to copy it.') } }}>Copy reference</button></div>
    {copied && <p className="copy-feedback" role="status">Reference number copied.</p>}{error && <Notice kind="error">{error}</Notice>}
    <p className="field-help">AI analysis, if used, is advisory only. Your reference identifies the official record in this prototype.</p>
    <div className="button-row"><button className="button" type="button" onClick={onDone}>View my grievances</button><button className="button button-outline" type="button" onClick={() => { setSubmitted(null); setCopied(false) }}>Submit another</button></div>
  </section>
  return <div className="submit-layout">
    <form className="form-card grievance-form" onSubmit={submit}>
      <p className="eyebrow">New grievance</p><h2>Tell us what happened</h2><p className="muted">Add enough detail to help the team understand the concern. Fields marked required must be completed.</p>
      {error && <Notice kind="error">{error}</Notice>}
      <div className="form-row"><label>District<select name="district" value={form.district} onChange={update} required><option value="">Choose a district</option>{DISTRICTS.map((district) => <option key={district}>{district}</option>)}</select></label><label>Category<input name="category" value={form.category} onChange={update} maxLength={80} placeholder="For example, roads" required /></label></div>
      <label>Subject<input name="subject" value={form.subject} onChange={update} maxLength={200} placeholder="A short description of the issue" required /></label>
      <label>Details<textarea name="description" value={form.description} onChange={update} rows="7" placeholder="Describe the location, what happened, and when you noticed it." required /></label>
      <div className="ai-tools"><div><strong>Optional AI suggestions</strong><p>Suggestions are advisory. You review and choose what to put in the form.</p></div><button className="button button-outline button-small" type="button" onClick={analyze} disabled={busy || form.description.trim().length < 20}>{busy ? 'Analyzing…' : 'Analyze details'}</button></div>
      {suggestion && <section className="suggestion-panel" aria-label="AI analysis suggestions"><div className="suggestion-heading"><span className="ai-spark" aria-hidden="true">✳</span><div><strong>AI suggestions</strong><small>Advisory output · Not an official decision</small></div></div>
        <div className="suggestion-values"><div><span>Suggested category</span><strong>{suggestion.category}</strong></div><div><span>Suggested priority</span><strong>{titleCase(suggestion.priority)}</strong></div><div><span>Suggested department</span><strong>{suggestion.department_code}</strong></div></div>
        <p className="suggestion-summary">{suggestion.summary}</p>
        <div className="human-review"><span className="review-check" aria-hidden="true">✓</span><span><strong>Official values are set by a human reviewer.</strong> Current category: {form.category || 'not selected'}. The submitted form uses your entered category and district; AI suggestions do not change official priority or department.</span></div>
        <button className="text-link text-button" type="button" onClick={() => setForm((old) => ({ ...old, category: suggestion.category }))}>Use suggested category</button>
      </section>}
      <label>Supporting files <span className="optional">(JPG, PNG or PDF, up to 5 MB each)</span><input type="file" accept=".jpg,.jpeg,.png,.pdf" multiple onChange={(event) => setFiles(Array.from(event.target.files || []))} /></label>
      {files.length > 0 && <p className="field-help">Selected: {files.map((file) => file.name).join(', ')}</p>}
      <button className="button" disabled={busy}>{busy ? 'Submitting…' : 'Submit grievance'}</button>
    </form>
    <aside className="side-note"><p className="eyebrow">Before you submit</p><h2>Keep your reference number</h2><p>It helps you return to the status page. The public tracker shows the status and public updates only.</p><hr /><p className="eyebrow">Prototype data</p><p>Use fictional details only. Do not upload real identity documents or sensitive personal information.</p></aside>
  </div>
}

function DetailPanel({ grievance, onChanged, feedbackSent, setFeedbackSent }) {
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [remarks, setRemarks] = useState('')
  const [rating, setRating] = useState(5)
  const [comments, setComments] = useState('')
  const [busy, setBusy] = useState(false)
  const feedbackCycle = grievance.current_resolution_cycle || 1
  const feedbackKey = `${grievance.id}:${feedbackCycle}`
  const currentFeedback = grievance.feedback?.resolution_cycle === feedbackCycle
  async function runAction(path, payload = {}) {
    setBusy(true); setError(''); setNotice('')
    try {
      const result = await api(`/grievances/${grievance.id}/${path}/`, jsonRequest('POST', payload))
      setNotice(path === 'reopen' ? 'Reopen request submitted. The status has been updated.' : 'Feedback saved. Thank you.')
      if (path === 'feedback') setFeedbackSent((old) => ({ ...old, [feedbackKey]: true }))
      if (path === 'reopen') { setRemarks(''); onChanged(result) }
    } catch (err) { setError(err.message) }
    finally { setBusy(false) }
  }
  async function download(attachment) {
    setError('')
    try { await downloadGrievanceAttachment(grievance.id, attachment) }
    catch (err) { setError(err.message) }
  }
  return <aside className="detail-panel">
    <div className="detail-heading"><div><p className="eyebrow">{grievance.reference_number}</p><h2>{grievance.subject}</h2></div><button className="icon-button" onClick={() => onChanged(null)} aria-label="Close grievance details">×</button></div>
    <span className={`status-pill status-${grievance.status.toLowerCase()}`}>{titleCase(grievance.status)}</span>
    <p className="detail-meta">{grievance.district || 'District not provided'} · {grievance.category}</p>
    <p className="detail-description">{grievance.description}</p>
    {error && <Notice kind="error">{error}</Notice>}{notice && <Notice kind="success">{notice}</Notice>}
    {grievance.attachments?.length > 0 && <div className="detail-section"><h3>Attachments</h3>{grievance.attachments.map((file) => <button className="file-link" key={file.id} onClick={() => download(file)}>↧ {file.original_name}</button>)}</div>}
    {grievance.status === 'RESOLVED' && <div className="detail-actions">
      {currentFeedback || feedbackSent[feedbackKey] ? <Notice kind="success">Feedback submitted for resolution {feedbackCycle}{currentFeedback ? ` · ${grievance.feedback.rating}/5` : ''}.</Notice> : <div className="feedback-box"><h3>How was the response?</h3><label>Rating<select value={rating} onChange={(event) => setRating(Number(event.target.value))}>{[5, 4, 3, 2, 1].map((value) => <option key={value} value={value}>{value} — {value === 5 ? 'Excellent' : value === 1 ? 'Needs improvement' : 'Good'}</option>)}</select></label><label>Comments <span className="optional">(optional)</span><textarea value={comments} onChange={(event) => setComments(event.target.value)} rows="2" /></label><button className="button button-small" disabled={busy} onClick={() => runAction('feedback', { rating, comments })}>Send feedback for this resolution</button></div>}
      <div className="feedback-box"><h3>Still needs attention?</h3><label>Reason to reopen<textarea value={remarks} onChange={(event) => setRemarks(event.target.value)} rows="2" placeholder="Explain what remains unresolved" /></label><button className="button button-outline button-small" disabled={busy || !remarks.trim()} onClick={() => runAction('reopen', { remarks })}>Reopen grievance</button></div>
    </div>}
    <div className="detail-section"><h3>Status history</h3><Timeline history={grievance.history} /></div>
  </aside>
}

export default function CitizenDashboard({ initialMode = 'list' }) {
  const [items, setItems] = useState([])
  const [selected, setSelected] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [filter, setFilter] = useState('ALL')
  const [mode, setMode] = useState(initialMode)
  const [feedbackSent, setFeedbackSent] = useState({})
  async function load() {
    setLoading(true); setError('')
    try { setItems(await api('/grievances/')) }
    catch (err) { setError(err.message) }
    finally { setLoading(false) }
  }
  useEffect(() => {
    api('/grievances/').then(setItems).catch((err) => setError(err.message)).finally(() => setLoading(false))
  }, [])
  const filtered = useMemo(() => items.filter((item) => filter === 'ALL' || item.status === filter), [items, filter])
  function replaceAfterAction(updated) {
    setSelected(updated)
    load()
  }
  const resolvedCount = items.filter((item) => item.status === 'RESOLVED').length
  const activeCount = items.length - resolvedCount
  return <div className="workspace-wrap">
    <PageIntro eyebrow="Citizen workspace" title={mode === 'submit' ? 'Submit a grievance' : 'Your grievances'} actions={<><button className={`tab-button ${mode === 'list' ? 'active' : ''}`} onClick={() => setMode('list')}>My cases</button><button className={`button button-small ${mode === 'submit' ? 'button-muted' : ''}`} onClick={() => setMode('submit')}>New grievance</button></>}>
      Follow the status and updates for concerns you have submitted in this prototype.
    </PageIntro>
    {mode === 'submit' ? <GrievanceForm onCreated={(item) => setItems((old) => [item, ...old])} onDone={() => setMode('list')} /> : <>
      {error && <Notice kind="error">{error}</Notice>}
      <div className="metric-row"><div className="metric-card"><span>Total submitted</span><strong>{items.length}</strong><small>All your grievance records</small></div><div className="metric-card"><span>In progress</span><strong>{activeCount}</strong><small>Awaiting or receiving action</small></div><div className="metric-card"><span>Resolved</span><strong>{resolvedCount}</strong><small>Responses ready to review</small></div></div>
      <section className="data-section"><div className="section-heading"><div><p className="eyebrow">Your record</p><h2>Recent grievances</h2></div><label className="filter-label">Filter<select value={filter} onChange={(event) => setFilter(event.target.value)}><option value="ALL">All statuses</option>{['SUBMITTED', 'UNDER_REVIEW', 'IN_PROGRESS', 'REOPENED', 'RESOLVED'].map((status) => <option key={status} value={status}>{titleCase(status)}</option>)}</select></label></div>
        {loading ? <div className="loading-list" aria-label="Loading grievances"><span /><span /><span /></div> : filtered.length === 0 ? <div className="empty-state"><span className="empty-icon" aria-hidden="true">＋</span><h3>{items.length ? 'No cases match this filter.' : 'No grievances yet'}</h3><p>{items.length ? 'Choose another status to see more.' : 'Submit your first grievance to begin tracking it here.'}</p>{!items.length && <button className="button button-small" onClick={() => setMode('submit')}>Submit a grievance</button>}</div> : <div className="table-scroll"><table><thead><tr><th>Reference</th><th>Subject</th><th>District</th><th>Status</th><th>Submitted</th><th><span className="sr-only">Actions</span></th></tr></thead><tbody>{filtered.map((item) => <tr key={item.id}><td className="ref-cell">{item.reference_number}</td><td><strong>{item.subject}</strong><small>{item.category}</small></td><td>{item.district || '—'}</td><td><span className={`status-pill status-${item.status.toLowerCase()}`}>{titleCase(item.status)}</span></td><td>{new Date(item.created_at).toLocaleDateString()}</td><td><button className="text-link text-button" onClick={() => setSelected(item)}>View details <span aria-hidden="true">→</span></button></td></tr>)}</tbody></table></div>}
      </section>
    </>}
    {selected && <div className="drawer-backdrop" onClick={(event) => { if (event.target === event.currentTarget) setSelected(null) }}><DetailPanel grievance={selected} onChanged={replaceAfterAction} feedbackSent={feedbackSent} setFeedbackSent={setFeedbackSent} /></div>}
  </div>
}
