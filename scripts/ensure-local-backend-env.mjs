import fs from "fs";
import path from "path";

const envPath = process.argv[2] ?? path.join("backend", ".env");
const required = {
  USE_SQLITE: "True",
  DEBUG: "True",
  CORS_ALLOWED_ORIGINS: "http://127.0.0.1:5174,http://localhost:5174",
};

let lines = [];
if (fs.existsSync(envPath)) {
  lines = fs.readFileSync(envPath, "utf8").split(/\r?\n/);
}

const seen = new Set();
const out = [];

for (const line of lines) {
  const match = line.match(/^([^=]+)=/);
  if (!match) {
    out.push(line);
    continue;
  }
  const key = match[1].trim();
  if (key in required) {
    out.push(`${key}=${required[key]}`);
    seen.add(key);
  } else {
    out.push(line);
  }
}

for (const [key, value] of Object.entries(required)) {
  if (!seen.has(key)) {
    out.push(`${key}=${value}`);
  }
}

fs.writeFileSync(envPath, out.join("\n").replace(/\n+$/, "") + "\n");
console.log(`Updated ${envPath} for local dev (USE_SQLITE, DEBUG).`);
