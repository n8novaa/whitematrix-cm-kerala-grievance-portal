import { useCallback, useEffect, useRef, useState } from 'react'
import { api, downloadGrievanceAttachment, jsonRequest } from '../api'
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
  const latestReport = [...(grievance.action_reports || [])].sort((a, b) => new Date(a.created_at) - new Date(b.created_at) || a.id - b.id).at(-1)
  const reportPending = latestReport?.review_status === 'PENDING'
  const reportReturned = latestReport?.review_status === 'RETURNED'
  const internalNotes = (grievance.history || []).filter((item) => item.is_internal && item.remarks && item.remarks !== grievance.assignment?.remarks)
  const publicUpdates = (grievance.history || []).filter((item) => !item.is_internal && item.remarks)
  async function submit(path, body, success) {
    setBusy(true); setError(''); setNotice('')
    try { await api(`/grievances/${grievance.id}/${path}/`, jsonRequest('POST', body)); setNotice(success); onUpdated() }
    catch (err) { setError(err.message) }
    finally { setBusy(false) }
  }
  async function download(attachment) {
    setError('')
    try { await downloadGrievanceAttachment(grievance.id, attachment) }
    catch (err) { setError(err.message) }
  }
  return <article className="officer-case">
    <div className="officer-case-header"><div><p className="eyebrow">{grievance.reference_number} · {grievance.district || 'District not set'}</p><h2>{grievance.subject}</h2></div><span className={`status-pill status-${grievance.status.toLowerCase()}`}>{titleCase(grievance.status)}</span></div>
    <p className="detail-meta">{grievance.district || 'District not set'} · {grievance.category} · {grievance.department_name || 'Department'}</p><p className="detail-description">{grievance.description}</p>
    {grievance.attachments?.length > 0 && <section className="detail-section"><h3>Attachments</h3>{grievance.attachments.map((file) => <button className="file-link" key={file.id} onClick={() => download(file)}>↧ {file.original_name}</button>)}</section>}
    {grievance.assignment?.remarks && <div className="officer-instructions"><strong>Assignment instructions</strong><p>{grievance.assignment.remarks}</p></div>}
    {internalNotes.length > 0 && <div className="officer-instructions"><strong>Internal notes</strong>{internalNotes.map((item, index) => <p key={`${item.created_at}-${index}`}>{item.remarks}<small> · {new Date(item.created_at).toLocaleString()}</small></p>)}</div>}
    {publicUpdates.length > 0 && <div className="officer-instructions"><strong>Citizen-visible updates</strong>{publicUpdates.map((item, index) => <p key={`${item.created_at}-${index}`}>{item.remarks}<small> · {new Date(item.created_at).toLocaleString()}</small></p>)}</div>}
    {error && <Notice kind="error">{error}</Notice>}{notice && <Notice kind="success">{notice}</Notice>}
    {grievance.status !== 'RESOLVED' && <div className="officer-actions"><form onSubmit={(event) => { event.preventDefault(); submit('updates', { remarks: progress, is_public: shareProgress }, shareProgress ? 'Citizen-visible progress update published.' : 'Internal progress note recorded.') }}><label>Investigation progress<textarea rows="3" value={progress} onChange={(event) => setProgress(event.target.value)} placeholder="Record what was checked or what happens next" required minLength={5} /></label><label className="checkbox-label"><input type="checkbox" checked={shareProgress} onChange={(event) => setShareProgress(event.target.checked)} /> Share this update with the citizen</label><button className="button button-outline button-small" disabled={busy || progress.trim().length < 5}>Add progress update</button></form>
      <div className="officer-report-compose">
        {reportPending && <div className="report-state report-state-pending" role="status"><strong>Report awaiting CMO review</strong><span>A new report can be submitted after the CMO accepts or returns this one.</span></div>}
        {reportReturned && <div className="report-state report-state-returned" role="status"><strong>Changes requested by the CMO</strong><span>Review the note below, update your report, then submit a replacement.</span></div>}
        {!reportPending && <form onSubmit={(event) => { event.preventDefault(); submit('action-reports', { report }, 'Action-taken report submitted for CMO review.') }}><label>{reportReturned ? 'Revised action-taken report' : 'Action-taken report'}<textarea rows="3" value={report} onChange={(event) => setReport(event.target.value)} placeholder="Describe the action completed and outcome" required minLength={10} /></label><button className="button button-small" disabled={busy || report.trim().length < 10}>{reportReturned ? 'Submit revised report' : 'Submit report for review'}</button></form>}
      </div></div>}
    {grievance.action_reports?.length > 0 && <div className="officer-report-list"><h3>Your submitted reports</h3>{grievance.action_reports.map((item) => <article className={`report-card report-card-${item.review_status.toLowerCase()}`} key={item.id}><div className="report-heading"><strong>Submitted {new Date(item.created_at).toLocaleDateString()}</strong><span className={`status-pill status-${item.review_status.toLowerCase()}`}>{titleCase(item.review_status)}</span></div><p>{item.report}</p>{item.review_remarks && <div className="return-note"><strong>CMO review note</strong><p>{item.review_remarks}</p></div>}</article>)}</div>}
    <div className="detail-section"><h3>Status history</h3><Timeline history={grievance.history?.filter((item) => item.previous_status !== item.new_status)} /></div>
  </article>
}

