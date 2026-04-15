# Python Pattern Mining For AI-DSL

This note focuses on Python code shapes that are common in real projects and look promising for token-oriented compression in AI-DSL.

## Source sample

I inspected representative files from several widely used Python projects:

- FastAPI: `fastapi/encoders.py`
  <https://github.com/fastapi/fastapi/blob/master/fastapi/encoders.py>
- Requests: `src/requests/utils.py`
  <https://github.com/psf/requests/blob/main/src/requests/utils.py>
- Requests: `src/requests/models.py`
  <https://github.com/psf/requests/blob/main/src/requests/models.py>
- pandas: `pandas/core/common.py`
  <https://github.com/pandas-dev/pandas/blob/main/pandas/core/common.py>
- Transformers: `src/transformers/utils/generic.py`
  <https://github.com/huggingface/transformers/blob/main/src/transformers/utils/generic.py>

The goal here is not statistical exactness. The goal is to identify repeated structural templates that are worth turning into short, stable DSL forms.

## Observed high-frequency shapes

### 1. Dict item map / filter-map

This pattern appears frequently when code recursively normalizes, serializes, filters, or adapts dictionaries.

Representative examples from the sampled repos:

- FastAPI recursively encodes dict keys and values in `jsonable_encoder`.
- Transformers converts nested dict values in `to_py_obj` and `to_numpy`.
- Requests parses or rebuilds dict-like structures in several helpers.

Typical Python forms:

```python
{k: to_py_obj(v) for k, v in obj.items()}
{k: v for k, v in obj.items() if v is not None}
```

AI-DSL candidates:

```text
KV(obj,_k,to_py_obj(_v))
KVF(obj,_k,_v,_v is not None)
```

Suggested lowering:

```python
{k: to_py_obj(v) for k, v in obj.items()}
{k: v for k, v in obj.items() if v is not None}
```

Why this matters:

- long Python boilerplate
- appears in framework glue code, serialization, validation, config handling
- maps cleanly to deterministic translation

### 2. None-coalescing defaults

This is extremely common in constructors, option normalization, and helper functions.

Representative examples:

- `custom_encoder = custom_encoder or {}` in FastAPI
- `hooks = {} if hooks is None else hooks` and similar forms in Requests
- repeated config fallback logic in Transformers

Typical Python forms:

```python
hooks = hooks if hooks is not None else {}
value = kwargs.get(name) if kwargs.get(name) is not None else default
```

AI-DSL candidate:

```text
CO(value,fallback)
```

Suggested lowering:

```python
(value if value is not None else fallback)
```

Why this matters:

- appears everywhere in option-heavy Python
- `None` semantics are safer than generic `or`
- easy to compose inside assignments, returns, and larger expressions

### 3. Any/all/count checks over predicates

This pattern was already visible in earlier local analysis, and it also shows up repeatedly in utility-heavy libraries.

Typical Python forms:

```python
any(x is None for x in args)
all(arg is not None for arg in args)
sum(1 for x in nums if x > 10)
```

Current AI-DSL support:

```text
A(seq,cond)
E(seq,cond)
CF(seq,cond)
```

This remains a high-priority family because it is common in validation and shape checking code.

Related sub-family seen clearly in `pandas.core.common.py`:

```python
any(arg is None for arg in args)
all(arg is not None for arg in args)
sum(x is not None for x in args)
```

These suggest a short variadic None-check family:

```text
ANYN(a,b,c)
ALLNN(a,b,c)
CNTNN(a,b,c)
```

These are attractive because:

- they avoid forcing the model to spell out generator boilerplate
- they appear in utility and validation code
- they keep semantics explicit and deterministic

### 4. Recursive normalization over nested structures

This appears strongly in FastAPI and Transformers.

Typical Python forms:

```python
if isinstance(obj, dict):
    return {k: f(v) for k, v in obj.items()}
elif isinstance(obj, (list, tuple)):
    return [f(x) for x in obj]
else:
    return obj
```

This suggests a larger future direction:

- not just expression macros
- but type-dispatch or shape-dispatch constructs

Possible future AI-DSL direction:

```text
match obj
  dict -> KV(obj,_k,FN(_v))
  list -> M(obj,FN(_))
  else -> obj
```

I am not implementing this yet because it requires a more explicit syntax and semantics layer.

### 5. Try-fallback conversion chains

Observed in FastAPI and Requests:

```python
try:
    data = dict(obj)
except Exception:
    data = vars(obj)
```

This is common in Python interoperability code, but it is also semantically heavier than the current macro family.

Possible future direction:

```text
TRY(dict(obj), vars(obj))
```

Suggested lowering:

```python
try:
    __tmp = dict(obj)
except Exception:
    __tmp = vars(obj)
```

I would keep this lower priority for now because:

- hidden control flow makes debugging harder
- exception scope matters
- it needs careful semantics around caught exception types

### 6. Context-managed temporary mutation

Observed in Requests and pandas:

```python
old_value = getattr(obj, attr)
setattr(obj, attr, value)
try:
    yield obj
finally:
    setattr(obj, attr, old_value)
```

This is common enough to matter eventually, but it is more like a statement/runtime abstraction than a pure expression macro.

Possible future direction:

- `TEMPSET(obj, attr, value)`
- `WITHENV(name, value)`

This belongs to a later phase after the Python translator has a stronger statement model.

## Priority recommendation

Based on both observed project code and token-compression feasibility, the next Python-first priorities should be:

1. `KV` and `KVF`
2. `CO`
3. variadic None-check helpers such as `ANYN / ALLNN / CNTNN`
4. more dict/list normalization helpers built on top of the same placeholder model
5. only after that, consider higher-level control-flow abstractions such as `TRY` or structural `match`

## Translation rules worth keeping

The current design principle that seems most defensible is:

- prefer short macros for repeated structural boilerplate
- keep translation deterministic and syntax-directed
- avoid macros that hide too much control flow too early

That means these are good near-term candidates:

```text
CO(x,y) -> (x if x is not None else y)
KV(d,k,v) -> {k_expr: v_expr for k, v in d.items()}
KVF(d,k,v,c) -> {k_expr: v_expr for k, v in d.items() if cond_expr}
ANYN(a,b,c) -> any(it is None for it in (a, b, c))
ALLNN(a,b,c) -> all(it is not None for it in (a, b, c))
CNTNN(a,b,c) -> sum(1 for it in (a, b, c) if it is not None)
```

And these should stay in the backlog for now:

- exception-driven fallback macros
- contextmanager macros
- recursive shape-dispatch syntax

## Current conclusion

Looking at real open-source Python code reinforces the same conclusion as the earlier local token studies:

- shrinking keywords is not the main win
- compressing repeated structural templates is the main win

The most immediately useful next step for AI-DSL is therefore not “more Python-lite abbreviations”, but a denser vocabulary for:

- dict normalization
- option/default handling
- validation predicates
- recursive object-to-object transformations
