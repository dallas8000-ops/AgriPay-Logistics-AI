import { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import { useCapabilities } from '../context/CapabilitiesContext';
import { COUNTRIES } from '../lib/api';

export default function SettingsPage() {
  const { user, logout } = useAuth();
  const caps = useCapabilities();
  const { theme, toggleTheme } = useTheme();
  const country = user?.country ? COUNTRIES[user.country as keyof typeof COUNTRIES] : null;
  const [smsAlerts, setSmsAlerts] = useState(true);
  const [whatsappAlerts, setWhatsappAlerts] = useState(true);
  const [deferredPrompt, setDeferredPrompt] = useState<{ prompt: () => Promise<void> } | null>(null);

  useEffect(() => {
    setSmsAlerts(localStorage.getItem('notify_sms') !== 'false');
    setWhatsappAlerts(localStorage.getItem('notify_whatsapp') !== 'false');

    const handler = (e: Event) => {
      e.preventDefault();
      setDeferredPrompt(e as unknown as { prompt: () => Promise<void> });
    };
    window.addEventListener('beforeinstallprompt', handler);
    return () => window.removeEventListener('beforeinstallprompt', handler);
  }, []);

  const togglePref = (key: string, value: boolean, setter: (v: boolean) => void) => {
    setter(value);
    localStorage.setItem(key, String(value));
  };

  const installApp = async () => {
    if (deferredPrompt) {
      await deferredPrompt.prompt();
      setDeferredPrompt(null);
    }
  };

  return (
    <div className="page">
      <h1 className="page-title">Settings</h1>
      <div className="card">
        <div className="list-item">
          <span>Account</span>
          <strong>{user?.username}</strong>
        </div>
        <div className="list-item">
          <span>Role</span>
          <strong>{user?.role}</strong>
        </div>
        <div className="list-item">
          <span>Country</span>
          <strong>{country ? `${country.flag} ${country.name}` : '—'}</strong>
        </div>
        <div className="list-item">
          <span>Currency</span>
          <strong>{user?.currency}</strong>
        </div>
        <div className="list-item">
          <span>Theme</span>
          <button className="btn btn-secondary" onClick={toggleTheme}>
            {theme === 'light' ? '🌙 Dark' : '☀️ Light'}
          </button>
        </div>
      </div>

      <div className="card" style={{ marginTop: '1rem' }}>
        <h3 style={{ marginBottom: '0.75rem', fontSize: '1rem' }}>Notification Preferences</h3>
        <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '0.75rem' }}>
          In-app alerts are always on. External channels require gateway configuration on the server.
        </p>
        <label className="list-item" style={{ cursor: caps?.notifications.sms.status === 'operational' ? 'pointer' : 'not-allowed', opacity: caps?.notifications.sms.status === 'operational' ? 1 : 0.55 }}>
          <span>📱 SMS alerts {caps?.notifications.sms.status !== 'operational' && '(not configured)'}</span>
          <input
            type="checkbox"
            checked={smsAlerts}
            disabled={caps?.notifications.sms.status !== 'operational'}
            onChange={(e) => togglePref('notify_sms', e.target.checked, setSmsAlerts)}
          />
        </label>
        <label className="list-item" style={{ cursor: caps?.notifications.whatsapp.status === 'operational' ? 'pointer' : 'not-allowed', opacity: caps?.notifications.whatsapp.status === 'operational' ? 1 : 0.55 }}>
          <span>💬 WhatsApp alerts {caps?.notifications.whatsapp.status !== 'operational' && '(not configured)'}</span>
          <input
            type="checkbox"
            checked={whatsappAlerts}
            disabled={caps?.notifications.whatsapp.status !== 'operational'}
            onChange={(e) => togglePref('notify_whatsapp', e.target.checked, setWhatsappAlerts)}
          />
        </label>
      </div>

      {caps && (
        <div className="card" id="integrations" style={{ marginTop: '1rem', fontSize: '0.82rem' }}>
          <h3 style={{ marginBottom: '0.5rem', fontSize: '1rem' }}>Integration status</h3>
          <p style={{ color: 'var(--text-muted)', marginBottom: '0.65rem' }}>
            Live on this server vs optional add-ons. Core collection (personal transfer + SMS reconcile) works without merchant accounts.
          </p>
          <ul style={{ margin: '0 0 0.75rem', paddingLeft: '1.1rem', color: 'var(--text-muted)' }}>
            <li>Personal transfer: {caps.collection.personal_transfer.status}</li>
            <li>SMS reconciliation: {caps.collection.sms_reconciliation.status}</li>
            <li>MTN MoMo API: {caps.collection.merchant_api.providers.mtn_momo}</li>
            <li>Stripe cards: {caps.collection.stripe.status}</li>
            <li>Flutterwave: {caps.collection.flutterwave?.status ?? 'not_configured'} (optional)</li>
          </ul>
          {caps.warnings.length > 0 && (
            <>
              <h4 style={{ fontSize: '0.88rem', marginBottom: '0.35rem' }}>Optional channels</h4>
              <ul style={{ margin: 0, paddingLeft: '1.1rem', color: 'var(--text-muted)' }}>
                {caps.warnings.map((w) => (
                  <li key={w}>{w}</li>
                ))}
              </ul>
            </>
          )}
        </div>
      )}

      {deferredPrompt && (
        <button className="btn btn-primary btn-block" style={{ marginTop: '1rem' }} onClick={installApp}>
          📲 Install AgriPay App
        </button>
      )}

      <p style={{ marginTop: '1rem', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
        Offline mode caches listings and queues actions when you lose connection.
      </p>

      <button className="btn btn-secondary btn-block" style={{ marginTop: '1.5rem' }} onClick={logout}>
        Sign Out
      </button>
    </div>
  );
}
