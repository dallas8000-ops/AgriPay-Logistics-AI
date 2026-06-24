import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Shield, Sparkles, Truck, Wallet } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { COUNTRIES } from '../lib/api';

const FEATURES = [
  { icon: Wallet, title: 'Mobile Money', desc: 'MTN, Airtel & M-Pesa sandbox payments' },
  { icon: Truck, title: 'Logistics', desc: 'Driver tracking & proof-of-delivery' },
  { icon: Sparkles, title: 'AI Pricing', desc: 'Smart crop estimates & buyer scores' },
  { icon: Shield, title: 'Disputes', desc: 'Protected trades across 4 countries' },
];

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(username, password);
      navigate('/');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page auth-page--split">
      <aside className="auth-showcase">
        <span className="auth-logo">🌾</span>
        <h1>AgriPay Logistics AI</h1>
        <p className="auth-tagline">
          The mobile-first platform connecting farmers, vendors, buyers & truck drivers across East Africa.
        </p>
        <div className="country-flags">
          {Object.values(COUNTRIES).map((c) => (
            <span key={c.name} title={c.name}>{c.flag}</span>
          ))}
        </div>
        <ul className="auth-feature-list">
          {FEATURES.map(({ icon: Icon, title, desc }) => (
            <li key={title}>
              <span className="auth-feature-icon"><Icon size={18} /></span>
              <div>
                <strong>{title}</strong>
                <span>{desc}</span>
              </div>
            </li>
          ))}
        </ul>
      </aside>

      <form className="card auth-form" onSubmit={handleSubmit}>
        <h2>Welcome back</h2>
        <p className="auth-form-sub">Sign in to your account</p>
        <div className="form-group">
          <label>Username</label>
          <input value={username} onChange={(e) => setUsername(e.target.value)} required autoComplete="username" />
        </div>
        <div className="form-group">
          <label>Password</label>
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required autoComplete="current-password" />
        </div>
        {error && <p className="error-msg">{error}</p>}
        <button type="submit" className="btn btn-primary btn-block" disabled={loading}>
          {loading ? 'Signing in…' : 'Sign in'}
        </button>
        <p className="auth-footer">
          New here? <Link to="/register">Create account</Link>
        </p>
        <details className="demo-hint">
          <summary>Demo accounts</summary>
          <ul>
            <li>james_farmer / demo12345</li>
            <li>mary_buyer / demo12345</li>
            <li>peter_driver / demo12345</li>
            <li>admin / admin12345</li>
          </ul>
        </details>
      </form>
    </div>
  );
}
