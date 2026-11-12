import { useEffect, useState } from 'react'
import { api, downloadGrievanceAttachment, jsonRequest } from '../api'
import { Notice, PageIntro } from '../components/Layout'
import { Timeline } from './PublicPages'

const titleCase = (value = '') => value.toLowerCase().replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase())
const isOverdue = (grievance) => grievance.status !== 'RESOLVED' && Date.now() - new Date(grievance.created_at).getTime() > 7 * 24 * 60 * 60 * 1000
const KERALA_DISTRICTS = ['Alappuzha', 'Ernakulam', 'Idukki', 'Kannur', 'Kasaragod', 'Kollam', 'Kottayam', 'Kozhikode', 'Malappuram', 'Palakkad', 'Pathanamthitta', 'Thiruvananthapuram', 'Thrissur', 'Wayanad']

function ReviewPanel({ grievance, departments, reload, close }) {
  const [department, setDepartment] = useState(grievance.department || '')
  const [officer, setOfficer] = useState('')
  const [officers, setOfficers] = useState([])
  const [reviewRemarks, setReviewRemarks] = useState('')
  const [assignmentRemarks, setAssignmentRemarks] = useState('')
  const [resolution, setResolution] = useState('')
  const [reportRemarks, setReportRemarks] = useState({})
  const [aiValues, setAiValues] = useState(() => ({ department_id: grievance.ai_recommendation?.department_id || '', category: grievance.ai_recommendation?.category || grievance.category, priority: grievance.ai_recommendation?.priority || grievance.priority }))
  const [publicUpdate, setPublicUpdate] = useState('')
  const [escalationReason, setEscalationReason] = useState('')
  const [escalations, setEscalations] = useState([])
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (!department) return
    api(`/departments/${department}/officers/`).then(setOfficers).catch((err) => setError(err.message))
  }, [department])
  useEffect(() => { api(`/grievances/${grievance.id}/escalations/`).then(setEscalations).catch((err) => setError(err.message)) }, [grievance.id])

  async function act(work) {
    setBusy(true); setError(''); setNotice('')
    try { await work(); setNotice('Update saved.'); setEscalations(await api(`/grievances/${grievance.id}/escalations/`)); await reload() }
    catch (err) { setError(err.message) }
    finally { setBusy(false) }
  }

  async function download(attachment) {
    setError('')
    try { await downloadGrievanceAttachment(grievance.id, attachment) }
    catch (err) { setError(err.message) }
  }

  const latestReport = [...(grievance.action_reports || [])].sort((a, b) => new Date(a.created_at) - new Date(b.created_at) || a.id - b.id).at(-1)
  const accepted = latestReport?.review_status === 'ACCEPTED'
    && latestReport.officer_id === grievance.assignment?.officer_id
    && new Date(latestReport.created_at) > new Date(grievance.assignment?.assigned_at)
  const overdue = isOverdue(grievance)
  return <div className="drawer-backdrop" onClick={(event) => { if (event.target === event.currentTarget) close() }}>
    <aside className="detail-panel review-panel" aria-label={`Review grievance ${grievance.reference_number}`}>
      <div className="detail-heading"><div><p className="eyebrow">{grievance.reference_number}</p><h2>{grievance.subject}</h2></div><button className="icon-button" onClick={close} aria-label="Close review">×</button></div>
      <span className={`status-pill status-${grievance.status.toLowerCase()}`}>{titleCase(grievance.status)}</span>
      {overdue && <div className="overdue-banner"><strong>Overdue · open more than 7 days</strong><span>Review the next action and escalate if this case needs additional oversight.</span></div>}
      <p className="detail-meta">{grievance.district || 'District not provided'} · {grievance.category} · {grievance.department_name || 'Unassigned'}</p>
      <p className="detail-description">{grievance.description}</p>
      {grievance.attachments?.length > 0 && <section className="detail-section"><h3>Attachments</h3>{grievance.attachments.map((file) => <button className="file-link" key={file.id} onClick={() => download(file)}>↧ {file.original_name}</button>)}</section>}
      {error && <Notice kind="error">{error}</Notice>}{notice && <Notice kind="success">{notice}</Notice>}
      {['SUBMITTED', 'REOPENED'].includes(grievance.status) && <section className="detail-section"><h3>Initial review</h3><label>Internal review note<textarea rows="2" value={reviewRemarks} onChange={(event) => setReviewRemarks(event.target.value)} placeholder="Record the first review step" /></label><button className="button button-small" disabled={busy} onClick={() => act(async () => api(`/grievances/${grievance.id}/cmo/review/`, jsonRequest('POST', { remarks: reviewRemarks })))}>Move to under review</button></section>}
      {grievance.ai_recommendation && <section className="detail-section review-group"><p className="eyebrow">Decision support</p><h3>AI advisory suggestions</h3><p className="field-help">These suggestions are not official grievance values. The CMO makes the final decision and records it below.</p><div className="official-values"><strong>Current official values</strong><span>{grievance.department_name || 'Unassigned'} · {grievance.category} · {titleCase(grievance.priority)} priority</span></div><div className="suggestion-values"><div><span>Suggested department</span><strong>{grievance.ai_recommendation.department_name || 'Unavailable'}</strong></div><div><span>Suggested category</span><strong>{grievance.ai_recommendation.category}</strong></div><div><span>Suggested priority</span><strong>{titleCase(grievance.ai_recommendation.priority)}</strong></div></div><p>{grievance.ai_recommendation.summary}</p><span className={`status-pill status-${grievance.ai_recommendation.decision.toLowerCase()}`}>{titleCase(grievance.ai_recommendation.decision)}</span>
        {grievance.ai_recommendation.decision === 'PENDING' && <><label>Override department<select value={aiValues.department_id} onChange={(event) => setAiValues((old) => ({ ...old, department_id: event.target.value }))}><option value="">Choose department</option>{departments.map((item) => <option value={item.id} key={item.id}>{item.name}</option>)}</select></label><label>Override category<input value={aiValues.category} maxLength={80} onChange={(event) => setAiValues((old) => ({ ...old, category: event.target.value }))} /></label><label>Override priority<select value={aiValues.priority} onChange={(event) => setAiValues((old) => ({ ...old, priority: event.target.value }))}>{['LOW', 'MEDIUM', 'HIGH'].map((value) => <option value={value} key={value}>{titleCase(value)}</option>)}</select></label><div className="button-row"><button className="button button-small" disabled={busy} onClick={() => act(async () => api(`/grievances/${grievance.id}/ai-recommendation/decision/`, jsonRequest('POST', { decision: 'ACCEPTED' })))}>Accept suggestions</button><button className="button button-outline button-small" disabled={busy || !aiValues.department_id || !aiValues.category.trim()} onClick={() => act(async () => api(`/grievances/${grievance.id}/ai-recommendation/decision/`, jsonRequest('POST', { decision: 'OVERRIDDEN', ...aiValues, department_id: Number(aiValues.department_id) })))}>Save override</button></div></>}
      </section>}
      <section className="detail-section assignment-section review-group"><p className="eyebrow">Department action</p><h3>Assign an officer</h3>
        <label>Department<select value={department} onChange={(event) => { setDepartment(event.target.value); setOfficer(''); setOfficers([]) }}><option value="">Choose department</option>{departments.map((item) => <option value={item.id} key={item.id}>{item.name}</option>)}</select></label>
        <label>Assigned officer<select value={officer} onChange={(event) => setOfficer(event.target.value)} disabled={!department}><option value="">Choose officer</option>{officers.map((item) => <option value={item.id} key={item.id}>{item.name} · {item.email}</option>)}</select></label>
        <label>Internal assignment note <textarea rows="2" value={assignmentRemarks} onChange={(event) => setAssignmentRemarks(event.target.value)} placeholder="Context for the assigned officer" /></label>
        <button className="button button-small" disabled={busy || !department || !officer} onClick={() => act(async () => api(`/grievances/${grievance.id}/assign/`, jsonRequest('POST', { department_id: Number(department), officer_id: Number(officer), remarks: assignmentRemarks })))}>{busy ? 'Saving…' : 'Save assignment'}</button>
      </section>
      {grievance.status !== 'RESOLVED' && <section className="detail-section"><h3>Citizen-visible update</h3><label>Public progress update<textarea rows="3" value={publicUpdate} onChange={(event) => setPublicUpdate(event.target.value)} placeholder="Share a non-sensitive progress message" /></label><button className="button button-small" disabled={busy || publicUpdate.trim().length < 5} onClick={() => act(async () => { await api(`/grievances/${grievance.id}/updates/`, jsonRequest('POST', { remarks: publicUpdate, is_public: true })); setPublicUpdate('') })}>Publish update</button></section>}
      <section className="detail-section"><h3>Escalation history</h3>{escalations.map((item) => <article className="return-note" key={item.id}><strong>{item.raised_by} · {new Date(item.created_at).toLocaleString()}</strong><p>{item.reason}</p></article>)}{grievance.status !== 'RESOLVED' && <><label>Escalation reason<textarea rows="2" value={escalationReason} onChange={(event) => setEscalationReason(event.target.value)} placeholder="Why does this case need higher-level attention?" /></label><button className="button button-outline button-small" disabled={busy || escalationReason.trim().length < 10} onClick={() => act(async () => { await api(`/grievances/${grievance.id}/escalations/`, jsonRequest('POST', { reason: escalationReason })); setEscalationReason('') })}>Escalate case</button></>}</section>
      <section className="detail-section review-group"><p className="eyebrow">Officer response</p><h3>Review action-taken reports</h3>
        {!grievance.action_reports?.length ? <p className="muted">No report submitted yet.</p> : grievance.action_reports.map((report) => <article className="report-card" key={report.id}><div className="report-heading"><strong>{report.officer_email}</strong><span className={`status-pill status-${report.review_status.toLowerCase()}`}>{titleCase(report.review_status)}</span></div><p>{report.report}</p><small>{new Date(report.created_at).toLocaleString()}</small>{report.review_remarks && <div className="return-note"><strong>Review note</strong><p>{report.review_remarks}</p></div>}
          {report.review_status === 'PENDING' && <><label>Review note<textarea rows="2" value={reportRemarks[report.id] || ''} onChange={(event) => setReportRemarks((old) => ({ ...old, [report.id]: event.target.value }))} placeholder="Add at least 10 characters when returning this report" /></label><div className="button-row"><button className="button button-small" disabled={busy} onClick={() => act(async () => api(`/grievances/action-reports/${report.id}/review/`, jsonRequest('POST', { decision: 'ACCEPTED', remarks: reportRemarks[report.id] || '' })))}>Accept report</button><button className="button button-outline button-small" disabled={busy || (reportRemarks[report.id] || '').trim().length < 10} onClick={() => act(async () => api(`/grievances/action-reports/${report.id}/review/`, jsonRequest('POST', { decision: 'RETURNED', remarks: reportRemarks[report.id] })))}>Return for updates</button></div></>}
        </article>)}
      </section>
      {grievance.status !== 'RESOLVED' && <section className="detail-section resolve-box review-group"><p className="eyebrow">Final review</p><h3>Resolve grievance</h3>{!accepted && <p className="field-help">The latest report must be accepted from the currently assigned officer after assignment.</p>}<label>Resolution note<textarea rows="2" value={resolution} onChange={(event) => setResolution(event.target.value)} placeholder="Add at least 10 characters summarizing the response" /></label><button className="button" disabled={busy || !accepted || resolution.trim().length < 10} onClick={() => act(async () => api(`/grievances/${grievance.id}/resolve/`, jsonRequest('POST', { remarks: resolution })))}>Mark resolved</button></section>}
      <section className="detail-section"><h3>Internal remarks</h3><Timeline history={grievance.history?.filter((item) => item.is_internal)} /></section>
      <section className="detail-section"><h3>Public updates and status history</h3><Timeline history={grievance.history?.filter((item) => !item.is_internal)} /></section>
    </aside>
  </div>
}

