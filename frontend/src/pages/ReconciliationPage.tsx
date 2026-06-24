import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import PageHeader from '../components/PageHeader';
import { formatCurrency, invoiceApi, ledgerApi, type LedgerEntry, type ReconciliationSummary } from '../lib/api';
import { smsDemoForInvoice, smsPasteExample } from '../lib/locale';
import { useAuth } from '../context/AuthContext';

export default function ReconciliationPage() {
  const { user } = useAuth();
  const [summary, setSummary] = useState<ReconciliationSummary | null>(null);
  const [entries, setEntries] = useState<LedgerEntry[]>([]);
  const [smsText, setSmsText] = useState('');
  const [parsedPreview, setParsedPreview] = useState<Record<string, unknown> | null>(null);
  const [msg, setMsg] = useState('');
  const [loading, setLoading] = useState(false);
  const [demoInvoiceRef, setDemoInvoiceRef] = useState<string | null>(null);

  const load = () => {
    ledgerApi.summary().then(setSummary).catch(() => {});
    ledgerApi.list().then(setEntries).catch(() => {});
    invoiceApi.list().then((invoices) => {
      const pending = invoices.find((i) => i.status === 'pending');
      if (pending) setDemoInvoiceRef(pending.payment_reference);
    }).catch(() => {});
  };

  useEffect(() => { load(); }, []);

  const fillDemoSms = () => {
    invoiceApi.list().then((invoices) => {
      const pending = invoices.find((i) => i.status === 'pending');
      if (!pending) {
        setMsg('Create a pending payment request first (Invoices → New).');
        return;
      }
      setSmsText(smsDemoForInvoice(pending.payment_reference, pending.amount, pending.currency, user?.country));
      setParsedPreview(null);
      setMsg(`Demo SMS loaded for ${pending.payment_reference} — click Record payment.`);
    }).catch(() => setMsg('Could not load invoices.'));
  };

  const handleExportCsv = async () => {
    try {
      await ledgerApi.exportCsv();
    } catch {
      setMsg('CSV export failed.');
    }
  };

  const handleParse = async () => {
    if (!smsText.trim()) return;
    setLoading(true);
    setMsg('');
    try {
      const parsed = await ledgerApi.parseSms(smsText);
      setParsedPreview(parsed);
    } catch (err) {
      setMsg(err instanceof Error ? err.message : 'Could not parse SMS');
    } finally {
      setLoading(false);
    }
  };

  const handleRecord = async () => {
    if (!smsText.trim()) return;
    setLoading(true);
    setMsg('');
    try {
      await ledgerApi.create({ raw_sms: smsText, source: 'sms_paste' });
      setSmsText('');
      setParsedPreview(null);
      setMsg('Payment recorded. Matched orders are marked paid automatically.');
      load();
    } catch (err) {
      setMsg(err instanceof Error ? err.message : 'Failed to record payment');
    } finally {
      setLoading(false);
    }
  };

  const handleMatchInvoice = async (entryId: number, invoiceId: number) => {
    try {
      await ledgerApi.matchInvoice(entryId, invoiceId);
      setMsg('Payment matched and invoice marked paid.');
      load();
    } catch (err) {
      setMsg(err instanceof Error ? err.message : 'Match failed');
    }
  };

  const handleMatch = async (entryId: number, orderId: number) => {
    try {
      await ledgerApi.match(entryId, orderId);
      setMsg('Payment matched and order marked paid.');
      load();
    } catch (err) {
      setMsg(err instanceof Error ? err.message : 'Match failed');
    }
  };

  return (
    <div className="page">
      <PageHeader
        title="Reconcile Payments"
        subtitle="Paste confirmation SMS to match payments — you verify your own inbox; we do not read your phone automatically."
        action={
          <button type="button" className="btn btn-secondary btn-sm" onClick={handleExportCsv}>
            Export CSV
          </button>
        }
      />

      {summary && (
        <div className="stat-grid" style={{ marginBottom: '1rem' }}>
          <div className="stat-card stat-card--highlight">
            <div className="stat-value">{summary.pending_orders_count}</div>
            <div className="stat-label">Awaiting payment</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{summary.unmatched_entries_count}</div>
            <div className="stat-label">Unmatched SMS</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{summary.matched_entries_count}</div>
            <div className="stat-label">Matched</div>
          </div>
        </div>
      )}

      <section className="card form-card">
        <h3 className="form-card-title">Paste confirmation SMS</h3>
        <p className="page-subtitle" style={{ marginBottom: '0.75rem' }}>
          Copy the text from your MTN, Airtel, or M-Pesa confirmation. Include reference <strong>AGR-…</strong> or <strong>INV-…</strong> if possible.
          Parser accuracy varies — always confirm amount and payer before marking paid.
        </p>
        <textarea
          value={smsText}
          onChange={(e) => setSmsText(e.target.value)}
          rows={5}
          placeholder={smsPasteExample(user?.currency, user?.country)}
          style={{ width: '100%', marginBottom: '0.75rem' }}
        />
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
          {demoInvoiceRef && (
            <button type="button" className="btn btn-secondary" onClick={fillDemoSms} disabled={loading}>
              Load demo SMS
            </button>
          )}
          <button type="button" className="btn btn-secondary" onClick={handleParse} disabled={loading}>
            Preview parse
          </button>
          <button type="button" className="btn btn-primary" onClick={handleRecord} disabled={loading || !smsText.trim()}>
            Record payment
          </button>
        </div>
        {parsedPreview && (
          <div className="toast-msg" style={{ marginTop: '0.75rem' }}>
            Parsed: {parsedPreview.amount ? `${parsedPreview.currency} ${parsedPreview.amount}` : 'amount unknown'}
            {' · '}confidence {(parsedPreview.confidence as number) * 100}%
            {(parsedPreview.suggested_orders as Array<{ id: number }>)?.length > 0 && (
              <> · suggested order #{(parsedPreview.suggested_orders as Array<{ id: number }>)[0].id}</>
            )}
          </div>
        )}
        {msg && <p className="toast-msg" style={{ marginTop: '0.75rem' }}>{msg}</p>}
      </section>

      <section className="dashboard-section">
        <h2 className="section-title">Payment ledger</h2>
        {entries.length === 0 ? (
          <div className="empty-state-card">
            <span className="empty-state-icon">📒</span>
            <p>No entries yet. Payments you receive on your personal number will appear here after you paste SMS confirmations.</p>
          </div>
        ) : (
          entries.map((entry) => (
            <article key={entry.id} className="produce-card" style={{ marginBottom: '0.75rem' }}>
              <div className="produce-card-body">
                <div className="produce-card-top">
                  <strong>
                    {entry.amount ? formatCurrency(entry.amount, entry.currency || 'KES') : 'Amount unknown'}
                  </strong>
                  <span className={`badge${entry.status === 'matched' ? '' : ' badge-tier'}`}>{entry.status}</span>
                </div>
                <p className="produce-card-meta">
                  {entry.provider || 'mobile money'} · {entry.source.replace('_', ' ')}
                  {entry.order_reference && <> · {entry.order_reference}</>}
                  {entry.invoice_reference && <> · {entry.invoice_reference}</>}
                </p>
                {entry.raw_sms && (
                  <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.35rem' }}>
                    {entry.raw_sms.slice(0, 120)}{entry.raw_sms.length > 120 ? '…' : ''}
                  </p>
                )}
                {entry.status === 'unmatched' && (entry.suggested_order_ids?.length > 0 || entry.suggested_invoice_ids?.length > 0) && (
                  <div style={{ marginTop: '0.75rem', display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                    {entry.suggested_order_ids?.map((oid) => (
                      <button
                        key={`o-${oid}`}
                        type="button"
                        className="btn btn-primary btn-sm"
                        onClick={() => handleMatch(entry.id, oid)}
                      >
                        Match order #{oid}
                      </button>
                    ))}
                    {entry.suggested_invoice_ids?.map((iid) => (
                      <button
                        key={`i-${iid}`}
                        type="button"
                        className="btn btn-secondary btn-sm"
                        onClick={() => handleMatchInvoice(entry.id, iid)}
                      >
                        Match invoice #{iid}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </article>
          ))
        )}
      </section>

      <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '1rem' }}>
        References: <strong>AGR-{'{order}'}</strong> for marketplace orders, <strong>INV-{'{invoice}'}</strong> for payment requests.
        {' '}<Link to="/invoices">Payment requests →</Link>
        {' · '}
        <Link to="/marketplace">Marketplace orders →</Link>
      </p>
    </div>
  );
}