export default function OfficerDashboard() {
  const [items, setItems] = useState([])
  const [selected, setSelected] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const refreshInProgress = useRef(false)
  const load = useCallback(async (showLoading = true) => {
    if (refreshInProgress.current) return
    refreshInProgress.current = true
    if (showLoading) setLoading(true)
    setError('')
    try {
      const queue = await api('/grievances/officer/queue/')
      setItems(queue)
      setSelected((current) => current && queue.some((item) => String(item.id) === current) ? current : queue[0] ? String(queue[0].id) : '')
    } catch (err) { setError(err.message) }
    finally {
      refreshInProgress.current = false
      if (showLoading) setLoading(false)
    }
  }, [])
  useEffect(() => {
    const initialRefreshTimeout = window.setTimeout(() => load(), 0)
    let focusRefreshTimeout
    const refreshWhenVisible = () => {
      if (document.visibilityState !== 'visible') return
      window.clearTimeout(focusRefreshTimeout)
      focusRefreshTimeout = window.setTimeout(() => load(false), 150)
    }
    const interval = window.setInterval(refreshWhenVisible, 30_000)
    window.addEventListener('focus', refreshWhenVisible)
    document.addEventListener('visibilitychange', refreshWhenVisible)
    return () => {
      window.clearInterval(interval)
      window.clearTimeout(initialRefreshTimeout)
      window.clearTimeout(focusRefreshTimeout)
      window.removeEventListener('focus', refreshWhenVisible)
      document.removeEventListener('visibilitychange', refreshWhenVisible)
    }
  }, [load])
  const current = items.find((item) => String(item.id) === selected)
  return <div className="workspace-wrap">
    <PageIntro eyebrow="Department officer workspace" title="Department grievance queue" actions={<button className="button button-outline button-small" onClick={load}>Refresh queue</button>}>Review cases forwarded to your department, record investigation progress, and submit action-taken reports for CMO review.</PageIntro>
    {error && <Notice kind="error">{error}</Notice>}
    <div className="officer-workspace">
      <aside className="case-list"><div className="case-list-heading"><h2>Department queue</h2><span>{items.length}</span></div>
        {loading ? <div className="loading-list"><span /><span /><span /></div> : items.length === 0 ? <div className="empty-state"><h3>Queue is clear</h3><p>No grievances are currently assigned to your department.</p></div> : items.map((item) => <button className={`case-list-item ${String(item.id) === selected ? 'selected' : ''}`} key={item.id} onClick={() => setSelected(String(item.id))}><span className="case-reference">{item.reference_number}</span><strong>{item.subject}</strong><small>{item.district || 'District not set'} · {item.category}</small><span className={`status-pill status-${item.status.toLowerCase()}`}>{titleCase(item.status)}</span></button>)}
      </aside>
      <div className="case-detail-area">{current ? <OfficerCase key={current.id} grievance={current} onUpdated={load} /> : <div className="empty-state"><span className="empty-icon">↖</span><h3>Select a grievance</h3><p>Choose a case from your assigned queue to review its details.</p></div>}</div>
    </div>
  </div>
}
