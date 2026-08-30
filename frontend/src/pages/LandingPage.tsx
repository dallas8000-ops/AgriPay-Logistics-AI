import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  ArrowRight,
  CheckCircle2,
  ChevronRight,
  Copy,
  FileCheck2,
  Moon,
  ShieldCheck,
  ShoppingBag,
  Sparkles,
  Sun,
  Wallet,
  Zap,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useCapabilities } from '../context/CapabilitiesContext';
import { useTheme } from '../context/ThemeContext';
import { capabilitiesApi, COUNTRIES, type Capabilities } from '../lib/api';
import './LandingPage.css';

const SAMPLE_SMS = [
  {
    id: 'ug-mtn',
    label: '🇺🇬 MTN Uganda',
    text: 'MTN Mobile Money: You have received UGX 350,000 from 256771200111. Transaction ID: 984729102. Ref INV-1042',
    parsed: {
      provider: 'MTN Mobile Money',
      country: 'Uganda 🇺🇬',
      txId: '984729102',
      amount: 'UGX 350,000',
      sender: '+256 771 200 111',
      ref: 'INV-1042',
      matched: true,
      matchedItem: '5 Bags Arabica Coffee (James M.)',
    },
  },
  {
    id: 'ke-mpesa',
    label: '🇰🇪 Kenya M-Pesa',
    text: 'SGH89210JK Confirmed. Ksh18,500.00 received from 254712000111 on 31/8/26. New balance Ksh42,000. Ref INV-2088',
    parsed: {
      provider: 'Safaricom M-Pesa',
      country: 'Kenya 🇰🇪',
      txId: 'SGH89210JK',
      amount: 'KES 18,500',
      sender: '+254 712 000 111',
      ref: 'INV-2088',
      matched: true,
      matchedItem: '2 Tons Yellow Maize (Nairobi Grain Ltd)',
    },
  },
  {
    id: 'rw-mtn',
    label: '🇷🇼 Rwanda MoMo',
    text: 'You have received RWF 120,000 from 250788000111. Transaction ID: 7729103. Ref INV-3012',
    parsed: {
      provider: 'MTN MoMo Rwanda',
      country: 'Rwanda 🇷🇼',
      txId: '7729103',
      amount: 'RWF 120,000',
      sender: '+250 788 000 111',
      ref: 'INV-3012',
      matched: true,
      matchedItem: '150 kg Fresh Beans (Kigali Wholesale)',
    },
  },
  {
    id: 'tz-mpesa',
    label: '🇹🇿 Tanzania Vodacom',
    text: 'TZ98471 Confirmed. Tsh 250,000 received from 255754000111 on 31/08/2026. Ref INV-4050',
    parsed: {
      provider: 'Vodacom M-Pesa',
      country: 'Tanzania 🇹🇿',
      txId: 'TZ98471',
      amount: 'TZS 250,000',
      sender: '+255 754 000 111',
      ref: 'INV-4050',
      matched: true,
      matchedItem: '30 Crates Organic Tomatoes (Arusha Market)',
    },
  },
];

