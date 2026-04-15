# TokenLite / 面向 AI 的低 Token Python 风格 DSL 原型

[中文](#中文说明) | [English](#english)

## 中文说明

这是我的一个想法：做一个更适合 AI 生成、阅读和传递的 Python 风格 DSL。

核心目标不是提升人类可读性，而是尽量压缩代码在 tokenizer 下的 token 成本。当前原型采用这条路径：

- 让 AI 输出更短的 DSL
- 在本地把 DSL 编译成 Python
- 继续复用 Python 运行时和生态

### 当前状态

这是一个早期原型，不是成熟语言，也不是完整论文实现。

目前已经有：

- 缩进敏感的 DSL 语法
- `DSL -> Python` 编译器
- `DSL -> C++` 编译器雏形
- 一组表达式级压缩宏，例如 `F / M / FM / S / A / E`
- 用 OpenAI 兼容 tokenizer 做 token 对比的 benchmark 脚本

### 当前后端路线

目前项目已经明确朝多后端走：

1. `ai-dsl -> python -> 解释器 -> 运行`
2. `ai-dsl -> c++ -> 编译 -> 运行`
3. `ai-dsl -> 二进制 -> 运行`（未来目标，当前未实现）

这样设计不是为了单纯支持更多目标，而是分别对应不同需求：

- 支持多种语言后端
  是为了更容易接入不同语言编写的现有项目和工程体系。例如有的项目主干是 Python，有的项目主干是 C++，未来也可能是 Rust、Go 或其他语言。
- 支持独立二进制路径
  是为了在某些场景下绕开解释器或宿主语言运行时，争取更高的执行效率、更简单的部署方式，以及更可控的产物形态。

目前真正可稳定使用的是 Python 后端。

C++ 后端目前是雏形，目标是证明“同一份 DSL 可以落到不同语言后端”这件事是可行的。它现在主要支持：

- 函数定义
- 赋值
- `if / else`
- `return`
- `print`
- `len`
- `F / M / FM / S / A / E` 这些宏
- 数字列表和字符串列表这类基础容器

暂时还不完整，尤其对 Python 专属表达式支持有限，例如：

- f-string
- Python 列表推导原语
- `range(...)`
- 更复杂的动态类型行为

### 这个仓库想表达什么

我想验证一件事：

**如果代码主要是给 AI 和机器之间交换，而不是给人长期维护，那么是否应该设计一种比 Python 更适合 tokenizer 的表示？**

现在的实验结果说明，单纯缩写 Python 关键字收益很有限；但如果压缩高频结构模式，例如 filter、map、filter+map、sum，这个方向是有实际 token 收益的。

### 我自己的说明

这是我的个人想法和原型实现。我的知识水平有限，这个项目也还很粗糙，很多地方都不完整。

如果你觉得这个方向有价值，欢迎继续发扬光大：

- 补更系统的语言设计
- 做更严谨的编译器
- 建更大的 benchmark
- 做英文论文、正式实验和可复现实证
- 把它推进成真正的 AI-first programming interface

如果未来有人把这个方向做得更扎实、更系统，我会很高兴。

### 快速开始

```bash
cd C:\Users\renzhc\workspace\ai-dsl-prototype
python -m venv .venv
.venv\Scripts\activate
pip install -e .
aidsl compile examples\fib.aidl
aidsl run examples\fib.aidl
aidsl compile benchmarks\small_task.aidl --target cpp
```

### 语法示例

```text
f even_square_sum(nums)
  = squares FM(nums,_%2==0,_*_)
  r S(squares)

= data [1, 2, 3, 4, 5, 6]
= result even_square_sum(data)
p result
```

会编译成：

```python
def even_square_sum(nums):
    squares = [it * it for it in nums if it % 2 == 0]
    return sum(squares)

data = [1, 2, 3, 4, 5, 6]
result = even_square_sum(data)
print(result)
```

### Token Benchmark

项目里提供了两类 benchmark：

- `scripts/compare_tokens.mjs`
  对比 Python 和 DSL 的代码 token / 回答 token
- `scripts/benchmark_pipeline.mjs`
  对比生成链路和执行链路的 token

运行：

```bash
npm install
node scripts/compare_tokens.mjs
node scripts/benchmark_pipeline.mjs
```

### 项目结构

- `src/aidsl/compiler.py`: Python / C++ 双后端编译器
- `src/aidsl/cli.py`: CLI
- `examples/`: 示例
- `benchmarks/`: token benchmark
- `docs/paper_draft_zh.md`: 中文论文草稿

## English

This repository is an early prototype for a simple idea:

**what if code meant primarily for AI-to-machine exchange should use a representation that is more token-efficient than plain Python?**

The goal is not better readability for humans. The goal is to reduce token cost when code is generated, transmitted, and interpreted by language models.

The current approach is:

- let the model emit a shorter DSL
- compile the DSL locally into Python
- keep using the Python runtime and ecosystem

### Current status

This is an early-stage prototype, not a finished language.

What is already here:

- an indentation-sensitive DSL
- a `DSL -> Python` compiler
- an early `DSL -> C++` compiler
- expression-level compression macros such as `F / M / FM / S / A / E`
- benchmark scripts using OpenAI-compatible token encodings

### Backend roadmap

The project is now explicitly moving toward multiple backend paths:

1. `ai-dsl -> python -> interpreter -> run`
2. `ai-dsl -> c++ -> compiler -> run`
3. `ai-dsl -> binary -> run` (future target, not implemented yet)

This is not just about supporting more targets for its own sake. Each path serves a different practical purpose:

- Multiple language backends
  make it easier to integrate the DSL into projects that are already built around different host languages. Some codebases are Python-first, some are C++-first, and future targets may include Rust, Go, or others.
- A direct binary path
  is meant for cases where the DSL should run without going through an interpreter or a host-language runtime first, with the goal of improving execution efficiency, deployment simplicity, and output control.

Right now, the Python backend is the stable path.

The C++ backend is intentionally incomplete. Its current role is to prove that one DSL can target more than one execution language. For now it mainly supports:

- function definitions
- assignments
- `if / else`
- `return`
- `print`
- `len`
- `F / M / FM / S / A / E` macros
- basic numeric and string list literals

It does not yet cover many Python-specific constructs, including:

- f-strings
- Python list-comprehension syntax
- `range(...)`
- more dynamic typing behavior

### What this repo is trying to show

The main question behind this project is:

**if code is mostly exchanged between AI systems and execution environments, should we still optimize the surface language for humans first?**

The current result is narrow but useful:

- keyword shortening alone does not help much
- compressing high-frequency structural patterns can produce real token savings

### Personal note

This is my own idea and prototype. My background is limited, and the implementation is still rough.

If you find this direction interesting, I sincerely hope others can take it further:

- build a cleaner language design
- implement a more rigorous compiler
- create larger benchmarks
- write a stronger paper with broader experiments
- push it toward a real AI-first programming interface

If someone improves this idea substantially, I would be happy to see it happen.

### Quick start

```bash
cd C:\Users\renzhc\workspace\ai-dsl-prototype
python -m venv .venv
.venv\Scripts\activate
pip install -e .
aidsl compile examples\fib.aidl
aidsl run examples\fib.aidl
aidsl compile benchmarks\small_task.aidl --target cpp
```

### Example

```text
f even_square_sum(nums)
  = squares FM(nums,_%2==0,_*_)
  r S(squares)

= data [1, 2, 3, 4, 5, 6]
= result even_square_sum(data)
p result
```

Compiles to:

```python
def even_square_sum(nums):
    squares = [it * it for it in nums if it % 2 == 0]
    return sum(squares)

data = [1, 2, 3, 4, 5, 6]
result = even_square_sum(data)
print(result)
```

### Token benchmarks

Two benchmark scripts are included:

- `scripts/compare_tokens.mjs`
- `scripts/benchmark_pipeline.mjs`

Run:

```bash
npm install
node scripts/compare_tokens.mjs
node scripts/benchmark_pipeline.mjs
```

### Layout

- `src/aidsl/compiler.py`: Python and C++ backends
- `src/aidsl/cli.py`: CLI
- `examples/`: examples
- `benchmarks/`: token benchmarks
- `docs/paper_draft_zh.md`: Chinese paper draft
