import { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { aiApi, formatCurrency, type PriceEstimate } from '../lib/api';

const CROPS = ['maize', 'beans', 'coffee', 'tea', 'bananas', 'tomatoes', 'potatoes', 'avocado', 'rice', 'onions'];
const SEASONS = [
  { value: 'long_rains', label: 'Long Rains' },
  { value: 'short_rains', label: 'Short Rains' },
  { value: 'dry', label: 'Dry Season' },
];

export default function AIPricingPage() {
  const { user } = useAuth();
  const [crop, setCrop] = useState('maize');
  const [quantity, setQuantity] = useState('500');
  const [season, setSeason] = useState('long_rains');
  const [result, setResult] = useState<PriceEstimate | null>(null);
  const [loading, setLoading] = useState(false);

  const estimate = async () => {
    setLoading(true);
    try {
      const r = await aiApi.priceEstimate({
        crop,
        quantity_kg: parseFloat(quantity),
        country: user?.country,
        season,
      });
      setResult(r);
    } catch {
      setResult(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page">
      <h1 className="page-title">AI Price Estimate</h1>
      <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginBottom: '1rem' }}>
        Get smart pricing by crop, location, quantity, and season across East Africa.
      </p>

      <div className="card">
        <div className="form-group">
          <label>Crop</label>
          <select value={crop} onChange={(e) => setCrop(e.target.value)}>
            {CROPS.map((c) => <option key={c} value={c}>{c.charAt(0).toUpperCase() + c.slice(1)}</option>)}
          </select>
        </div>
        <div className="form-group">
          <label>Quantity (kg)</label>
          <input type="number" value={quantity} onChange={(e) => setQuantity(e.target.value)} />
        </div>
        <div className="form-group">
          <label>Season</label>
          <select value={season} onChange={(e) => setSeason(e.target.value)}>
            {SEASONS.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
          </select>
        </div>
        <button className="btn btn-primary btn-block" onClick={estimate} disabled={loading}>
          {loading ? 'Calculating…' : 'Get AI Estimate'}
        </button>
      </div>

      {result && (
        <div className="card" style={{ marginTop: '1rem' }}>
          <h3 style={{ marginBottom: '0.75rem' }}>{result.crop} — {result.currency}</h3>
          <div className="grid-2">
            <div className="stat-card">
              <div className="stat-value" style={{ fontSize: '1.25rem' }}>
                {formatCurrency(result.unit_price, result.currency)}
              </div>
              <div className="stat-label">Per kg</div>
            </div>
            <div className="stat-card">
              <div className="stat-value" style={{ fontSize: '1.25rem' }}>
                {formatCurrency(result.total_estimate, result.currency)}
              </div>
              <div className="stat-label">Total</div>
            </div>
          </div>
          <p style={{ marginTop: '0.75rem', fontSize: '0.85rem' }}>
            Confidence: {(result.confidence * 100).toFixed(0)}% · Risk: {result.risk_score.level}
          </p>
          <p style={{ marginTop: '0.5rem', fontSize: '0.85rem', color: 'var(--text-muted)' }}>
            {result.summary}
          </p>
        </div>
      )}
    </div>
  );
}
