import { useEffect, useState } from 'react'
import { AuthProvider } from './AuthContext.jsx'
import { useAuth } from './auth-context'
import { Layout, Notice } from './components/Layout'
import AuthPage from './pages/AuthPage'
import CitizenDashboard from './pages/CitizenDashboard'
import CMODashboard from './pages/CMODashboard'
import OfficerDashboard from './pages/OfficerDashboard'
import PublicPages from './pages/PublicPages'
import './App.css'

function Application() {
  const { user, loading } = useAuth()
  const [page, setPage] = useState(window.location.pathname.replace(/\/$/, '') || '/')
  function navigate(path) {
    window.history.pushState({}, '', path)
    setPage(path)
    window.scrollTo(0, 0)
  }

  useEffect(() => {
    function onPopState() { setPage(window.location.pathname.replace(/\/$/, '') || '/') }
    window.addEventListener('popstate', onPopState)
    return () => window.removeEventListener('popstate', onPopState)
  }, [])

  const protectedPage = ['/dashboard', '/submit'].includes(page)
  const route = user && ['/sign-in', '/register'].includes(page) ? '/dashboard'
    : user && page === '/submit' && user.role !== 'CITIZEN' ? '/dashboard' : page

  let content
  if (loading) content = <div className="app-loading" role="status">Restoring your session…</div>
  else if (protectedPage && !user) content = <AuthPage mode="login" onSuccess={() => navigate('/dashboard')} />
  else if (route === '/sign-in' || route === '/register') content = <AuthPage mode={route === '/register' ? 'register' : 'login'} onSuccess={() => navigate('/dashboard')} />
  else if (route === '/dashboard' && user?.role === 'CITIZEN') content = <CitizenDashboard />
  else if (route === '/submit' && user?.role === 'CITIZEN') content = <CitizenDashboard initialMode="submit" />
  else if (route === '/dashboard' && user?.role === 'CMO') content = <CMODashboard />
  else if (route === '/dashboard' && user?.role === 'OFFICER') content = <OfficerDashboard />
  else if (route === '/dashboard') content = <Notice kind="error">This account role is not enabled for a workspace.</Notice>
  else content = <PublicPages page={route} user={user} />

  return <Layout><div key={route} className="page-shell">{content ?? <div className="content-wrap"><h1>Page not found</h1><a className="button" href="/">Return home</a></div>}</div></Layout>
}

export default function App() {
  return <AuthProvider><Application /></AuthProvider>
}
