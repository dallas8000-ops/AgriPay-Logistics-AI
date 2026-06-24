import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { authApi, COUNTRIES } from '../lib/api';

const ROLES = [
  { value: 'farmer', label: 'Farmer' },
  { value: 'vendor', label: 'Market Vendor' },
  { value: 'buyer', label: 'Produce Buyer' },
  { value: 'driver', label: 'Truck Driver' },
];

export default function RegisterPage() {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    username: '', email: '', password: '', first_name: '', last_name: '',
    role: 'farmer', country: 'KE', phone: '',
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await authApi.register(form);
      navigate('/login');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Registration failed');
    } finally {
      setLoading(false);
    }
  };

  const set = (key: string, val: string) => setForm((f) => ({ ...f, [key]: val }));

  return (
    <div className="auth-page">
      <form className="card auth-form" onSubmit={handleSubmit}>
        <h2>Create account</h2>
        <div className="form-group">
          <label>I am a…</label>
          <select value={form.role} onChange={(e) => set('role', e.target.value)}>
            {ROLES.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
          </select>
        </div>
        <div className="form-group">
          <label>Country</label>
          <select value={form.country} onChange={(e) => set('country', e.target.value)}>
            {Object.entries(COUNTRIES).map(([code, c]) => (
              <option key={code} value={code}>{c.flag} {c.name}</option>
            ))}
          </select>
        </div>
        <div className="grid-2">
          <div className="form-group">
            <label>First name</label>
            <input value={form.first_name} onChange={(e) => set('first_name', e.target.value)} required />
          </div>
          <div className="form-group">
            <label>Last name</label>
            <input value={form.last_name} onChange={(e) => set('last_name', e.target.value)} required />
          </div>
        </div>
        <div className="form-group">
          <label>Username</label>
          <input value={form.username} onChange={(e) => set('username', e.target.value)} required />
        </div>
        <div className="form-group">
          <label>Email</label>
          <input type="email" value={form.email} onChange={(e) => set('email', e.target.value)} required />
        </div>
        <div className="form-group">
          <label>Phone (Mobile Money)</label>
          <input value={form.phone} onChange={(e) => set('phone', e.target.value)} placeholder="+254..." />
        </div>
        <div className="form-group">
          <label>Password</label>
          <input type="password" value={form.password} onChange={(e) => set('password', e.target.value)} required minLength={8} />
        </div>
        {error && <p className="error-msg">{error}</p>}
        <button type="submit" className="btn btn-primary btn-block" disabled={loading}>
          {loading ? 'Creating…' : 'Create account'}
        </button>
        <p className="auth-footer">
          Already have an account? <Link to="/login">Sign in</Link>
        </p>
      </form>
    </div>
  );
}
