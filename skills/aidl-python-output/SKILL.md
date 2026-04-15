---
name: aidl-python-output
description: Use when the user wants the model to receive ordinary Python tasks, Python snippets, or Python-oriented coding requests, but respond by writing AIDL directly for the Python backend. Enforce AIDL-first output, avoid drafting Python first, and prefer the compact AIDL macros and syntax already supported by this project.
---

# AIDL Python Output

Use this skill when the task is still conceptually about Python, but the model must output `AIDL` instead of Python source.

## Goal

Treat `AIDL` as the primary coding language.

This skill is a temporary integration layer for the prototype stage.

It exists so current coding clients can still accept ordinary Python-oriented tasks while forcing AIDL-first output. It is not the intended long-term form of the project.

The model should:

- read the user's original Python task, code, or intent
- internally map it into the current Python-targeting AIDL subset
- output `AIDL` directly

The model should not:

- draft Python and then "translate" it in the answer
- explain the equivalent Python unless the user explicitly asks
- fall back to Python syntax by habit

## Output Contract

- Default to outputting only `AIDL` code.
- Keep prose minimal unless the user explicitly asks for explanation.
- Prefer existing AIDL idioms over Python-shaped rewrites.
- Stay inside the current Python backend subset.

## Working Rules

1. Think in AIDL operators and macros first, not Python keywords.
2. Prefer AIDL structural forms such as `f`, `?`, `:`, `r`, `p`, `=` over Python spellings.
3. Prefer compression macros when they match the intent:
   `F`, `M`, `FM`, `S`, `A`, `E`, `SFM`, `CF`, `DFM`, `CO`, `KV`, `KVF`, `ANYN`, `ALLNN`, `CNTNN`.
4. Use `_` for the current item, and `_k` / `_v` for dict item transformations.
5. If the requested logic is outside the supported subset, either:
   - express the unsupported fragment with the narrowest possible `py ...` escape, or
   - say the construct is not yet covered by the current AIDL Python subset.
6. Do not generate unnecessary Python-style ceremony just because the source task was phrased in Python terms.

## Selection Heuristics

- Sequence filter: use `F(seq, cond)`
- Sequence map: use `M(seq, expr)`
- Filter then map: use `FM(seq, cond, expr)`
- Sum after filter-map: use `SFM(seq, cond, expr)`
- Count filtered items: use `CF(seq, cond)`
- Dict transform: use `KV(obj, key_expr, value_expr)`
- Dict filter-map: use `KVF(obj, key_expr, value_expr, cond)`
- Coalesce `None`: use `CO(value, fallback)`
- Multi-value `None` tests: use `ANYN`, `ALLNN`, `CNTNN`

## Syntax Reference

Read `../../src/aidsl/rules/python_aidl_rules.json` as the canonical rule source. Treat that JSON file as the single source of truth for the current Python-targeting AIDL subset.

## Temporary Status

- This skill-based path is temporary.
- In the long run, the model should ideally internalize AIDL directly rather than relying on a skill prompt plus external rules.
- The current structured rules file is useful in the prototype stage because it keeps the translator and the skill aligned.
- But if the rule set keeps growing, becomes more semantic, or starts carrying too much runtime and lowering knowledge, loading it through a skill or prompt may create token overhead that cancels out part of the compression benefit.
- At that point, the project should move away from "ship all rules in context" and toward more native AIDL modeling, learned priors, IR-level tooling, or compiler-side semantics.

## Quality Bar

- Optimize for lower token output, not human readability.
- Keep emitted AIDL compact but still valid for the current translator.
- Reuse the project's current stable subset instead of inventing new syntax inside the answer.