export default function CMODashboard() {
  const [stats, setStats] = useState(null)
  const [items, setItems] = useState([])
  const [departments, setDepartments] = useState([])
  const [selected, setSelected] = useState(null)
  const [filters, setFilters] = useState({ status: '', department: '', district: '', category: '', priority: '', search: '' })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  async function load() {
    setLoading(true); setError('')
    try {
      const params = new URLSearchParams()
      Object.entries(filters).forEach(([key, value]) => { if (value) params.set(key, value) })
      const [queue, summary] = await Promise.all([api(`/grievances/cmo/queue/?${params}`), api('/dashboard/cmo/statistics/')])
      setItems(queue); setStats(summary)
      if (selected) setSelected(queue.find((item) => item.id === selected.id) || null)
    } catch (err) { setError(err.message) }
    finally { setLoading(false) }
  }

  useEffect(() => { api('/departments/').then(setDepartments).catch((err) => setError(err.message)) }, [])
  useEffect(() => {
    const params = new URLSearchParams()
    Object.entries(filters).forEach(([key, value]) => { if (value) params.set(key, value) })
    Promise.all([api(`/grievances/cmo/queue/?${params}`), api('/dashboard/cmo/statistics/')])
      .then(([queue, summary]) => { setItems(queue); setStats(summary); setSelected((current) => current ? queue.find((item) => item.id === current.id) || null : null) })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [filters])
  const byDepartment = stats?.by_department || []
  const byDistrict = stats?.by_district || []
  return <div className="workspace-wrap">
    <PageIntro eyebrow="CMO workspace" title="Grievance review" actions={<button className="button button-outline button-small" onClick={load}>Refresh queue</button>}>Review incoming cases, assign department action, and approve reports before resolution.</PageIntro>
    {error && <Notice kind="error">{error}</Notice>}
    <div className="metric-row cmo-metrics"><div className="metric-card"><span>Total cases</span><strong>{stats?.total ?? '—'}</strong><small>Across all statuses</small></div><div className="metric-card"><span>Awaiting resolution</span><strong>{stats?.pending ?? '—'}</strong><small>Open or in progress</small></div><div className="metric-card"><span>Resolved</span><strong>{stats?.resolved ?? '—'}</strong><small>Marked complete</small></div><div className="metric-card metric-alert"><span>Over 7 days</span><strong>{stats?.overdue ?? '—'}</strong><small>Open for follow-up</small></div></div>
    {byDepartment.length > 0 && <section className="department-summary"><p className="eyebrow">Cases by department</p>{byDepartment.map((item) => <div key={item.department__name}><span>{item.department__name || 'Unassigned'}</span><strong>{item.count}</strong></div>)}</section>}
    {byDistrict.length > 0 && <section className="department-summary"><p className="eyebrow">Cases by district</p>{byDistrict.map((item) => <div key={item.district}><span>{item.district || 'Not provided'}</span><strong>{item.count}</strong></div>)}</section>}
    <section className="data-section"><div className="section-heading"><div><p className="eyebrow">Case management</p><h2>Grievance queue</h2></div><div className="queue-filters"><label className="filter-label">Status<select value={filters.status} onChange={(event) => setFilters((old) => ({ ...old, status: event.target.value }))}><option value="">All statuses</option>{['SUBMITTED', 'UNDER_REVIEW', 'IN_PROGRESS', 'REOPENED', 'RESOLVED'].map((status) => <option key={status} value={status}>{titleCase(status)}</option>)}</select></label><label className="filter-label">Department<select value={filters.department} onChange={(event) => setFilters((old) => ({ ...old, department: event.target.value }))}><option value="">All departments</option>{departments.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label><label className="filter-label">Priority<select value={filters.priority} onChange={(event) => setFilters((old) => ({ ...old, priority: event.target.value }))}><option value="">All priorities</option>{['LOW', 'MEDIUM', 'HIGH'].map((value) => <option key={value} value={value}>{titleCase(value)}</option>)}</select></label><label className="filter-label">District<select value={filters.district} onChange={(event) => setFilters((old) => ({ ...old, district: event.target.value }))}><option value="">All districts</option>{KERALA_DISTRICTS.map((district) => <option key={district}>{district}</option>)}</select></label><label className="filter-label">Category<input value={filters.category} onChange={(event) => setFilters((old) => ({ ...old, category: event.target.value }))} placeholder="Any category" /></label><label className="search-label">Search<input type="search" value={filters.search} onChange={(event) => setFilters((old) => ({ ...old, search: event.target.value }))} placeholder="Reference or subject" /></label></div></div>
      {loading ? <div className="loading-list" aria-label="Loading cases"><span /><span /><span /></div> : items.length === 0 ? <div className="empty-state"><span className="empty-icon">✓</span><h3>No grievances found</h3><p>Change your filters or refresh the queue.</p></div> : <div className="table-scroll"><table><thead><tr><th>Reference</th><th>Grievance</th><th>District</th><th>Department</th><th>Status</th><th>Submitted</th><th /></tr></thead><tbody>{items.map((item) => <tr key={item.id} className={isOverdue(item) ? 'case-overdue' : ''}><td className="ref-cell">{item.reference_number}{isOverdue(item) && <small className="overdue-label">Overdue</small>}</td><td><strong>{item.subject}</strong><small>{item.category}</small></td><td>{item.district || '—'}</td><td>{item.department_name || 'Unassigned'}</td><td><span className={`status-pill status-${item.status.toLowerCase()}`}>{titleCase(item.status)}</span></td><td>{new Date(item.created_at).toLocaleDateString()}</td><td><button className="text-link text-button" onClick={() => setSelected(item)}>Review <span aria-hidden="true">→</span></button></td></tr>)}</tbody></table></div>}
    </section>
    {selected && <ReviewPanel key={selected.id} grievance={selected} departments={departments} reload={load} close={() => setSelected(null)} />}
  </div>
}
