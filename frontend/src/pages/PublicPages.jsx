import { useEffect, useState } from 'react'
import { api, jsonRequest } from '../api'
import { Notice, PageIntro } from '../components/Layout'

const titleCase = (value = '') => value.toLowerCase().replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase())

function HomePage({ user }) {
  const [departments, setDepartments] = useState([])
  useEffect(() => { api('/departments/').then(setDepartments).catch(() => setDepartments([])) }, [])
  return <>
    <section className="home-hero">
      <div className="hero-copy">
        <p className="eyebrow"><span className="live-dot" /> A demonstration of public service follow-up</p>
        <h1>Every concern deserves a clear next step.</h1>
        <p className="hero-description">A simple place to submit a grievance, keep its reference, and follow updates as it moves through review.</p>
        <div className="hero-actions"><a className="button" href={user?.role === 'CITIZEN' ? '/submit' : user ? '/dashboard' : '/register'}>{user && user.role !== 'CITIZEN' ? 'Open workspace' : 'Submit a grievance'} <span aria-hidden="true">→</span></a><a className="text-link" href="/track">Track a grievance <span aria-hidden="true">↗</span></a></div>
        <p className="prototype-note">Recruitment prototype using fictional demo data · Not an official government service</p>
      </div>
      <div className="hero-panel" aria-label="Grievance status example">
        <div className="panel-topline"><span>DEMO TRACKING</span><span className="status-pill status-progress">In progress</span></div>
        <p className="tracking-number">CMK-2026-A18C42F0123456789ABCDEFFEDCBA987</p>
        <h2>Streetlight outage near the community hall</h2>
        <div className="mini-timeline"><span className="timeline-dot done" /><div><strong>Submitted</strong><small>Reference created</small></div><time>10 Nov</time></div>
        <div className="mini-timeline"><span className="timeline-dot done" /><div><strong>Under review</strong><small>Department assigned</small></div><time>11 Nov</time></div>
        <div className="mini-timeline"><span className="timeline-dot active" /><div><strong>Work in progress</strong><small>Next update will appear here</small></div><time>Now</time></div>
        <a href="/track" className="panel-link">See how tracking works <span aria-hidden="true">→</span></a>
      </div>
    </section>
    <section className="home-info">
      <div><p className="eyebrow">Built around follow-through</p><h2>A clear record from submission to response.</h2></div>
      <div className="info-steps"><article><span>01</span><h3>Tell us what happened</h3><p>Share the subject, details, and any useful files. Keep your reference number safe.</p></article><article><span>02</span><h3>Follow the progress</h3><p>See the current status and public updates attached to your grievance.</p></article><article><span>03</span><h3>Review the response</h3><p>When a case is marked resolved, share feedback or request that it be reopened.</p></article></div>
    </section>
    <section className="home-stats" aria-label="Illustrative prototype statistics"><p className="eyebrow">Prototype snapshot · Illustrative sample data</p><div className="sample-stat-grid"><article><strong>14</strong><span>Kerala districts represented</span></article><article><strong>3</strong><span>Workflow stages before resolution</span></article><article><strong>1</strong><span>Reference to track each case</span></article></div><small>These figures describe the demonstration and are not live government statistics.</small></section>
    <section className="featured-departments"><div className="section-heading"><div><p className="eyebrow">Across the workflow</p><h2>Featured departments</h2><p className="muted">Sample departments used in this prototype.</p></div><a className="text-link" href="/departments">Browse directory <span aria-hidden="true">→</span></a></div><div className="department-grid">{departments.slice(0, 3).map((department) => <article className="department-card" key={department.id}><span className="dept-code">{department.code}</span><h3>{department.name}</h3><p>{department.description}</p></article>)}</div>{departments.length === 0 && <p className="muted">Department examples are unavailable while the directory is offline.</p>}</section>
    <section className="home-callout"><div><p className="eyebrow">Prototype notice</p><h2>This service is a fictional demonstration.</h2><p>It is not connected to a government department and must not be used for real complaints or personal data.</p></div><a className="button button-outline" href="/about">About this prototype</a></section>
  </>
}

