# AI-DSL 教程

这份教程只讲当前原型已经支持、而且相对稳定的部分。它不是语言规范书，而是“怎么快速写、怎么翻译、怎么跑、怎么继续扩”的上手文档。

## 1. 这个语言要解决什么问题

AI-DSL 不是主要给人长期手写维护的语言。

它的目标是：

- 让 AI 在生成代码时用更短的表示
- 在 AI 和本地运行环境之间传递更紧凑的代码
- 先通过 `AI-DSL -> Python` 验证真实 token 节省

当前阶段，你应该把它理解成：

- 一个面向 AI 的低 token 表层表示
- 一个能稳定翻译到 Python 的 toy 级原型

## 2. 最基本的工作流

### 安装

```bash
cd C:\Users\renzhc\workspace\ai-dsl-prototype
python -m venv .venv
.venv\Scripts\activate
pip install -e .
```

### 翻译成 Python

```bash
aidsl translate examples\fib.aidl
```

### 直接运行

```bash
aidsl run examples\fib.aidl
```

### 看简单统计

```bash
aidsl stats examples\fib.aidl
```

## 3. 语句层语法

当前语句层只有少量缩写，重点不是“花哨”，而是把高频样板压短。

### 函数定义

```text
f add(x, y)
  r x + y
```

会翻译成：

```python
def add(x, y):
    return x + y
```

### 条件分支

```text
? x > 0
  p x
:
  p 0
```

会翻译成：

```python
if x > 0:
    print(x)
else:
    print(0)
```

### 赋值、返回、打印

```text
= total 0
r total
p total
```

分别对应：

```python
total = 0
return total
print(total)
```

### 原样嵌入 Python 表达式

```text
py value.append(x)
```

这在原型阶段很有用。遇到 DSL 还没覆盖的表达式时，可以临时退回 Python。

## 4. 占位符规则

表达式宏里当前主要有三个占位符：

- `_`：序列里的当前元素
- `_k`：字典项里的 key
- `_v`：字典项里的 value

例如：

```text
FM(nums,_%2==0,_*_)
KV(obj,_k,to_py_obj(_v))
KVF(obj,_k,_v,_v is not None)
```

## 5. 当前可用宏

### 列表与聚合

#### `F(seq, cond)`

```text
= evens F(nums,_%2==0)
```

```python
evens = [it for it in nums if it % 2 == 0]
```

#### `M(seq, expr)`

```text
= squares M(nums,_*_)
```

```python
squares = [it * it for it in nums]
```

#### `FM(seq, cond, expr)`

```text
= squares FM(nums,_%2==0,_*_)
```

```python
squares = [it * it for it in nums if it % 2 == 0]
```

#### `S(seq)`

```text
= total S(values)
```

```python
total = sum(values)
```

#### `A(seq, cond)`

```text
= ok A(nums,_>0)
```

```python
ok = any(it > 0 for it in nums)
```

#### `E(seq, cond)`

```text
= ok E(nums,_>0)
```

```python
ok = all(it > 0 for it in nums)
```

#### `SFM(seq, cond, expr)`

```text
= total SFM(nums,_>0,_*_)
```

```python
total = sum(it * it for it in nums if it > 0)
```

#### `CF(seq, cond)`

```text
= count CF(nums,_>10)
```

```python
count = sum(1 for it in nums if it > 10)
```

#### `DFM(seq, key_expr, value_expr, cond)`

```text
= mapping DFM(nums,_,_*_,_>0)
```

```python
mapping = {it: it * it for it in nums if it > 0}
```

### 默认值与字典变换

#### `CO(value, fallback)`

```text
= hooks CO(hooks,{})
```

```python
hooks = (hooks if hooks is not None else {})
```

#### `KV(obj, key_expr, value_expr)`

```text
= mapped KV(obj,_k,to_py_obj(_v))
```

```python
mapped = {k: to_py_obj(v) for k, v in obj.items()}
```

#### `KVF(obj, key_expr, value_expr, cond)`

```text
= filtered KVF(obj,_k,_v,_v is not None)
```

```python
filtered = {k: v for k, v in obj.items() if v is not None}
```

### 多参数 None 检查

#### `ANYN(a,b,c,...)`

```text
= has_none ANYN(a,b,c)
```

```python
has_none = any(it is None for it in (a, b, c,))
```

#### `ALLNN(a,b,c,...)`

```text
= all_present ALLNN(a,b,c)
```

```python
all_present = all(it is not None for it in (a, b, c,))
```

#### `CNTNN(a,b,c,...)`

```text
= present CNTNN(a,b,c)
```

```python
present = sum(1 for it in (a, b, c,) if it is not None)
```

## 6. 一个完整小例子

```text
f build_report(nums)
  = even_squares FM(nums,_%2==0,_*_)
  = positive_sum SFM(nums,_>0,_*_)
  = count_positive CF(nums,_>0)
  r {
    "even_squares": even_squares,
    "positive_sum": positive_sum,
    "count_positive": count_positive,
  }

= data [-3, 0, 2, 5, 8]
= report build_report(data)
p report
```

## 7. 怎么判断一个新语法值不值得加

当前最实用的标准就三条：

1. 在真实 Python 项目里反复出现
2. 翻译规则足够确定，不靠猜
3. 在真实 tokenizer 下真的省 token

如果只是字符更短，但 token 基本不变，就不值得加。

## 8. 当前不适合太早做的东西

下面这些方向很重要，但不适合现在就匆忙并进翻译器：

- `try/except` 驱动的 fallback 宏
- `with` / contextmanager 宏
- 递归 shape-dispatch 语法
- 复杂模式匹配

原因也很简单：它们会明显增加控制流复杂度、错误定位难度和调试成本。

## 9. 推荐的扩展路线

如果你接下来要继续扩语言，我建议按这个顺序：

1. 继续做 dict/list 规范化相关宏
2. 继续做参数校验 / 默认值 / 条件过滤相关宏
3. 再考虑结构化控制流抽象
4. 最后才考虑更像独立语言的语义层

## 10. 配套文档

当前可以一起看的几份文档：

- `docs/python_compression_analysis.md`
- `docs/python_pattern_mining.md`
- `docs/statement_token_savings.md`
- `docs/paper_draft_zh.md`

如果你要把这个项目继续往前推，这几份文档应该一起维护，而不是只改代码不更新语言说明。
