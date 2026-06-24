import { spawnSync } from "child_process";

const service = process.argv[2];
const configJson = process.argv[3];
const extraArgs = process.argv.slice(4);

if (!service || !configJson) {
  console.error("Usage: node stripe-add-config.mjs <provider/service> <config-json> [extra stripe args...]");
  process.exit(1);
}

JSON.parse(configJson);

const args = [
  "projects",
  "add",
  service,
  "--config",
  configJson,
  "--yes",
  "--accept-tos",
  "--non-interactive",
  ...extraArgs,
];

const result = spawnSync("stripe", args, { encoding: "utf8", shell: true });
if (result.stdout) process.stdout.write(result.stdout);
if (result.stderr) process.stderr.write(result.stderr);
process.exit(result.status ?? 1);
