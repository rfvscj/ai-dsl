# LLM Serving Pattern Mining For AI-DSL

This note focuses on Python code shapes that appear frequently in LLM-serving-oriented projects and that may deserve dedicated AI-DSL support.

## Source sample

I inspected representative utility and config files from these repositories:

- Transformers: `src/transformers/utils/generic.py`
  <https://github.com/huggingface/transformers/blob/main/src/transformers/utils/generic.py>
- vLLM: `vllm/config/kernel.py`
  <https://github.com/vllm-project/vllm/blob/main/vllm/config/kernel.py>
- SGLang: `python/sglang/utils.py`
  <https://github.com/sgl-project/sglang/blob/main/python/sglang/utils.py>
- SGLang: `python/sglang/srt/lora/lora_registry.py`
  <https://github.com/sgl-project/sglang/blob/main/python/sglang/srt/lora/lora_registry.py>

The focus is not model math kernels. It is the Python glue around configuration, normalization, dispatch, and orchestration, because that is where AI-generated Python often becomes verbose.

## High-frequency shapes

### 1. String-to-list normalization

Seen clearly in vLLM config validation:

```python
if isinstance(value, str):
    value = value.replace(" ", "").split(",")
```

This pattern is common in CLI, env var, config, and backend selection code.

Candidate DSL:

```text
CSV(value)
```

Suggested lowering:

```python
value.replace(" ", "").split(",")
```

Why it matters:

- common in config-heavy infra code
- deterministic
- compresses a surprisingly verbose normalize step

### 2. Unique append / merge-with-dedup

Seen in vLLM platform-default merging:

```python
unique_op_priority = [op for op in op_priority if op not in current_op_priority]
current_op_priority.extend(unique_op_priority)
```

Candidate DSL:

```text
UEXT(base, incoming)
```

Suggested lowering:

```python
base.extend([it for it in incoming if it not in base])
```

This is useful for:

- merging feature lists
- backend priority lists
- plugin/provider capability sets represented as ordered lists

I would treat this as a statement-level helper or runtime helper, not just an expression macro.

### 3. Type-dispatch normalization

Seen repeatedly in SGLang and Transformers:

```python
if isinstance(json_schema, dict):
    ...
elif isinstance(json_schema, str):
    ...
elif issubclass(json_schema, BaseModel):
    ...
else:
    raise ValueError(...)
```

Also visible in SGLang object dispatch and Transformers conversion helpers.

This is a strong signal that AI-DSL eventually wants a compact type-dispatch form.

Candidate DSL:

```text
tcase json_schema
  dict -> json.dumps(json_schema)
  str -> json_schema
  BaseModel -> json.dumps(json_schema.model_json_schema())
  else -> err("invalid schema")
```

This is not implemented yet. It is more than a macro. It needs:

- explicit branch syntax
- clear dispatch order
- deterministic lowering to `if/elif/else`

### 4. Dict normalization from mixed spec formats

Seen in SGLang overlay-registry loading:

```python
normalized = {}
for source_model_id, spec in payload.items():
    if isinstance(spec, str):
        normalized[source_model_id] = {"overlay_repo_id": spec}
    elif isinstance(spec, dict) and spec.get("overlay_repo_id"):
        normalized[source_model_id] = dict(spec)
```

This is a recurring infra pattern:

- accept permissive user input
- normalize to one internal format

Candidate DSL:

```text
NKV(payload)
  str -> {"overlay_repo_id": _v}
  dict if _v.get("overlay_repo_id") -> dict(_v)
```

This again suggests a higher-level dict-dispatch construct, not just a tiny macro.

### 5. Optional scalar-or-list handling

Seen in SGLang LoRA registry:

```python
if isinstance(lora_name, str):
    ...
elif isinstance(lora_name, list):
    ...
else:
    raise TypeError(...)
```

And similarly in many serving APIs where one parameter can be:

- a single item
- a batch/list of items

Candidate DSL:

```text
onelist lora_name
  one -> ...
  many -> ...
```

Possible lowering:

- `str` / scalar branch
- `list` branch
- error branch

This is promising because AI-generated orchestration code often needs exactly this pattern.

### 6. Async gather over filtered list

Seen in SGLang:

```python
await asyncio.gather(
    *[
        self._counters[id].increment(notify_all=False)
        for id in lora_ids
        if id is not None
    ]
)
```

Candidate DSL:

```text
AG(ids,_ is not None,self._counters[_].increment(notify_all=False))
```

Suggested lowering:

```python
await asyncio.gather(*[
    expr for it in ids if cond
])
```

This is interesting because:

- it appears in async orchestration code
- it is structurally repetitive
- it is verbose in Python

But it should probably wait until AI-DSL has explicit async semantics.

### 7. Poll-until-ready loops

Seen in SGLang readiness helpers:

```python
while True:
    ...
    try:
        response = requests.get(...)
        if response.status_code == 200:
            return
    except requests.exceptions.RequestException:
        ...
    if timeout:
        raise TimeoutError(...)
    time.sleep(1)
```

This is a classic serving/runtime pattern.

Candidate DSL:

```text
wait_http url
  ok 200 -> return
  timeout -> err("not ready")
  sleep 1
```

This is not a Python compression macro. It is an AI-runtime primitive candidate.

### 8. Type-based dispatcher registry

Seen in SGLang `TypeBasedDispatcher` and also conceptually in Transformers conversion helpers.

Typical Python form:

```python
fn = mapping.get(type(obj))
if fn is not None:
    return fn(obj)
for ty, fn in mapping.items():
    if isinstance(obj, ty):
        return fn(obj)
if fallback is not None:
    return fallback(obj)
raise ValueError(...)
```

Candidate DSL:

```text
dispatch obj mapping fallback
```

or a more explicit syntax:

```text
dispatch obj
  exact mapping
  isa ty -> fn(obj)
  else -> fallback(obj)
```

Again, this is more like a medium-term structural feature.

## What seems worth doing now

The best near-term candidates are still the ones that:

- appear repeatedly in infra code
- are easy to lower
- are easy for AI to learn

That gives this short list:

1. `CSV(x)` for config string normalization
2. `ANYN / ALLNN / CNTNN` which are already good fits for validation-heavy code
3. `KV / KVF / CO` which already match many normalization patterns

## What seems worth designing, but not implementing yet

These patterns are clearly real, but they need more than expression macros:

1. `tcase` for type-dispatch normalization
2. `onelist` for scalar-or-list handling
3. async gather/filter helpers
4. wait/poll runtime primitives
5. registry/dispatcher abstractions

## Design implication

Looking specifically at Transformers, vLLM, and SGLang strengthens a more precise view of AI-DSL:

- for ordinary Python utility code, expression macros are enough for the first wave
- for serving/orchestration systems, the next wave should not just be “shorter Python”
- it should move toward compact structural forms for:
  - normalization
  - dispatch
  - async fanout
  - readiness waiting
  - registry operations

So the language roadmap should probably split into two layers:

1. **Python compression layer**
   small deterministic macros like `FM`, `KVF`, `CO`, `CNTNN`
2. **Serving/runtime layer**
   structured constructs like `tcase`, `onelist`, `dispatch`, `wait_http`, `agather`

That separation keeps the current translator simple while still giving a clear path toward a more AI-native system language.
