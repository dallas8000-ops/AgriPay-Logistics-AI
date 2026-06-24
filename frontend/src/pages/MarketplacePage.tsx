import { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import {
  aiApi, formatCurrency, marketplaceApi, queueOfflineAction, type PriceEstimate, type ProduceListing,
} from '../lib/api';
import PageHeader from '../components/PageHeader';
import ProduceCard from '../components/ProduceCard';

const CATEGORIES = ['All', 'Maize', 'Coffee', 'Beans', 'Banana', 'Tomato', 'Rice'];

export default function MarketplacePage() {
  const { user } = useAuth();
  const [listings, setListings] = useState<ProduceListing[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [orderModal, setOrderModal] = useState<ProduceListing | null>(null);
  const [form, setForm] = useState({ crop: '', quantity_kg: '', unit_price: '', location: '', description: '' });
  const [orderForm, setOrderForm] = useState({ quantity_kg: '', delivery_address: '' });
  const [filter, setFilter] = useState('');
  const [category, setCategory] = useState('All');
  const [msg, setMsg] = useState('');
  const [priceHint, setPriceHint] = useState<PriceEstimate | null>(null);

  const load = () => {
    const params = new URLSearchParams();
    if (filter) params.set('crop', filter);
    if (category !== 'All') params.set('crop', category);
    const qs = params.toString();
    return marketplaceApi.listings(qs || undefined).then((r) => setListings(r.results)).catch(() => {});
  };

  useEffect(() => { load(); }, [filter, category]);

  useEffect(() => {
    if (!showForm || !form.crop || !form.quantity_kg) {
      setPriceHint(null);
      return;
    }
    const qty = parseFloat(form.quantity_kg);
    if (!qty || qty <= 0) return;
    aiApi.priceEstimate({ crop: form.crop, quantity_kg: qty, country: user?.country }).then(setPriceHint).catch(() => setPriceHint(null));
  }, [showForm, form.crop, form.quantity_kg, user?.country]);

  const canSell = user?.role === 'farmer' || user?.role === 'vendor';

  const handleCreateListing = async (e: React.FormEvent) => {
    e.preventDefault();
    const data = {
      ...form,
      quantity_kg: parseFloat(form.quantity_kg),
      unit_price: parseFloat(form.unit_price),
      country: user?.country,
    };
    try {
      if (!navigator.onLine) {
        queueOfflineAction({ url: '/marketplace/listings/', method: 'POST', body: data });
        setMsg('Saved offline — will sync when connected');
      } else {
        const listing = await marketplaceApi.createListing(data);
        const guide = listing.ai_suggested_price
          ? formatCurrency(listing.ai_suggested_price, listing.currency)
          : null;
        setMsg(guide ? `Listed! Price guide: ${guide}/kg` : 'Listing published.');
      }
      setShowForm(false);
      load();
    } catch (err) {
      setMsg(err instanceof Error ? err.message : 'Failed');
    }
  };

  const handleOrder = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!orderModal) return;
    try {
      const order = await marketplaceApi.createOrder({
        listing: orderModal.id,
        quantity_kg: parseFloat(orderForm.quantity_kg),
        delivery_address: orderForm.delivery_address,
      });
      setOrderModal(null);
      window.location.href = `/payment/${order.id}`;
    } catch (err) {
      setMsg(err instanceof Error ? err.message : 'Order failed');
    }
  };

  return (
    <div className="page marketplace-page">
      <PageHeader
        title={canSell ? 'My Listings' : 'Marketplace'}
        subtitle={canSell ? 'Manage produce & reach buyers across East Africa' : 'Fresh produce from verified farmers & vendors'}
        action={canSell && (
          <button type="button" className="btn btn-primary btn-sm" onClick={() => setShowForm(!showForm)}>
            {showForm ? 'Cancel' : '+ List'}
          </button>
        )}
      />

      {msg && <div className="toast-msg">{msg}</div>}

      <div className="search-bar">
        <span className="search-icon" aria-hidden>🔍</span>
        <input
          placeholder="Search crops, locations…"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          className="search-input"
        />
      </div>

      <div className="category-chips">
        {CATEGORIES.map((c) => (
          <button
            key={c}
            type="button"
            className={`category-chip${category === c ? ' category-chip--active' : ''}`}
            onClick={() => setCategory(c)}
          >
            {c}
          </button>
        ))}
      </div>

      {showForm && (
        <form className="card form-card" onSubmit={handleCreateListing}>
          <h3 className="form-card-title">New Listing</h3>
          <div className="form-group">
            <label>Crop</label>
            <input value={form.crop} onChange={(e) => setForm({ ...form, crop: e.target.value })} required placeholder="e.g. Maize, Coffee" />
          </div>
          <div className="grid-2">
            <div className="form-group">
              <label>Quantity (kg)</label>
              <input type="number" value={form.quantity_kg} onChange={(e) => setForm({ ...form, quantity_kg: e.target.value })} required />
            </div>
            <div className="form-group">
              <label>Price/kg ({user?.currency})</label>
              <input type="number" value={form.unit_price} onChange={(e) => setForm({ ...form, unit_price: e.target.value })} required />
            </div>
          </div>
          {priceHint && (
            <div style={{ marginBottom: '0.75rem', display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
              <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                Price guide: {formatCurrency(priceHint.unit_price, priceHint.currency)}/kg
              </span>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={() => setForm((f) => ({ ...f, unit_price: String(priceHint.unit_price) }))}
              >
                Use suggestion
              </button>
            </div>
          )}
          <div className="form-group">
            <label>Location</label>
            <input value={form.location} onChange={(e) => setForm({ ...form, location: e.target.value })} required placeholder="District, region" />
          </div>
          <button type="submit" className="btn btn-primary btn-block">Publish Listing</button>
        </form>
      )}

      <div className="produce-list">
        {listings.length === 0 ? (
          <div className="empty-state-card">
            <span className="empty-state-icon">🛒</span>
            <p>No listings match your search. Try another crop or list your own produce.</p>
          </div>
        ) : (
          listings.map((l) => (
            <ProduceCard
              key={l.id}
              listing={l}
              action={user?.role === 'buyer' && (
                <button
                  type="button"
                  className="btn btn-primary btn-block produce-card-btn"
                  onClick={() => {
                    setOrderModal(l);
                    setOrderForm({ quantity_kg: String(Math.min(parseFloat(l.quantity_kg), 100)), delivery_address: '' });
                  }}
                >
                  Buy Now
                </button>
              )}
            />
          ))
        )}
      </div>

      {orderModal && (
        <div className="modal-overlay" onClick={() => setOrderModal(null)}>
          <form className="card modal" onClick={(e) => e.stopPropagation()} onSubmit={handleOrder}>
            <h3>Order {orderModal.crop}</h3>
            <p className="modal-subtitle">Pay via personal transfer — send to seller&apos;s number with reference AGR-{'{order}'}</p>
            <div className="form-group">
              <label>Quantity (kg)</label>
              <input type="number" value={orderForm.quantity_kg} onChange={(e) => setOrderForm({ ...orderForm, quantity_kg: e.target.value })} required max={orderModal.quantity_kg} />
            </div>
            <div className="form-group">
              <label>Delivery Address</label>
              <input value={orderForm.delivery_address} onChange={(e) => setOrderForm({ ...orderForm, delivery_address: e.target.value })} required />
            </div>
            <button type="submit" className="btn btn-primary btn-block">Proceed to Payment</button>
          </form>
        </div>
      )}
    </div>
  );
}
