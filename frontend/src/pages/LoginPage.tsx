import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { BookOpen, Shield, Wallet } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { capabilitiesApi, COUNTRIES, type Capabilities } from '../lib/api';

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [caps, setCaps] = useState<Capabilities | null>(null);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    capabilitiesApi.get().then(setCaps).catch(() => {});
  }, []);

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

  const features = [
    { icon: Wallet, title: 'Personal-number collection', desc: caps?.collection.personal_transfer.description.slice(0, 72) + '…' || 'Collect without a merchant account' },
    { icon: BookOpen, title: 'SMS reconciliation', desc: caps?.collection.sms_reconciliation.description.slice(0, 72) + '…' || 'Paste confirmations — replace the notebook' },
    { icon: Shield, title: 'Honest deployment', desc: 'Only features configured on this server are offered at checkout' },
  ];

  return (
    <div className="auth-page auth-page--split">
      <aside className="auth-showcase">
        <span className="auth-logo">🌾</span>
        <h1>{caps?.product_name || 'AgriPay'}</h1>
        <p className="auth-tagline">
          {caps?.tagline || 'East Africa payments and reconciliation for SMEs and traders.'}
        </p>
        <div className="country-flags">
          {Object.values(COUNTRIES).map((c) => (
            <span key={c.name} title={c.name}>{c.flag}</span>
          ))}
        </div>
        <ul className="auth-feature-list">
          {features.map(({ icon: Icon, title, desc }) => (
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
          <summary>Demo accounts (Uganda / UGX)</summary>
          <p className="demo-hint-lead">Primary portfolio demo — sign in as the farmer to try invoices and SMS reconcile.</p>
          <ul>
            <li><strong>james_farmer</strong> / demo12345 — Mbale farmer, MTN MoMo +256</li>
            <li>mary_buyer / demo12345 — Kampala buyer</li>
            <li>peter_driver / demo12345</li>
            <li>admin / admin12345</li>
          </ul>
        </details>
      </form>
    </div>
  );
}
