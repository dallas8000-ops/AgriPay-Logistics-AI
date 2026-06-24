import { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { aiApi, COUNTRIES, formatCurrency, type CountryCode, type PriceEstimate } from '../lib/api';

const CROPS = ['maize', 'beans', 'coffee', 'tea', 'bananas', 'tomatoes', 'potatoes', 'avocado', 'rice', 'onions'];
const SEASONS = [
  { value: 'long_rains', label: 'Long Rains' },
  { value: 'short_rains', label: 'Short Rains' },
  { value: 'dry', label: 'Dry Season' },
];

export default function AIPricingPage() {
  const { user } = useAuth();
  const [crop, setCrop] = useState('maize');
  const [country, setCountry] = useState<CountryCode>((user?.country as CountryCode) || 'UG');
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
        country,
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
      <h1 className="page-title">Crop Price Guide</h1>
      <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginBottom: '1rem' }}>
        Multinational wholesale benchmarks (Uganda, Kenya, Tanzania, Rwanda) with live USD→local FX.
        Snapshots are RATIN-aligned — verify at your local market before listing.
      </p>

      <div className="card">
        <div className="form-group">
          <label>Country</label>
          <select value={country} onChange={(e) => setCountry(e.target.value as CountryCode)}>
            {(Object.keys(COUNTRIES) as CountryCode[]).map((code) => (
              <option key={code} value={code}>
                {COUNTRIES[code].flag} {COUNTRIES[code].name} ({COUNTRIES[code].currency})
              </option>
            ))}
          </select>
        </div>
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
          {loading ? 'Calculating…' : 'Get estimate'}
        </button>
      </div>

      {result && (
        <div className="card" style={{ marginTop: '1rem' }}>
          <h3 style={{ marginBottom: '0.75rem' }}>
            {result.crop} — {COUNTRIES[country]?.flag} {result.currency}
          </h3>
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
            {result.method === 'live_market' ? ' · Live market quote' : ' · FX-adjusted estimate'}
          </p>
          {result.market && (
            <p style={{ marginTop: '0.5rem', fontSize: '0.85rem', color: 'var(--text-muted)' }}>
              {result.market.name}
              {result.market.observed_date ? ` · observed ${result.market.observed_date}` : ''}
              {result.market.day_change_pct != null && (
                <> · day {result.market.day_change_pct > 0 ? '+' : ''}{result.market.day_change_pct}%</>
              )}
              {result.market.month_change_pct != null && (
                <> · month {result.market.month_change_pct > 0 ? '+' : ''}{result.market.month_change_pct}%</>
              )}
            </p>
          )}
          {result.fx && (
            <p style={{ marginTop: '0.35rem', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              FX {result.fx.base}/{result.fx.quote}: {result.fx.rate.toLocaleString(undefined, { maximumFractionDigits: 2 })}
              {result.fx.live ? ' (live)' : ' (fallback)'}
              {result.fx.updated_at ? ` · ${result.fx.updated_at}` : ''}
            </p>
          )}
          <p style={{ marginTop: '0.5rem', fontSize: '0.85rem', color: 'var(--text-muted)' }}>
            {result.summary}
          </p>
          {result.method_note && (
            <p style={{ marginTop: '0.75rem', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              {result.method_note}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
