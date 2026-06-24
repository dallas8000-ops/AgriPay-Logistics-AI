const CROP_ICONS: Record<string, string> = {
  maize: '🌽',
  corn: '🌽',
  coffee: '☕',
  tea: '🍵',
  banana: '🍌',
  beans: '🫘',
  rice: '🍚',
  wheat: '🌾',
  tomato: '🍅',
  potato: '🥔',
  avocado: '🥑',
  mango: '🥭',
  cassava: '🥔',
  sorghum: '🌾',
  default: '🥬',
};

export function cropIcon(name: string): string {
  const key = name.toLowerCase().trim();
  for (const [crop, icon] of Object.entries(CROP_ICONS)) {
    if (key.includes(crop)) return icon;
  }
  return CROP_ICONS.default;
}

export const ROLE_LABELS: Record<string, string> = {
  farmer: 'Farmer',
  vendor: 'Market Vendor',
  buyer: 'Produce Buyer',
  driver: 'Truck Driver',
  admin: 'Platform Admin',
};
