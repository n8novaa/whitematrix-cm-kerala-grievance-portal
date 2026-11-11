import { useEffect, useState } from 'react'
import { api, jsonRequest } from '../api'
import { Notice, PageIntro } from '../components/Layout'
import { Timeline } from './PublicPages'

const titleCase = (value = '') => value.toLowerCase().replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase())

function OfficerCase({ grievance, onUpdated }) {
  const [progress, setProgress] = useState('')
  const [shareProgress, setShareProgress] = useState(false)
  const [report, setReport] = useState('')
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState(false)
  async function submit(path, body, success) {
    setBusy(true); setError(''); setNotice('')
    try { await api(`/grievances/${grievance.id}/${path}/`, jsonRequest('POST', body)); setNotice(success); onUpdated() }
    catch (err) { setError(err.message) }
    finally { setBusy(false) }
  }
  return <article className="officer-case">
    <div className="officer-case-header"><div><p className="eyebrow">{grievance.reference_number} · {grievance.district || 'District not set'}</p><h2>{grievance.subject}</h2></div><span className={`status-pill status-${grievance.status.toLowerCase()}`}>{titleCase(grievance.status)}</span></div>
    <p className="detail-meta">{grievance.district || 'District not set'} · {grievance.category} · {grievance.department_name || 'Department'}</p><p className="detail-description">{grievance.description}</p>
    {grievance.assignment?.remarks && <div className="officer-instructions"><strong>Assignment instructions</strong><p>{grievance.assignment.remarks}</p></div>}
    {grievance.history?.some((item) => item.remarks && item.remarks !== grievance.assignment?.remarks) && <div className="officer-instructions"><strong>Progress notes</strong>{grievance.history.filter((item) => item.remarks && item.remarks !== grievance.assignment?.remarks).map((item, index) => <p key={`${item.created_at}-${index}`}>{item.remarks}</p>)}</div>}
    {error && <Notice kind="error">{error}</Notice>}{notice && <Notice kind="success">{notice}</Notice>}
    {grievance.status !== 'RESOLVED' && <div className="officer-actions"><form onSubmit={(event) => { event.preventDefault(); submit('updates', { remarks: progress, is_public: shareProgress }, shareProgress ? 'Citizen-visible progress update published.' : 'Internal progress note recorded.') }}><label>Investigation progress<textarea rows="3" value={progress} onChange={(event) => setProgress(event.target.value)} placeholder="Record what was checked or what happens next" required minLength={5} /></label><label className="checkbox-label"><input type="checkbox" checked={shareProgress} onChange={(event) => setShareProgress(event.target.checked)} /> Share this update with the citizen</label><button className="button button-outline button-small" disabled={busy || progress.trim().length < 5}>Add progress update</button></form>
      <form onSubmit={(event) => { event.preventDefault(); submit('action-reports', { report }, 'Action-taken report submitted for CMO review.') }}><label>Action-taken report<textarea rows="3" value={report} onChange={(event) => setReport(event.target.value)} placeholder="Describe the action completed and outcome" required minLength={10} /></label><button className="button button-small" disabled={busy || report.trim().length < 10}>Submit report</button></form></div>}
    {grievance.action_reports?.length > 0 && <div className="officer-report-list"><h3>Your submitted reports</h3>{grievance.action_reports.map((item) => <article className="report-card" key={item.id}><div className="report-heading"><strong>Submitted {new Date(item.created_at).toLocaleDateString()}</strong><span className={`status-pill status-${item.review_status.toLowerCase()}`}>{titleCase(item.review_status)}</span></div><p>{item.report}</p>{item.review_remarks && <div className="return-note"><strong>CMO review note</strong><p>{item.review_remarks}</p></div>}</article>)}</div>}
    <div className="detail-section"><h3>Case history</h3><Timeline history={grievance.history} /></div>
  </article>
}

export default function OfficerDashboard() {
  const [items, setItems] = useState([])
  const [selected, setSelected] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  async function load() {
    setLoading(true); setError('')
    try {
      const queue = await api('/grievances/officer/queue/')
      setItems(queue)
      setSelected((current) => current && queue.some((item) => String(item.id) === current) ? current : queue[0] ? String(queue[0].id) : '')
    } catch (err) { setError(err.message) }
    finally { setLoading(false) }
  }
  useEffect(() => {
    api('/grievances/officer/queue/')
      .then((queue) => { setItems(queue); setSelected(queue[0] ? String(queue[0].id) : '') })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [])
  const current = items.find((item) => String(item.id) === selected)
  return <div className="workspace-wrap">
    <PageIntro eyebrow="Department officer workspace" title="Assigned grievances" actions={<button className="button button-outline button-small" onClick={load}>Refresh queue</button>}>Record investigation progress and submit an action-taken report for CMO review.</PageIntro>
    {error && <Notice kind="error">{error}</Notice>}
    <div className="officer-workspace">
      <aside className="case-list"><div className="case-list-heading"><h2>My queue</h2><span>{items.length}</span></div>
        {loading ? <div className="loading-list"><span /><span /><span /></div> : items.length === 0 ? <div className="empty-state"><h3>Queue is clear</h3><p>No grievances are assigned to your account.</p></div> : items.map((item) => <button className={`case-list-item ${String(item.id) === selected ? 'selected' : ''}`} key={item.id} onClick={() => setSelected(String(item.id))}><span className="case-reference">{item.reference_number}</span><strong>{item.subject}</strong><small>{item.district || 'District not set'} · {item.category}</small><span className={`status-pill status-${item.status.toLowerCase()}`}>{titleCase(item.status)}</span></button>)}
      </aside>
      <div className="case-detail-area">{current ? <OfficerCase key={current.id} grievance={current} onUpdated={load} /> : <div className="empty-state"><span className="empty-icon">↖</span><h3>Select a grievance</h3><p>Choose a case from your assigned queue to review its details.</p></div>}</div>
    </div>
  </div>
}