function DepartmentsPage() {
  const [departments, setDepartments] = useState([])
  const [error, setError] = useState('')
  useEffect(() => { api('/departments/').then(setDepartments).catch((err) => setError(err.message)) }, [])
  return <div className="content-wrap"><PageIntro eyebrow="Directory" title="Departments">Fictional departments available in the demonstration workflow.</PageIntro>
    {error && <Notice kind="error">{error}</Notice>}
    <div className="department-grid">{departments.map((department) => <article className="department-card" key={department.id}><span className="dept-code">{department.code}</span><h2>{department.name}</h2><p>{department.description}</p></article>)}</div>
    {!departments.length && !error && <p className="muted">Loading departments…</p>}
  </div>
}

function ContactPage() {
  const [form, setForm] = useState({ name: '', email: '', subject: '', message: '' })
  const [state, setState] = useState({ busy: false, error: '', success: false })
  function update(event) { setForm((old) => ({ ...old, [event.target.name]: event.target.value })) }
  async function submit(event) {
    event.preventDefault()
    setState({ busy: true, error: '', success: false })
    try {
      await api('/grievances/contact-enquiries/', jsonRequest('POST', form))
      setState({ busy: false, error: '', success: true })
      setForm({ name: '', email: '', subject: '', message: '' })
    } catch (err) { setState({ busy: false, error: err.message, success: false }) }
  }
  return <div className="content-wrap"><PageIntro eyebrow="Contact" title="Send a prototype enquiry">This form stores a demonstration enquiry. Do not include sensitive or real personal information.</PageIntro>
    <div className="contact-layout"><form className="form-card" onSubmit={submit}>
      {state.error && <Notice kind="error">{state.error}</Notice>}{state.success && <Notice kind="success">Your enquiry has been saved in the prototype.</Notice>}
      <div className="form-row"><label>Name<input name="name" value={form.name} onChange={update} required maxLength={120} /></label><label>Email<input type="email" name="email" value={form.email} onChange={update} required /></label></div>
      <label>Subject<input name="subject" value={form.subject} onChange={update} required maxLength={200} /></label>
      <label>Message<textarea name="message" value={form.message} onChange={update} rows="5" required /></label>
      <button className="button" disabled={state.busy}>{state.busy ? 'Sending…' : 'Send enquiry'}</button>
    </form><aside className="side-note"><p className="eyebrow">Please remember</p><h2>Demonstration only</h2><p>This is not a government contact channel. The enquiry is stored only as sample prototype data.</p></aside></div>
  </div>
}

function TrackingPage({ initialReference = '' }) {
  const [reference, setReference] = useState(initialReference)
  const [record, setRecord] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  async function lookup(event) {
    event.preventDefault()
    if (!reference.trim()) return
    setBusy(true); setError(''); setRecord(null)
    try { setRecord(await api(`/grievances/track/${encodeURIComponent(reference.trim())}/`)) }
    catch (err) { setError(err.status === 404 ? 'We could not find that reference. Check it and try again.' : err.message) }
    finally { setBusy(false) }
  }
  useEffect(() => {
    if (!initialReference) return
    api(`/grievances/track/${encodeURIComponent(initialReference)}/`)
      .then(setRecord)
      .catch((err) => setError(err.status === 404 ? 'We could not find that reference. Check it and try again.' : err.message))
      .finally(() => setBusy(false))
  }, [initialReference])
  return <div className="content-wrap"><PageIntro eyebrow="Public tracking" title="Track a grievance">Enter the reference number to see the current status and public updates. The description and attachments stay private.</PageIntro>
    <form className="track-form" onSubmit={lookup}><label htmlFor="tracking-reference">Reference number</label><div><input id="tracking-reference" value={reference} onChange={(event) => setReference(event.target.value)} placeholder="CMK-2026-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX" required /><button className="button" disabled={busy}>{busy ? 'Searching…' : 'Find grievance'}</button></div></form>
    {error && <Notice kind="error">{error}</Notice>}
    {record && <section className="tracking-result"><div className="result-heading"><div><p className="eyebrow">{record.reference_number}</p><h2>{record.subject}</h2></div><span className={`status-pill status-${record.status.toLowerCase()}`}>{titleCase(record.status)}</span></div>
      <p className="result-meta">{record.category} <span>·</span> Submitted {new Date(record.created_at).toLocaleDateString()}</p>
      <p className="tracking-summary">Department: <strong>{record.department_name || 'Under initial review'}</strong></p>
      <h3>Public status history</h3>
      <Timeline history={record.history} />
    </section>}
  </div>
}

export function Timeline({ history = [] }) {
  if (!history.length) return <p className="muted">No status updates have been published yet.</p>
  return <ol className="timeline">{history.map((item, index) => <li key={`${item.created_at}-${index}`}><span className="timeline-dot done" /><div><strong>{titleCase(item.new_status)}</strong>{item.remarks && <p>{item.remarks}</p>}<time>{new Date(item.created_at).toLocaleString()}</time></div></li>)}</ol>
}

