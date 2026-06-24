import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { authApi } from '../lib/api';

export default function OnboardingPage() {
  const { user, refreshUser } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState<Record<string, string>>({});
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    authApi.onboarding().then((r) => {
      if (r.onboarding_complete) navigate('/');
      if (r.profile) setForm(r.profile as Record<string, string>);
    }).catch(() => {});
  }, [navigate]);

  const fields: Record<string, Array<{ key: string; label: string }>> = {
    farmer: [
      { key: 'farm_name', label: 'Farm Name' },
      { key: 'location', label: 'Farm Location' },
      { key: 'mobile_money_number', label: 'Mobile Money Number' },
    ],
    vendor: [
      { key: 'stall_name', label: 'Stall Name' },
      { key: 'market_location', label: 'Market Location' },
      { key: 'mobile_money_number', label: 'Mobile Money Number' },
    ],
    buyer: [
      { key: 'business_name', label: 'Business Name' },
      { key: 'location', label: 'Business Location' },
      { key: 'mobile_money_number', label: 'Mobile Money Number' },
    ],
    driver: [
      { key: 'license_number', label: 'License Number' },
      { key: 'vehicle_type', label: 'Vehicle Type' },
      { key: 'vehicle_plate', label: 'Plate Number' },
      { key: 'mobile_money_number', label: 'Mobile Money Number' },
    ],
  };

  const roleFields = fields[user?.role || 'farmer'] || fields.farmer;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      await authApi.submitOnboarding(form);
      await refreshUser();
      navigate('/');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page">
      <h1 className="page-title">Complete Your Profile</h1>
      <p style={{ color: 'var(--text-muted)', marginBottom: '1rem', fontSize: '0.9rem' }}>
        Tell us about your {user?.role} business to start using AgriPay.
      </p>
      <form className="card" onSubmit={handleSubmit}>
        {roleFields.map(({ key, label }) => (
          <div key={key} className="form-group">
            <label>{label}</label>
            <input
              value={form[key] || ''}
              onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))}
              required
            />
          </div>
        ))}
        {error && <p className="error-msg">{error}</p>}
        <button type="submit" className="btn btn-primary btn-block" disabled={loading}>
          {loading ? 'Saving…' : 'Complete Onboarding'}
        </button>
      </form>
    </div>
  );
}
