import fs from "fs";

const envPath = process.argv[2] ?? ".env";
const env = fs.readFileSync(envPath, "utf8");
const match = env.match(/^AGRIPAY_DB_VARIABLES=(.*)$/m);

if (!match) {
  process.exit(1);
}

let raw = match[1].trim();
if (
  (raw.startsWith("'") && raw.endsWith("'")) ||
  (raw.startsWith('"') && raw.endsWith('"'))
) {
  raw = raw.slice(1, -1);
}

const parsed = JSON.parse(raw);
const databaseUrl = parsed.DATABASE_URL ?? parsed.DATABASE_PUBLIC_URL ?? "";
if (!databaseUrl) {
  process.exit(1);
}

process.stdout.write(databaseUrl);
