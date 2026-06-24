import { Link } from 'react-router-dom';
import { cropIcon } from '../lib/crops';
import { formatCurrency, type ProduceListing } from '../lib/api';

interface ProduceCardProps {
  listing: ProduceListing;
  action?: React.ReactNode;
  compact?: boolean;
}

export default function ProduceCard({ listing, action, compact }: ProduceCardProps) {
  return (
    <article className={`produce-card${compact ? ' produce-card--compact' : ''}`}>
      <div className="produce-card-icon" aria-hidden>{cropIcon(listing.crop)}</div>
      <div className="produce-card-body">
        <div className="produce-card-top">
          <div>
            <h3 className="produce-card-title">{listing.crop}</h3>
            {listing.variety && <span className="produce-card-variety">{listing.variety}</span>}
          </div>
          <span className="badge badge-country">{listing.country}</span>
        </div>
        <p className="produce-card-meta">
          <span>📍 {listing.location}</span>
          <span>·</span>
          <span>{listing.quantity_kg} kg</span>
          {listing.season && (
            <>
              <span>·</span>
              <span>{listing.season}</span>
            </>
          )}
        </p>
        <div className="produce-card-footer">
          <div>
            <p className="produce-card-price">{formatCurrency(listing.unit_price, listing.currency)}/kg</p>
            {listing.ai_suggested_price && (
              <p className="produce-card-ai">
                Guide: {formatCurrency(listing.ai_suggested_price, listing.currency)}/kg
              </p>
            )}
          </div>
          {listing.seller_name && !compact && (
            <span className="produce-card-seller">{listing.seller_name}</span>
          )}
        </div>
        {action}
      </div>
    </article>
  );
}

export function ProduceCardLink({ listing }: { listing: ProduceListing }) {
  return (
    <Link to="/marketplace" className="produce-card-link">
      <ProduceCard listing={listing} compact />
    </Link>
  );
}
