import { useState } from 'react'
import { useAuth } from '../auth-context'
import { Notice } from '../components/Layout'

export default function AuthPage({ mode, onSuccess }) {
  const isRegister = mode === 'register'
  const { signIn, register } = useAuth()
  const [values, setValues] = useState({ email: '', password: '', confirm_password: '', first_name: '', last_name: '', mobile_number: '' })
  const [error, setError] = useState('')
  const [confirmError, setConfirmError] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const [busy, setBusy] = useState(false)

  function update(event) {
    setValues((current) => ({ ...current, [event.target.name]: event.target.value }))
    if (event.target.name === 'confirm_password' || event.target.name === 'password') setConfirmError('')
  }

  async function submit(event) {
    event.preventDefault()
    if (isRegister && values.password !== values.confirm_password) {
      setConfirmError('Passwords do not match. Re-enter the same password in both fields.')
      return
    }
    setBusy(true)
    setError('')
    try {
      if (isRegister) {
        await register(values)
      }
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
          <label>Last name<input name="last_name" value={values.last_name} onChange={update} autoComplete="family-name" required /></label>
        </div>}
        <label>Email address<input type="email" name="email" value={values.email} onChange={update} autoComplete="email" required /></label>
        {isRegister && <label>Mobile number<input type="tel" name="mobile_number" value={values.mobile_number} onChange={update} autoComplete="tel" inputMode="tel" pattern="[+]?[0-9][0-9 ().-]{5,18}" title="Enter a valid mobile number with 7 to 15 digits." required /></label>}
        <div className="password-field"><label htmlFor="account-password">Password</label><div className="password-control"><input id="account-password" type={showPassword ? 'text' : 'password'} name="password" value={values.password} onChange={update} autoComplete={isRegister ? 'new-password' : 'current-password'} minLength={8} required /><button className="password-toggle" type="button" aria-label={showPassword ? 'Hide password' : 'Show password'} aria-pressed={showPassword} onClick={() => setShowPassword((shown) => !shown)}>{showPassword ? 'Hide' : 'Show'}</button></div></div>
        {isRegister && <div className="password-field"><label htmlFor="confirm-password">Confirm password</label><div className="password-control"><input id="confirm-password" type={showConfirmPassword ? 'text' : 'password'} name="confirm_password" value={values.confirm_password} onChange={update} autoComplete="new-password" minLength={8} required aria-invalid={Boolean(confirmError || (values.confirm_password && values.password !== values.confirm_password))} aria-describedby={confirmError || (values.confirm_password && values.password !== values.confirm_password) ? 'confirm-password-error' : undefined} /><button className="password-toggle" type="button" aria-label={showConfirmPassword ? 'Hide confirmation password' : 'Show confirmation password'} aria-pressed={showConfirmPassword} onClick={() => setShowConfirmPassword((shown) => !shown)}>{showConfirmPassword ? 'Hide' : 'Show'}</button></div>{(confirmError || (values.confirm_password && values.password !== values.confirm_password)) && <p id="confirm-password-error" className="field-error" role="alert">{confirmError || 'Passwords do not match.'}</p>}</div>}
        {isRegister && <p className="field-help">Public registration creates a citizen account. CMO and officer access is provisioned for the demonstration.</p>}
        <button className="button button-wide" disabled={busy || (isRegister && (!values.confirm_password || values.password !== values.confirm_password))}>{busy ? 'Please wait…' : isRegister ? 'Create account' : 'Sign in'}</button>
        <p className="auth-switch">{isRegister ? 'Already registered?' : 'New to the prototype?'} <a href={isRegister ? '/sign-in' : '/register'}>{isRegister ? 'Sign in' : 'Create an account'}</a></p>
      </form>
    </section>
  )
}
