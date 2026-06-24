import { COUNTRIES, type CountryCode } from './api';

const DIAL: Record<CountryCode, string> = {
  UG: '+256',
  KE: '+254',
  TZ: '+255',
  RW: '+250',
};

export function countryDial(country?: string | null): string {
  if (country && country in DIAL) return DIAL[country as CountryCode];
  return DIAL.KE;
}

export function phonePlaceholder(country?: string | null): string {
  return `${countryDial(country)}…`;
}

/** Example SMS paste text matching the signed-in user's currency and country code. */
export function smsPasteExample(currency?: string | null, country?: string | null): string {
  const code = (country && country in COUNTRIES ? country : 'KE') as CountryCode;
  const cur = currency || COUNTRIES[code].currency;
  const dialDigits = countryDial(country).slice(1);
  const amount = cur === 'KES' ? '5,000' : cur === 'UGX' ? '50,000' : cur === 'TZS' ? '120,000' : '45,000';
  const provider = code === 'KE' ? 'M-Pesa' : 'MTN Mobile Money';
  return (
    `${provider}: You have received ${cur} ${amount} from ${dialDigits}712345678. ` +
    'Transaction ID: 1234567890. Ref INV-4'
  );
}

export function demoCountryLabel(country?: string | null): string {
  const code = (country && country in COUNTRIES ? country : 'KE') as CountryCode;
  const c = COUNTRIES[code];
  return `${c.flag} ${c.name} (${c.currency})`;
}
