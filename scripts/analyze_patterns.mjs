import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { getEncoding } from "js-tiktoken";

const root = resolve(process.cwd());
const encodings = ["o200k_base", "cl100k_base"];

function readJson(relPath) {
  return JSON.parse(readFileSync(resolve(root, relPath), "utf8"));
}

function count(text, encodingName) {
  const encoder = getEncoding(encodingName);
  return encoder.encode(text).length;
}

const data = readJson("benchmarks/pattern_candidates.json");

for (const encodingName of encodings) {
  console.log(`== ${encodingName} ==`);
  for (const pattern of data.patterns) {
    console.log(`[${pattern.name}]`);
    const pyTokens = count(pattern.python, encodingName);
    console.log(`python: ${pyTokens} :: ${JSON.stringify(pattern.python)}`);
    for (const [name, snippet] of Object.entries(pattern.candidates)) {
      const tokens = count(snippet, encodingName);
      const saved = pyTokens - tokens;
      console.log(`${name}: ${tokens} :: saved=${saved} :: ${JSON.stringify(snippet)}`);
    }
    console.log("");
  }
}
