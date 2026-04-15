# AI-DSL

[中文](README.md)

A toy prototype for an AI-first, lower-token programming intermediate representation.

The core idea is to shift AI coding from "generate human-facing source code directly" to "generate AI-DSL first, then translate it locally into a target language or executable form."

`AI-DSL` is not primarily meant for humans to write. It is meant to be a compact coding IR for AI generation and machine-side processing.

## Positioning

This is a toy project.

It is my idea plus an early prototype, not a finished language and not a rigorously validated system. Stronger contributors are very welcome to take the idea much further.

The current prototype is meant to test three questions:

- Can AIDL reduce token cost during code generation?
- Can it translate reliably into Python while reusing the existing ecosystem?
- Can it later grow toward multiple backends and eventually a binary path?

## Core Idea

Mainstream programming languages were designed for humans, not for tokenizers.

If code is increasingly generated, revised, exchanged, and executed through AI systems, then the surface representation does not necessarily need to stay human-first. The goals of AI-DSL are:

- lower token cost during code generation
- lower code exchange cost between AI systems and execution environments
- preserve compatibility with existing software stacks

In the longer term, `AI-DSL -> binary -> run` is also one of the intended directions. The end state could be a toolchain centered around AI-DSL itself.

## Current Implementation

The repository currently includes:

- an indentation-sensitive AIDL syntax
- an `AIDL -> Python` translator
- an early `AIDL -> C++` compiler backend
- a local interpretation path
- compression macros that already show token savings
- benchmark scripts using OpenAI-compatible token encodings
- tutorial, analysis notes, and a paper draft

The stable path today is still Python-first:

1. `ai-dsl -> python -> interpreter -> run`
2. `ai-dsl -> c++ -> compiler -> run`
3. `ai-dsl -> binary -> run` (future target)

## Python-First Work

The first milestone is to make `AI-DSL -> Python` strong.

The currently supported compression macros include:

- `F / M / FM`
- `S / A / E`
- `SFM / CF / DFM`
- `CO`
- `KV / KVF`
- `ANYN / ALLNN / CNTNN`

These are intended to compress high-frequency Python patterns such as:

- filter + map
- sum over filter-map
- count-if
- dict comprehensions
- `None` coalescing and presence checks

## Structured Rules

The current Python-facing AIDL subset is defined in:

- `src/aidsl/rules/python_aidl_rules.json`

The translator reads from this structured rules file, and the prototype skill points to the same source of truth.

This is a prototype-stage strategy, not the final architecture.

If the ruleset grows too large, too semantic, or too tied to lowering/runtime behavior, shipping the full rules through prompts or skills may create token overhead and eventually reduce the net benefit. The long-term goal is still for models to internalize AIDL directly.

## Skill Is Temporary

There is also a local prototype skill:

- `skills/aidl-python-output/`

Its purpose is only to force AIDL-first output while current clients still accept Python-oriented tasks as input. It should be seen as a temporary integration layer, not the desired end state.

## Quick Start

```bash
cd C:\Users\renzhc\workspace\ai-dsl-prototype
python -m venv .venv
.venv\Scripts\activate
pip install -e .
```

Translate:

```bash
aidsl translate examples\fib.aidl
```

Run:

```bash
aidsl run examples\fib.aidl
```

Compile to C++:

```bash
aidsl compile benchmarks\small_task.aidl --target cpp
```

## Example

```text
f even_square_sum(nums)
  = squares FM(nums,_%2==0,_*_)
  r S(squares)

= data [1, 2, 3, 4, 5, 6]
= result even_square_sum(data)
p result
```

Translated Python:

```python
def even_square_sum(nums):
    squares = [it * it for it in nums if it % 2 == 0]
    return sum(squares)

data = [1, 2, 3, 4, 5, 6]
result = even_square_sum(data)
print(result)
```

## Benchmarks

Available scripts:

- `scripts/compare_tokens.mjs`
- `scripts/benchmark_pipeline.mjs`
- `scripts/report_statement_savings.mjs`
- `scripts/analyze_patterns.mjs`

Run:

```bash
npm install
node scripts/compare_tokens.mjs
node scripts/benchmark_pipeline.mjs
node scripts/report_statement_savings.mjs
```

## Documentation

- `docs/tutorial_zh.md`
- `docs/paper_draft_zh.md`
- `docs/python_compression_analysis.md`
- `docs/python_pattern_mining.md`
- `docs/llm_serving_pattern_mining.md`
- `docs/statement_token_savings.md`

## Repository Layout

- `src/aidsl/frontend.py`: frontend and shared utilities
- `src/aidsl/python_translator.py`: Python translator
- `src/aidsl/cpp_translator.py`: C++ compiler prototype
- `src/aidsl/compiler.py`: backend dispatch
- `src/aidsl/rules/`: structured rules
- `skills/aidl-python-output/`: prototype skill
- `examples/`: examples
- `benchmarks/`: benchmarks and tasks
- `docs/`: tutorial, analysis, paper draft

## Vision

The more radical direction is not just "a shorter Python-like DSL."

It may eventually become a language form that is more native to AI exchange itself: built on denser language material, stripped of low-value modifiers, and restored on-device through a fast translator into host languages or human-readable text.

My current intuition is:

- lossless encoding
- lossy decoding

AI-facing exchange stays compact and stable; human-facing recovery can expand, restate, and reshape as long as the semantics are preserved.

## Co-Build

If this direction seems worthwhile, contributions are welcome, especially from people with stronger backgrounds in:

- compilers and programming languages
- program analysis
- LLM systems
- tokenization, compression, and training data design

What I am doing right now is mainly to pin down the idea and a runnable prototype. A stronger system will need stronger people to continue it.