export default function PublicPages({ page, user }) {
  if (page === '/') return <HomePage user={user} />
  if (page === '/about') return <div className="content-wrap"><PageIntro eyebrow="About the prototype" title="A public service journey, made easier to follow.">People’s Desk is a fictional recruitment prototype that demonstrates an accountable grievance workflow and clear communication at each step.</PageIntro><div className="notice notice-warning">This is not an official Government of Kerala website or service. Do not submit real grievances or personal information.</div><section className="about-grid"><article><p className="eyebrow">Purpose</p><h2>Make each next step visible.</h2><p>Show how a concern can move from citizen submission through review, department action, and a recorded response.</p></article><article><p className="eyebrow">Vision</p><h2>Public follow-up people can understand.</h2><p>A service experience where people know a case has been received, who is acting on it, and what happened next.</p></article><article><p className="eyebrow">Mission</p><h2>Keep the record clear and accountable.</h2><p>Demonstrate role-based review, visible status history, reasoned report decisions, and a safe way to share updates.</p></article><article><p className="eyebrow">Objectives</p><h2>What this prototype demonstrates</h2><ul><li>Reference-based grievance tracking</li><li>CMO review and department assignment</li><li>Officer progress and action reports</li><li>Human review of advisory AI suggestions</li></ul></article></section></div>
  if (page === '/how-it-works') return <div className="content-wrap"><PageIntro eyebrow="Complete grievance lifecycle" title="Every role has a clear next step.">Citizens submit and track a case, the CMO reviews and assigns it, and the assigned officer investigates and reports back. The CMO reviews the latest action report before resolving the case; citizens can then leave feedback or reopen it if needed.</PageIntro><div className="notice notice-warning">This is a fictional prototype, not an official Government of Kerala service. Use fictional information only.</div><div className="info-steps detail-steps"><article><span>01 · CITIZEN</span><h3>Submit and follow up</h3><p>Register, submit a grievance, keep its reference, view public status history and attachments, give feedback after resolution, or request reopening with a reason.</p></article><article><span>02 · CMO</span><h3>Review and coordinate</h3><p>Review a submitted or reopened case, assign a department and officer, publish public updates, record internal notes, review reports, escalate when needed, and resolve only after accepting the latest report.</p></article><article><span>03 · DEPARTMENT OFFICER</span><h3>Investigate and report</h3><p>Work only on active assignments, record internal notes or citizen-visible updates, and submit an action-taken report for CMO review.</p></article><article><span>04 · STATUS PATH</span><h3>Five recorded statuses</h3><p>Submitted → Under Review → In Progress → Resolved. If the citizen reopens a resolved case, it moves through Reopened → Under Review → In Progress and needs a new accepted report before resolution again.</p></article></div><section className="notice notice-info"><strong>AI is advisory.</strong> Gemini may suggest a department, category, priority, and summary. A human CMO decides whether to accept or override those suggestions; AI never routes or resolves a grievance.</section></div>
  if (page === '/faq') return <div className="content-wrap"><PageIntro eyebrow="Frequently asked questions" title="A few useful answers">This prototype demonstrates the grievance workflow with fictional test data.</PageIntro><div className="faq-list"><details><summary>Is this an official Government of Kerala service?</summary><p>No. It is a recruitment prototype and is not operated by or endorsed by the Government of Kerala.</p></details><details><summary>Can I submit a real grievance?</summary><p>No. Use fictional information only. This prototype is not connected to public authorities.</p></details><details><summary>What is the reference number for?</summary><p>It lets you return to the public tracking page to see current status and public status history.</p></details><details><summary>What does the AI analysis do?</summary><p>When configured, it suggests a category, priority, department, and summary. A person reviews all suggestions; AI does not assign, reject, or resolve a case.</p></details><details><summary>Why is AI analysis unavailable?</summary><p>The live model requires a configured provider key. The grievance workflow remains usable when the provider is not configured.</p></details></div></div>
  if (page === '/departments') return <DepartmentsPage />
  if (page === '/contact') return <ContactPage />
  if (page === '/track' || page.startsWith('/track/')) return <TrackingPage initialReference={page.startsWith('/track/') ? decodeURIComponent(page.slice('/track/'.length)) : ''} />
  return null
}
