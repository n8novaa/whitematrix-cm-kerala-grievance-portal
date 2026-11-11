import { useEffect, useState } from 'react'
import { api, jsonRequest } from '../api'
import { Notice, PageIntro } from '../components/Layout'
import { Timeline } from './PublicPages'

const titleCase = (value = '') => value.toLowerCase().replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase())

function ReviewPanel({ grievance, departments, reload, close }) {
  const [department, setDepartment] = useState(grievance.department || '')
  const [officer, setOfficer] = useState('')
  const [officers, setOfficers] = useState([])
  const [remarks, setRemarks] = useState('')
  const [resolution, setResolution] = useState('')
  const [reportRemarks, setReportRemarks] = useState({})
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (!department) return
    api(`/departments/${department}/officers/`).then(setOfficers).catch((err) => setError(err.message))
  }, [department])

  async function act(work) {
    setBusy(true); setError(''); setNotice('')
    try { await work(); setNotice('Update saved.'); await reload() }
    catch (err) { setError(err.message) }
    finally { setBusy(false) }
  }

  const accepted = grievance.action_reports?.some((report) => report.review_status === 'ACCEPTED')
  return <div className="drawer-backdrop" onClick={(event) => { if (event.target === event.currentTarget) close() }}>
    <aside className="detail-panel review-panel" aria-label={`Review grievance ${grievance.reference_number}`}>
      <div className="detail-heading"><div><p className="eyebrow">{grievance.reference_number}</p><h2>{grievance.subject}</h2></div><button className="icon-button" onClick={close} aria-label="Close review">×</button></div>
      <span className={`status-pill status-${grievance.status.toLowerCase()}`}>{titleCase(grievance.status)}</span>
      <p className="detail-meta">{grievance.district || 'District not provided'} · {grievance.category} · {grievance.department_name || 'Unassigned'}</p>
      <p className="detail-description">{grievance.description}</p>
      {error && <Notice kind="error">{error}</Notice>}{notice && <Notice kind="success">{notice}</Notice>}
      <section className="detail-section assignment-section"><h3>Department assignment</h3>
        <label>Department<select value={department} onChange={(event) => { setDepartment(event.target.value); setOfficer(''); setOfficers([]) }}><option value="">Choose department</option>{departments.map((item) => <option value={item.id} key={item.id}>{item.name}</option>)}</select></label>
        <label>Assigned officer<select value={officer} onChange={(event) => setOfficer(event.target.value)} disabled={!department}><option value="">Choose officer</option>{officers.map((item) => <option value={item.id} key={item.id}>{item.name} · {item.email}</option>)}</select></label>
        <label>Internal assignment note <textarea rows="2" value={remarks} onChange={(event) => setRemarks(event.target.value)} placeholder="Context for the assigned officer" /></label>
        <button className="button button-small" disabled={busy || !department || !officer} onClick={() => act(async () => api(`/grievances/${grievance.id}/assign/`, jsonRequest('POST', { department_id: Number(department), officer_id: Number(officer), remarks })))}>{busy ? 'Saving…' : 'Save assignment'}</button>
      </section>
      <section className="detail-section"><h3>Action-taken reports</h3>
        {!grievance.action_reports?.length ? <p className="muted">No report submitted yet.</p> : grievance.action_reports.map((report) => <article className="report-card" key={report.id}><div className="report-heading"><strong>{report.officer_email}</strong><span className={`status-pill status-${report.review_status.toLowerCase()}`}>{titleCase(report.review_status)}</span></div><p>{report.report}</p><small>{new Date(report.created_at).toLocaleString()}</small>{report.review_remarks && <div className="return-note"><strong>Review note</strong><p>{report.review_remarks}</p></div>}
          {report.review_status === 'PENDING' && <><label>Review note<textarea rows="2" value={reportRemarks[report.id] || ''} onChange={(event) => setReportRemarks((old) => ({ ...old, [report.id]: event.target.value }))} placeholder="Add a note when returning this report" /></label><div className="button-row"><button className="button button-small" disabled={busy} onClick={() => act(async () => api(`/grievances/action-reports/${report.id}/review/`, jsonRequest('POST', { decision: 'ACCEPTED', remarks: reportRemarks[report.id] || '' })))}>Accept report</button><button className="button button-outline button-small" disabled={busy || !(reportRemarks[report.id] || '').trim()} onClick={() => act(async () => api(`/grievances/action-reports/${report.id}/review/`, jsonRequest('POST', { decision: 'RETURNED', remarks: reportRemarks[report.id] })))}>Return for updates</button></div></>}
        </article>)}
      </section>
      {grievance.status !== 'RESOLVED' && <section className="detail-section resolve-box"><h3>Resolution</h3>{!accepted && <p className="field-help">An accepted action report is required before resolution.</p>}<label>Resolution note<textarea rows="2" value={resolution} onChange={(event) => setResolution(event.target.value)} placeholder="Summarize the response for the citizen" /></label><button className="button" disabled={busy || !accepted || !resolution.trim()} onClick={() => act(async () => api(`/grievances/${grievance.id}/resolve/`, jsonRequest('POST', { remarks: resolution })))}>Mark resolved</button></section>}
      <section className="detail-section"><h3>Case history</h3><Timeline history={grievance.history} /></section>
    </aside>
  </div>
}

