import { useAuth } from '../auth-context'

export function Layout({ children }) {
  const { user, signOut } = useAuth()
  return (
    <>
      <div className="prototype-strip">Recruitment prototype · Fictional demonstration · Not an official Government of Kerala service</div>
      <header className="site-header">
        <a className="brand" href="/" aria-label="Kerala Grievance Portal home">
          <span className="brand-mark" aria-hidden="true">K</span>
          <span><strong>People’s Desk</strong><small>Kerala grievance prototype</small></span>
        </a>
        <nav className="main-nav" aria-label="Main navigation">
          <a href="/how-it-works">How it works</a>
          <a href="/faq">FAQ</a>
          <a href="/departments">Departments</a>
          <a href="/contact">Contact</a>
          {user ? (
            <>
              <a className="nav-dashboard" href="/dashboard">{user.role === 'CITIZEN' ? 'My grievances' : 'Workspace'}</a>
              <button className="button button-quiet nav-signout" onClick={() => signOut()}>Sign out</button>
            </>
          ) : (
            <><a href="/sign-in">Sign in</a><a className="button button-small" href="/register">Create an account</a></>
          )}
        </nav>
      </header>
      <main id="main-content">{children}</main>
      <footer className="site-footer">
        <a className="brand brand-footer" href="/"><span className="brand-mark" aria-hidden="true">K</span><span><strong>People’s Desk</strong><small>Prototype service</small></span></a>
        <p>This fictional prototype is for demonstration only. It is not operated by or endorsed by the Government of Kerala.</p>
        <div><a href="/about">About</a><a href="/how-it-works">How it works</a><a href="/faq">FAQ</a><a href="/contact">Contact</a></div>
      </footer>
    </>
  )
}

export function PageIntro({ eyebrow, title, children, actions }) {
  return (
    <section className="page-intro">
      <div><p className="eyebrow">{eyebrow}</p><h1>{title}</h1>{children && <p className="intro-copy">{children}</p>}</div>
      {actions && <div className="intro-actions">{actions}</div>}
    </section>
  )
}

export function Notice({ kind = 'info', children }) {
  return <div className={`notice notice-${kind}`} role="status">{children}</div>
}
