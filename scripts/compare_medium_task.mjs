import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { getEncoding } from "js-tiktoken";

const root = resolve(process.cwd());
const encodings = ["o200k_base", "cl100k_base"];

function read(relPath) {
  return readFileSync(resolve(root, relPath), "utf8").trim();
}

function count(text, encodingName) {
  const encoder = getEncoding(encodingName);
  return encoder.encode(text).length;
}

function pct(saved, base) {
  if (!base) {
    return "0.00";
  }
  return ((saved / base) * 100).toFixed(2);
}

const task = read("benchmarks/medium_task_prompt.txt");
const pythonCode = read("benchmarks/medium_task.py");
const dslCode = read("benchmarks/medium_task.aidl");

const pythonAnswer = `Task:\n${task}\n\nUse Python.\n\n${pythonCode}`;
const dslAnswer = `Task:\n${task}\n\nUse the DSL.\n\n${dslCode}`;

for (const encodingName of encodings) {
  const pyCodeTokens = count(pythonCode, encodingName);
  const dslCodeTokens = count(dslCode, encodingName);
  const pyAnswerTokens = count(pythonAnswer, encodingName);
  const dslAnswerTokens = count(dslAnswer, encodingName);

  console.log(`== ${encodingName} ==`);
  console.log(`python_code_tokens: ${pyCodeTokens}`);
  console.log(`dsl_code_tokens: ${dslCodeTokens}`);
  console.log(`code_tokens_saved: ${pyCodeTokens - dslCodeTokens}`);
  console.log(`code_saving_percent: ${pct(pyCodeTokens - dslCodeTokens, pyCodeTokens)}%`);
  console.log(`python_answer_tokens: ${pyAnswerTokens}`);
  console.log(`dsl_answer_tokens: ${dslAnswerTokens}`);
  console.log(`answer_tokens_saved: ${pyAnswerTokens - dslAnswerTokens}`);
  console.log(
    `answer_saving_percent: ${pct(pyAnswerTokens - dslAnswerTokens, pyAnswerTokens)}%`,
  );
  console.log("");
}
