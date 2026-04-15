# Python Compression Analysis

This note focuses on one concrete near-term goal:

- make the Python backend materially better
- identify Python patterns that repeatedly cost extra tokens
- only add DSL syntax when it wins on real token counts

## Working rule

Do not trust character count alone.

Every candidate syntax should be judged by real tokenizer counts first, then by implementation cost, then by readability/debuggability.

## High-frequency Python patterns worth compressing

The first batch to analyze:

1. filter + map + reduce
2. dict comprehension
3. count-if patterns
4. join + map
5. append loops that are really list transforms

These patterns appear often enough in AI-generated Python that even a small token win compounds across generation and iterative repair.

## Current hypothesis

The next useful syntax additions are likely to be:

1. `SFM(seq, cond, expr)`
   Collapse `sum(FM(...))` into one macro.
2. `DFM(seq, key, value, cond)`
   Compress dict-comprehension with optional filtering.
3. `CF(seq, cond)`
   Compress `len(F(...))` count-if patterns.
4. `J(seq, sep, expr)`
   Compress join-map string assembly.

These candidates are worth testing because they remove repeated structural scaffolding rather than only renaming Python keywords.

## Expected direction

The Python-first roadmap should be:

1. benchmark common patterns
2. keep only syntax that consistently saves tokens
3. implement the winners in the Python compiler
4. re-run pipeline-level measurements

## Tooling

Use:

- `scripts/analyze_patterns.mjs`
- `benchmarks/pattern_candidates.json`

to compare Python against current DSL and candidate lower-token syntax forms.