export default function CMODashboard() {
  const [stats, setStats] = useState(null)
  const [items, setItems] = useState([])
  const [departments, setDepartments] = useState([])
  const [selected, setSelected] = useState(null)
  const [filters, setFilters] = useState({ status: '', department: '', search: '' })
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
  return <div className="workspace-wrap">
    <PageIntro eyebrow="CMO workspace" title="Grievance review" actions={<button className="button button-outline button-small" onClick={load}>Refresh queue</button>}>Review incoming cases, assign department action, and approve reports before resolution.</PageIntro>
    {error && <Notice kind="error">{error}</Notice>}
    <div className="metric-row cmo-metrics"><div className="metric-card"><span>Total cases</span><strong>{stats?.total ?? '—'}</strong><small>Across all statuses</small></div><div className="metric-card"><span>Awaiting resolution</span><strong>{stats?.pending ?? '—'}</strong><small>Open or in progress</small></div><div className="metric-card"><span>Resolved</span><strong>{stats?.resolved ?? '—'}</strong><small>Marked complete</small></div><div className="metric-card metric-alert"><span>Over 7 days</span><strong>{stats?.overdue ?? '—'}</strong><small>Open for follow-up</small></div></div>
    {byDepartment.length > 0 && <section className="department-summary"><p className="eyebrow">Cases by department</p>{byDepartment.map((item) => <div key={item.department__name}><span>{item.department__name || 'Unassigned'}</span><strong>{item.count}</strong></div>)}</section>}
    <section className="data-section"><div className="section-heading"><div><p className="eyebrow">Case management</p><h2>Grievance queue</h2></div><div className="queue-filters"><label className="filter-label">Status<select value={filters.status} onChange={(event) => setFilters((old) => ({ ...old, status: event.target.value }))}><option value="">All statuses</option>{['SUBMITTED', 'UNDER_REVIEW', 'IN_PROGRESS', 'REOPENED', 'RESOLVED'].map((status) => <option key={status} value={status}>{titleCase(status)}</option>)}</select></label><label className="filter-label">Department<select value={filters.department} onChange={(event) => setFilters((old) => ({ ...old, department: event.target.value }))}><option value="">All departments</option>{departments.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label><label className="search-label">Search<input type="search" value={filters.search} onChange={(event) => setFilters((old) => ({ ...old, search: event.target.value }))} placeholder="Reference or subject" /></label></div></div>
      {loading ? <div className="loading-list" aria-label="Loading cases"><span /><span /><span /></div> : items.length === 0 ? <div className="empty-state"><span className="empty-icon">✓</span><h3>No grievances found</h3><p>Change your filters or refresh the queue.</p></div> : <div className="table-scroll"><table><thead><tr><th>Reference</th><th>Grievance</th><th>District</th><th>Department</th><th>Status</th><th>Submitted</th><th /></tr></thead><tbody>{items.map((item) => <tr key={item.id}><td className="ref-cell">{item.reference_number}</td><td><strong>{item.subject}</strong><small>{item.category}</small></td><td>{item.district || '—'}</td><td>{item.department_name || 'Unassigned'}</td><td><span className={`status-pill status-${item.status.toLowerCase()}`}>{titleCase(item.status)}</span></td><td>{new Date(item.created_at).toLocaleDateString()}</td><td><button className="text-link text-button" onClick={() => setSelected(item)}>Review <span aria-hidden="true">→</span></button></td></tr>)}</tbody></table></div>}
    </section>
    {selected && <ReviewPanel key={selected.id} grievance={selected} departments={departments} reload={load} close={() => setSelected(null)} />}
  </div>
}
