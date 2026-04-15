import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { getEncoding, encodingForModel } from "js-tiktoken";

const root = resolve(process.cwd());

function read(relPath) {
  return readFileSync(resolve(root, relPath), "utf8");
}

function countTokens(text, target) {
  const encoder =
    target.kind === "model"
      ? encodingForModel(target.name)
      : getEncoding(target.name);
  const count = encoder.encode(text).length;
  return count;
}

function pct(saved, base) {
  if (!base) {
    return "0.00";
  }
  return ((saved / base) * 100).toFixed(2);
}

const task = read("benchmarks/task_prompt.txt").trim();
const pythonCode = read("benchmarks/small_task.py").trim();
const dslCode = read("benchmarks/small_task.aidl").trim();

const pythonAnswer = `Task:\n${task}\n\nUse Python.\n\n${pythonCode}`;
const dslAnswer = `Task:\n${task}\n\nUse the DSL.\n\n${dslCode}`;

const targets = [
  { kind: "encoding", name: "o200k_base" },
  { kind: "encoding", name: "cl100k_base" },
];

for (const target of targets) {
  const pyCodeTokens = countTokens(pythonCode, target);
  const dslCodeTokens = countTokens(dslCode, target);
  const pyAnswerTokens = countTokens(pythonAnswer, target);
  const dslAnswerTokens = countTokens(dslAnswer, target);

  console.log(`== ${target.name} ==`);
  console.log(`python_code_tokens: ${pyCodeTokens}`);
  console.log(`dsl_code_tokens: ${dslCodeTokens}`);
  console.log(`code_tokens_saved: ${pyCodeTokens - dslCodeTokens}`);
  console.log(`code_saving_percent: ${pct(pyCodeTokens - dslCodeTokens, pyCodeTokens)}%`);
  console.log(`python_answer_tokens: ${pyAnswerTokens}`);
  console.log(`dsl_answer_tokens: ${dslAnswerTokens}`);
  console.log(`answer_tokens_saved: ${pyAnswerTokens - dslAnswerTokens}`);
  console.log(
    `answer_saving_percent: ${pct(pyAnswerTokens - dslAnswerTokens, pyAnswerTokens)}%`
  );
  console.log("");
}
