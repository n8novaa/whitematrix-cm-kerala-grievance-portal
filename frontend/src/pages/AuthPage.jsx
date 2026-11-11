import { useState } from 'react'
import { useAuth } from '../auth-context'
import { Notice } from '../components/Layout'

export default function AuthPage({ mode, onSuccess }) {
  const isRegister = mode === 'register'
  const { signIn, register } = useAuth()
  const [values, setValues] = useState({ email: '', password: '', first_name: '', last_name: '', mobile_number: '' })
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  function update(event) {
    setValues((current) => ({ ...current, [event.target.name]: event.target.value }))
  }

  async function submit(event) {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      if (isRegister) await register(values)
      else await signIn(values.email, values.password)
      onSuccess()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="auth-wrap">
      <div className="auth-aside">
        <p className="eyebrow">A clearer way to follow up</p>
        <h1>{isRegister ? 'Start with a secure account.' : 'Welcome back.'}</h1>
        <p>Track updates to your grievance in one place. This is a fictional recruitment prototype.</p>
        <div className="aside-rule"><span>01</span><p>Submit a concern and keep its reference number.</p></div>
        <div className="aside-rule"><span>02</span><p>Follow progress and see public status history.</p></div>
      </div>
      <form className="auth-card" onSubmit={submit}>
        <p className="eyebrow">{isRegister ? 'Citizen registration' : 'Account access'}</p>
        <h2>{isRegister ? 'Create your account' : 'Sign in to continue'}</h2>
        <p className="muted">{isRegister ? 'Use a valid email address and a strong password.' : 'Use the email and password for your demo account.'}</p>
        {error && <Notice kind="error">{error}</Notice>}
        {isRegister && <div className="form-row">
          <label>First name<input name="first_name" value={values.first_name} onChange={update} autoComplete="given-name" required /></label>
          <label>Last name<input name="last_name" value={values.last_name} onChange={update} autoComplete="family-name" /></label>
        </div>}
        <label>Email address<input type="email" name="email" value={values.email} onChange={update} autoComplete="email" required /></label>
        {isRegister && <label>Mobile number <span className="optional">(optional)</span><input type="tel" name="mobile_number" value={values.mobile_number} onChange={update} autoComplete="tel" /></label>}
        <label>Password<input type="password" name="password" value={values.password} onChange={update} autoComplete={isRegister ? 'new-password' : 'current-password'} minLength={8} required /></label>
        {isRegister && <p className="field-help">Public registration creates a citizen account. CMO and officer access is provisioned for the demonstration.</p>}
        <button className="button button-wide" disabled={busy}>{busy ? 'Please wait…' : isRegister ? 'Create account' : 'Sign in'}</button>
        <p className="auth-switch">{isRegister ? 'Already registered?' : 'New to the prototype?'} <a href={isRegister ? '/sign-in' : '/register'}>{isRegister ? 'Sign in' : 'Create an account'}</a></p>
      </form>
    </section>
  )
}