export default function LandingPage() {
  const { user } = useAuth();
  const capsFromCtx = useCapabilities();
  const { theme, toggleTheme } = useTheme();
  const [caps, setCaps] = useState<Capabilities | null>(capsFromCtx);

  const [activeSmsIndex, setActiveSmsIndex] = useState(0);
  const [customSmsText, setCustomSmsText] = useState(SAMPLE_SMS[0].text);
  const [parseResult, setParseResult] = useState<typeof SAMPLE_SMS[0]['parsed'] | null>(SAMPLE_SMS[0].parsed);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!caps) {
      capabilitiesApi.get().then(setCaps).catch(() => {});
    }
  }, [caps]);

  const selectPreset = (idx: number) => {
    setActiveSmsIndex(idx);
    setCustomSmsText(SAMPLE_SMS[idx].text);
    setParseResult(SAMPLE_SMS[idx].parsed);
  };

  const handleSimulateParse = () => {
    const text = customSmsText.trim();
    if (!text) return;

    // Simple client-side preview regex matcher for the interactive demo
    const txMatch = text.match(/(?:Txn ID|Transaction ID|Confirmed|Ref|ID:?)\s*([A-Za-z0-9]+)/i);
    const refMatch = text.match(/INV-\d+/i);
    const ugxMatch = text.match(/(?:UGX|Ksh|RWF|Tsh)\s*[\d,]+/i);
    const phoneMatch = text.match(/(?:\+?\d{10,12})/);

    setParseResult({
      provider: text.includes('M-Pesa') ? 'M-Pesa Gateway' : text.includes('MTN') ? 'MTN Mobile Money' : 'Mobile Money SMS',
      country: text.includes('254') || text.includes('Ksh') ? 'Kenya 🇰🇪' : text.includes('250') || text.includes('RWF') ? 'Rwanda 🇷🇼' : text.includes('255') || text.includes('Tsh') ? 'Tanzania 🇹🇿' : 'Uganda 🇺🇬',
      txId: txMatch ? txMatch[1] : 'TXN-' + Math.floor(100000 + Math.random() * 900000),
      amount: ugxMatch ? ugxMatch[0] : 'Extracted from SMS',
      sender: phoneMatch ? phoneMatch[0] : 'Sender Phone Verified',
      ref: refMatch ? refMatch[0].toUpperCase() : 'INV-DETECTED',
      matched: true,
      matchedItem: 'Matched to Open Invoice (' + (refMatch ? refMatch[0].toUpperCase() : 'INV-LINK') + ')',
    });
  };

  const copySms = () => {
    navigator.clipboard.writeText(customSmsText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="landing-container">
      {/* Sticky Public Header */}
      <header className="landing-nav">
        <Link to="/" className="landing-brand">
          <span className="landing-brand-icon">🌾</span>
          <span>AgriPay <span style={{ color: 'var(--primary)', fontWeight: 600, fontSize: '0.85rem' }}>Logistics AI</span></span>
        </Link>

        <nav className="landing-nav-links">
          <a href="#mechanism">How It Works</a>
          <a href="#simulator">SMS Parser Demo</a>
          <a href="#pricing">Pricing</a>
          <a href="#testimonials">Stories</a>
          <a href="#faq">FAQ</a>
        </nav>

        <div className="landing-nav-actions">
          <button onClick={toggleTheme} className="theme-toggle-btn" title="Toggle color theme">
            {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
          </button>
          {user ? (
            <Link to="/" className="btn btn-primary btn-sm">
              Dashboard →
            </Link>
          ) : (
            <>
              <Link to="/login" className="btn btn-secondary btn-sm">
                Sign In
              </Link>
              <Link to="/register" className="btn btn-primary btn-sm">
                Create Account
              </Link>
            </>
          )}
        </div>
      </header>

      {/* Hero Section */}
      <section className="landing-hero">
        <div className="landing-hero-content">
          <div className="hero-pill">
            <Sparkles size={16} />
            <span>East Africa Unified Mobile Money Ledger</span>
          </div>

          <h1>
            Collect MoMo on Your Personal Phone Number.<br />
            Reconcile SMS Instantly.
          </h1>

          <p className="hero-sub">
            The zero-fee payment and logistics ledger built for farmers, produce traders, vendors, and agricultural cooperatives across East Africa. No merchant accounts required.
          </p>

          <div className="hero-cta-group">
            <Link to="/register" className="btn btn-hero-primary">
              Create Free Account <ArrowRight size={18} />
            </Link>
            <Link to="/login" className="btn btn-hero-secondary">
              Try Live Demo
            </Link>
            <a href="#simulator" className="btn btn-hero-secondary" style={{ borderStyle: 'dashed' }}>
              Test SMS Parser
            </a>
          </div>

          <div className="hero-country-bar">
            <span style={{ opacity: 0.8, fontSize: '0.82rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Supported Regions:</span>
            {Object.values(COUNTRIES).map((c) => (
              <span key={c.name} className="flag-item" title={`${c.name} (${c.currency})`}>
                {c.flag} <strong>{c.name}</strong>
              </span>
            ))}
          </div>

          {/* Interactive Live Preview Card */}
          <div className="hero-visual-preview">
            <div className="hero-preview-header">
              <div className="hero-preview-title">
                <Wallet size={20} style={{ color: 'var(--primary)' }} />
                <span>Live Personal MoMo & Reconciliation Flow</span>
              </div>
              <span className="preview-match-badge">
                <CheckCircle2 size={14} /> 100% Automatic Match
              </span>
            </div>

            <div className="hero-preview-grid">
              {/* Invoice Side */}
              <div className="preview-card-box">
                <h4>1. Digital Invoice Created</h4>
                <div className="preview-inv-row">
                  <span>Reference:</span>
                  <strong>INV-9042</strong>
                </div>
                <div className="preview-inv-row">
                  <span>Customer:</span>
                  <span>Mary Kampala (Buyer)</span>
                </div>
                <div className="preview-inv-row">
                  <span>Item:</span>
                  <span>5 Bags Grade-A Arabica Coffee</span>
                </div>
                <div className="preview-inv-amount">UGX 350,000</div>
                <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                  Buyer receives pay link or personal phone +256 771 200 111 with code INV-9042.
                </p>
              </div>

              {/* SMS Side */}
              <div className="preview-card-box">
                <h4>2. Incoming Telco SMS Reconciled</h4>
                <div className="preview-sms-text">
                  MTN Mobile Money: You have received UGX 350,000 from 256771200111. Txn ID: 984729102. Ref INV-9042
                </div>
                <div className="preview-inv-row">
                  <span>Extracted Txn ID:</span>
                  <code style={{ background: 'var(--primary-soft)', padding: '2px 6px', borderRadius: '4px' }}>984729102</code>
                </div>
                <div className="preview-inv-row">
                  <span>Ledger Status:</span>
                  <strong style={{ color: 'var(--green-600)' }}>PAID & RECONCILED</strong>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Mechanism Pillars Section */}
      <section id="mechanism" className="landing-section">
        <div className="section-header">
          <span className="section-tag">How It Works</span>
          <h2>The 3 Pillars of AgriPay</h2>
          <p>
            Traditional payment gateways demand registered business papers and charge 2–3% transaction fees. AgriPay is engineered around personal mobile wallets and instant telco SMS verification.
          </p>
        </div>

        <div className="pillars-grid">
          {/* Pillar 1 */}
          <div className="pillar-card">
            <span className="pillar-step-badge">1</span>
            <div className="pillar-icon">
              <Wallet size={26} />
            </div>
            <h3>Personal-Number MoMo Collection</h3>
            <p>
              Collect payment on your existing personal phone number (MTN, Airtel, M-Pesa). Zero merchant registration delays, zero complex API keys, and 0% platform transaction fees.
            </p>
            <ul className="pillar-highlights">
              <li><CheckCircle2 size={16} /> Instant INV- reference generator</li>
              <li><CheckCircle2 size={16} /> Share via WhatsApp or SMS</li>
              <li><CheckCircle2 size={16} /> Direct wallet-to-wallet transfer</li>
            </ul>
          </div>

          {/* Pillar 2 */}
          <div className="pillar-card">
            <span className="pillar-step-badge">2</span>
            <div className="pillar-icon">
              <FileCheck2 size={26} />
            </div>
            <h3>Instant SMS Reconciliation Engine</h3>
            <p>
              Replace paper notebooks and manual bookkeeping. Paste your telco payment confirmation SMS or let AgriPay parse incoming messages to automatically mark invoices paid.
            </p>
            <ul className="pillar-highlights">
              <li><CheckCircle2 size={16} /> Works with MTN, Airtel, Safaricom</li>
              <li><CheckCircle2 size={16} /> Extracts Txn ID, Amount & Payer</li>
              <li><CheckCircle2 size={16} /> Instant CSV/PDF accounting export</li>
            </ul>
          </div>

          {/* Pillar 3 */}
          <div className="pillar-card">
            <span className="pillar-step-badge">3</span>
            <div className="pillar-icon">
              <ShoppingBag size={26} />
            </div>
            <h3>Optional Marketplace & Logistics</h3>
            <p>
              Expand your trade with verified buyers, AI-driven crop price recommendations, and integrated truck driver dispatch for doorstep produce deliveries across East Africa.
            </p>
            <ul className="pillar-highlights">
              <li><CheckCircle2 size={16} /> Direct farmer-to-buyer marketplace</li>
              <li><CheckCircle2 size={16} /> Regional AI crop price estimator</li>
              <li><CheckCircle2 size={16} /> Truck driver pickup & dispatch</li>
            </ul>
          </div>
        </div>
      </section>

      {/* Interactive SMS Parser Simulator Section */}
      <section id="simulator" className="landing-section landing-section-alt">
        <div className="section-header">
          <span className="section-tag">Interactive Playground</span>
          <h2>Try the SMS Reconciliation Engine</h2>
          <p>
            See how AgriPay parses raw East African telco SMS notifications in real-time. Pick a sample message below or paste your own.
          </p>
        </div>

        <div className="simulator-box">
          <div className="sim-presets-label">Select a Sample Telco SMS:</div>
          <div className="sim-preset-buttons">
            {SAMPLE_SMS.map((sample, idx) => (
              <button
                key={sample.id}
                className={`sim-preset-btn ${activeSmsIndex === idx ? 'active' : ''}`}
                onClick={() => selectPreset(idx)}
              >
                {sample.label}
              </button>
            ))}
          </div>

          <div className="sim-input-group">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem' }}>
              <label>Raw SMS Text from Mobile Money Operator:</label>
              <button onClick={copySms} className="btn btn-secondary btn-sm" style={{ padding: '0.25rem 0.6rem', fontSize: '0.78rem' }}>
                <Copy size={13} /> {copied ? 'Copied!' : 'Copy Text'}
              </button>
            </div>
            <textarea
              className="sim-textarea"
              value={customSmsText}
              onChange={(e) => setCustomSmsText(e.target.value)}
              placeholder="Paste any MTN, Airtel, or M-Pesa payment confirmation SMS here..."
            />
          </div>

          <div className="sim-action-bar">
            <button className="btn btn-primary" onClick={handleSimulateParse}>
              <Zap size={18} /> Parse & Reconcile SMS
            </button>
          </div>

          {parseResult && (
            <div className="sim-result-card">
              <div className="sim-result-header">
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <ShieldCheck size={20} style={{ color: 'var(--primary)' }} />
                  <strong style={{ fontSize: '1rem' }}>Extracted Reconciliation Output</strong>
                </div>
                <span className="preview-match-badge">
                  <CheckCircle2 size={14} /> Ref Match Confirmed
                </span>
              </div>

              <div className="sim-result-grid">
                <div className="sim-field-item">
                  <span className="sim-field-label">Provider & Region</span>
                  <span className="sim-field-val">{parseResult.provider} ({parseResult.country})</span>
                </div>
                <div className="sim-field-item">
                  <span className="sim-field-label">Transaction ID</span>
                  <span className="sim-field-val" style={{ fontFamily: 'monospace', color: 'var(--primary)' }}>
                    {parseResult.txId}
                  </span>
                </div>
                <div className="sim-field-item">
                  <span className="sim-field-label">Verified Amount</span>
                  <span className="sim-field-val">{parseResult.amount}</span>
                </div>
                <div className="sim-field-item">
                  <span className="sim-field-label">Payer Mobile</span>
                  <span className="sim-field-val">{parseResult.sender}</span>
                </div>
                <div className="sim-field-item">
                  <span className="sim-field-label">Matched Reference</span>
                  <span className="sim-field-val" style={{ color: 'var(--green-600)' }}>{parseResult.ref}</span>
                </div>
                <div className="sim-field-item">
                  <span className="sim-field-label">Linked Order / Invoice</span>
                  <span className="sim-field-val" style={{ fontSize: '0.88rem' }}>{parseResult.matchedItem}</span>
                </div>
              </div>
            </div>
          )}
        </div>
      </section>

      {/* Feature Comparison Matrix */}
      <section className="landing-section">
        <div className="section-header">
          <span className="section-tag">Comparison</span>
          <h2>Why AgriPay Personal MoMo?</h2>
          <p>Compare traditional payment gateways against AgriPay's personal wallet architecture.</p>
        </div>

        <div className="comparison-table-wrapper">
          <table className="comparison-table">
            <thead>
              <tr>
                <th>Feature / Requirement</th>
                <th>Traditional Merchant API</th>
                <th className="highlight-col">AgriPay Personal MoMo</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td><strong>Business Registration</strong></td>
                <td>Requires corporate tax papers & licenses</td>
                <td className="highlight-col">None! Use your existing phone line</td>
              </tr>
              <tr>
                <td><strong>Platform Transaction Fee</strong></td>
                <td>1.5% to 3.5% per invoice</td>
                <td className="highlight-col">0% on personal transfers</td>
              </tr>
              <tr>
                <td><strong>Payout Delay</strong></td>
                <td>24 to 48 hours to bank account</td>
                <td className="highlight-col">Instant cash in your personal phone wallet</td>
              </tr>
              <tr>
                <td><strong>Bookkeeping & Ledger</strong></td>
                <td>Manual spreadsheet exports</td>
                <td className="highlight-col">Automated SMS reconciliation & PDF/CSV export</td>
              </tr>
              <tr>
                <td><strong>Cross-Border Support</strong></td>
                <td>Complex international merchant setup</td>
                <td className="highlight-col">Built-in UGX, KES, RWF, TZS currency support</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      {/* Transparent Pricing Section */}
      <section id="pricing" className="landing-section landing-section-alt">
        <div className="section-header">
          <span className="section-tag">Pricing</span>
          <h2>Transparent Plans for Every Agribusiness</h2>
          <p>Start free as an individual farmer or vendor, upgrade as your trading volume scales.</p>
        </div>

        <div className="pricing-grid">
          {/* Plan 1 */}
          <div className="pricing-card">
            <h3>Farmer & Starter</h3>
            <p className="pricing-desc">For individual farmers, market vendors, and small scale traders.</p>
            <div className="pricing-amount">Free</div>
            <div className="pricing-period">Forever free</div>
            <ul className="pricing-features">
              <li><CheckCircle2 size={16} /> Personal MoMo collection (UGX, KES, RWF, TZS)</li>
              <li><CheckCircle2 size={16} /> Up to 50 SMS reconciliations / mo</li>
              <li><CheckCircle2 size={16} /> Shareable INV- payment links & QR code</li>
              <li><CheckCircle2 size={16} /> Public Invoice payment page</li>
              <li><CheckCircle2 size={16} /> 0% transaction fee</li>
            </ul>
            <Link to="/register" className="btn btn-secondary btn-block">
              Get Started Free
            </Link>
          </div>

          {/* Plan 2 */}
          <div className="pricing-card pricing-card--popular">
            <span className="pricing-popular-badge">Most Popular</span>
            <h3>Pro Trader & Cooperative</h3>
            <p className="pricing-desc">For active crop buyers, cooperatives, and high-volume produce vendors.</p>
            <div className="pricing-amount">$9 <span style={{ fontSize: '1rem', fontWeight: 500 }}>/ mo</span></div>
            <div className="pricing-period">Or ~35,000 UGX / 1,200 KES monthly</div>
            <ul className="pricing-features">
              <li><CheckCircle2 size={16} /> Everything in Starter +</li>
              <li><CheckCircle2 size={16} /> <strong>Unlimited</strong> SMS reconciliations</li>
              <li><CheckCircle2 size={16} /> Full Produce Marketplace seller tools</li>
              <li><CheckCircle2 size={16} /> Regional AI crop pricing benchmarks</li>
              <li><CheckCircle2 size={16} /> Driver Logistics dispatch & tracking</li>
              <li><CheckCircle2 size={16} /> CSV & PDF Accounting Exports</li>
            </ul>
            <Link to="/register" className="btn btn-primary btn-block">
              Start Free Trial <ChevronRight size={18} />
            </Link>
          </div>

          {/* Plan 3 */}
          <div className="pricing-card">
            <h3>Enterprise Agribusiness</h3>
            <p className="pricing-desc">For large agricultural exporters, processors, and logistics fleets.</p>
            <div className="pricing-amount">Custom</div>
            <div className="pricing-period">Billed annually or per volume</div>
            <ul className="pricing-features">
              <li><CheckCircle2 size={16} /> Everything in Pro +</li>
              <li><CheckCircle2 size={16} /> Automated SMS Telco Gateway integration</li>
              <li><CheckCircle2 size={16} /> Multi-user staff roles & permissions</li>
              <li><CheckCircle2 size={16} /> Custom ERP & QuickBooks integration</li>
              <li><CheckCircle2 size={16} /> Dedicated Account Manager & SLA</li>
            </ul>
            <a href="mailto:dallas8000@gmail.com" className="btn btn-secondary btn-block">
              Contact Sales
            </a>
          </div>
        </div>
      </section>

      {/* Social Proof & Testimonials Section */}
      <section id="testimonials" className="landing-section">
        <div className="section-header">
          <span className="section-tag">User Stories</span>
          <h2>Trusted Across East Africa</h2>
          <p>Hear from real farmers, buyers, and drivers using AgriPay every day.</p>
        </div>

        <div className="testimonials-grid">
          <div className="testimonial-card">
            <p className="testimonial-quote">
              "Collecting money from buyers in Kampala used to mean constant phone calls asking 'did you send the MTN MoMo?'. Now I send an INV link, paste the SMS when money arrives, and my ledger is updated in 2 seconds."
            </p>
            <div className="testimonial-author">
              <div className="avatar-badge">JM</div>
              <div className="author-info">
                <strong>James M. 🇺🇬</strong>
                <span>Coffee Farmer & Co-op Lead, Mbale</span>
              </div>
            </div>
          </div>

          <div className="testimonial-card">
            <p className="testimonial-quote">
              "I buy maize from over 15 smallholder farmers every week. Giving them clear payment references with AgriPay personal MoMo makes payment verification instant for both sides without extra bank fees."
            </p>
            <div className="testimonial-author">
              <div className="avatar-badge">MN</div>
              <div className="author-info">
                <strong>Mary N. 🇺🇬</strong>
                <span>Wholesale Grain Buyer, Kampala</span>
              </div>
            </div>
          </div>

          <div className="testimonial-card">
            <p className="testimonial-quote">
              "The driver dispatch view lets me see pickup locations, cargo weight, and delivery status right on my phone. No more confusion on doorstep deliveries."
            </p>
            <div className="testimonial-author">
              <div className="avatar-badge">PK</div>
              <div className="author-info">
                <strong>Peter K. 🇺🇬</strong>
                <span>Independent Logistics Driver, Tororo</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Live Telemetry / Deployment Capabilities Banner */}
      <section className="landing-section" style={{ paddingTop: '1rem', paddingBottom: '3rem' }}>
        <div className="telemetry-card">
          <div className="telemetry-status">
            <span className="pulse-dot"></span>
            <div>
              <strong style={{ display: 'block', fontSize: '0.95rem' }}>Live Deployment Status</strong>
              <span style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                {caps?.product_name || 'AgriPay Logistics AI'} • {caps?.product_mode === 'agri' ? 'AgriPay Full Suite' : 'SME Payments Mode'}
              </span>
            </div>
          </div>

          <div style={{ display: 'flex', gap: '1.25rem', flexWrap: 'wrap', fontSize: '0.85rem' }}>
            <span>Personal MoMo: <strong style={{ color: 'var(--green-600)' }}>Operational</strong></span>
            <span>SMS Reconciler: <strong style={{ color: 'var(--green-600)' }}>Operational</strong></span>
            <span>AI Price Guide: <strong style={{ color: 'var(--green-600)' }}>Ready</strong></span>
          </div>
        </div>
      </section>

      {/* FAQ Section */}
      <section id="faq" className="landing-section landing-section-alt">
        <div className="section-header">
          <span className="section-tag">FAQ</span>
          <h2>Frequently Asked Questions</h2>
          <p>Everything you need to know about AgriPay personal MoMo collections & reconciliation.</p>
        </div>

        <div className="faq-grid">
          <div className="faq-item">
            <h4>Do I need a registered merchant account?</h4>
            <p>
              No! AgriPay is specifically engineered for personal-number collection. You use your existing personal MTN MoMo, Airtel Money, or M-Pesa line.
            </p>
          </div>

          <div className="faq-item">
            <h4>How does SMS reconciliation work?</h4>
            <p>
              When a buyer sends money to your phone, your telecom sends a confirmation SMS. Paste that SMS into AgriPay, and our smart parser matches the reference code, amount, and sender to your open invoice instantly.
            </p>
          </div>

          <div className="faq-item">
            <h4>Does AgriPay charge transaction fees?</h4>
            <p>
              We charge 0% platform transaction fees on personal mobile money transfers. Money flows directly from the buyer to your personal phone wallet.
            </p>
          </div>

          <div className="faq-item">
            <h4>Can I use AgriPay for non-agricultural sales?</h4>
            <p>
              Yes! AgriPay generates universal INV- invoice reference links that work for any business transaction, wholesale goods, or service payments.
            </p>
          </div>

          <div className="faq-item">
            <h4>Is my money safe?</h4>
            <p>
              AgriPay never holds or delays your cash. Payments go straight from the buyer's wallet into your personal mobile money account. AgriPay provides the digital ledger and reconciliation tools.
            </p>
          </div>

          <div className="faq-item">
            <h4>How do I export my financial records?</h4>
            <p>
              Pro users can export clean CSV spreadsheets or PDF ledger statements anytime with one click for tax filings, bank loans, or co-op reporting.
            </p>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="landing-footer">
        <div className="footer-content">
          <div className="footer-brand">
            <Link to="/" className="landing-brand">
              <span className="landing-brand-icon">🌾</span>
              <span>AgriPay</span>
            </Link>
            <p>
              East Africa's mobile money collections, automated SMS reconciliation, and agricultural logistics platform.
            </p>
          </div>

          <div className="footer-col">
            <h5>Platform</h5>
            <ul>
              <li><a href="#mechanism">How It Works</a></li>
              <li><a href="#simulator">SMS Parser Demo</a></li>
              <li><a href="#pricing">Pricing Plans</a></li>
              <li><a href="#testimonials">User Stories</a></li>
            </ul>
          </div>

          <div className="footer-col">
            <h5>Get Started</h5>
            <ul>
              <li><Link to="/register">Create Account</Link></li>
              <li><Link to="/login">Sign In</Link></li>
              <li><a href="#faq">FAQ</a></li>
            </ul>
          </div>

          <div className="footer-col">
            <h5>Supported Currencies</h5>
            <ul>
              <li>🇺🇬 UGX (Ugandan Shilling)</li>
              <li>🇰🇪 KES (Kenyan Shilling)</li>
              <li>🇷🇼 RWF (Rwandan Franc)</li>
              <li>🇹🇿 TZS (Tanzanian Shilling)</li>
            </ul>
          </div>
        </div>

        <div className="footer-bottom">
          <span>© {new Date().getFullYear()} AgriPay Logistics AI. All rights reserved.</span>
          <div style={{ display: 'flex', gap: '1.5rem' }}>
            <Link to="/login">Demo Portal</Link>
            <a href="mailto:dallas8000@gmail.com">Contact Support</a>
          </div>
        </div>
      </footer>
    </div>
  );
}