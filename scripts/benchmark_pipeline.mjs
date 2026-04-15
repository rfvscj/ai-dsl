import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { getEncoding } from "js-tiktoken";

const root = resolve(process.cwd());

function read(relPath) {
  return readFileSync(resolve(root, relPath), "utf8").trim();
}

function countTokens(text, encodingName) {
  const encoder = getEncoding(encodingName);
  return encoder.encode(text).length;
}

function render(template, values) {
  return template.replace(/\{\{(\w+)\}\}/g, (_, key) => values[key] ?? "");
}

function compileDsl(relPath) {
  try {
    return execFileSync(
      "python3",
      ["-m", "src.aidsl.cli", "compile", relPath],
      { cwd: root, encoding: "utf8" }
    ).trim();
  } catch {
    return execFileSync(
      "wsl",
      [
        "bash",
        "-lc",
        `cd /mnt/c/Users/renzhc/workspace/ai-dsl-prototype && python3 -m src.aidsl.cli compile ${relPath}`,
      ],
      { cwd: root, encoding: "utf8" }
    ).trim();
  }
}

const task = read("benchmarks/task_prompt.txt");
const executionPrompt = read("benchmarks/execution_prompt.txt");
const pythonCode = read("benchmarks/small_task.py");
const dslCode = read("benchmarks/small_task.aidl");
const compiledDslPython = compileDsl("benchmarks/small_task.aidl");

const generationPythonPrompt =
  "Write code for the following task. Output Python only.\n\n{{task}}";
const generationDslPrompt =
  "Write code for the following task. Output DSL only.\n\n{{task}}";
const executionPromptTemplate =
  "{{instruction}}\n\n```{{lang}}\n{{code}}\n```";

const scenarios = [
  {
    name: "python",
    generationPrompt: render(generationPythonPrompt, { task }),
    generationOutput: pythonCode,
    executionInput: render(executionPromptTemplate, {
      instruction: executionPrompt,
      lang: "python",
      code: pythonCode,
    }),
  },
  {
    name: "dsl",
    generationPrompt: render(generationDslPrompt, { task }),
    generationOutput: dslCode,
    executionInput: render(executionPromptTemplate, {
      instruction: executionPrompt,
      lang: "text",
      code: dslCode,
    }),
  },
  {
    name: "dsl_compiled_backend",
    generationPrompt: render(generationDslPrompt, { task }),
    generationOutput: dslCode,
    executionInput: render(executionPromptTemplate, {
      instruction: executionPrompt,
      lang: "python",
      code: compiledDslPython,
    }),
  },
];

for (const encodingName of ["o200k_base", "cl100k_base"]) {
  console.log(`== ${encodingName} ==`);
  for (const scenario of scenarios) {
    const genIn = countTokens(scenario.generationPrompt, encodingName);
    const genOut = countTokens(scenario.generationOutput, encodingName);
    const execIn = countTokens(scenario.executionInput, encodingName);
    console.log(`[${scenario.name}]`);
    console.log(`generation_input_tokens: ${genIn}`);
    console.log(`generation_output_tokens: ${genOut}`);
    console.log(`generation_total_tokens: ${genIn + genOut}`);
    console.log(`execution_input_tokens: ${execIn}`);
    console.log("");
  }
}
