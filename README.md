# AI-DSL

[English](README.en.md)

面向 AI 编程的低 token 中间表示原型。

一句话说，这个项目想把 AI 写代码这件事，从“直接生成人类语言源码”，改成“先生成 AI-DSL，再由本地客户端翻译到目标语言或可执行形式”。

`AI-DSL` 不是一门主要给人写的语言，它更像一种面向 AI 的编程中间层。

## 项目定位

这是一个 `toy project`。

它首先是我提出的一个想法和一个早期原型，不是成熟语言，也不是已经严格验证的完整系统。我非常欢迎更有经验的人继续共建，把这个方向做扎实。

当前的重点不是“替代 Python”，而是验证三件事：

- AI 直接输出更紧凑的 AIDL，是否真的能减少 token
- AIDL 是否能稳定翻译到 Python，并复用现有生态
- 后续是否能继续走向多后端甚至独立二进制

## 核心想法

当前主流语言主要是为人类设计的，不是为 tokenizer 设计的。

如果代码主要是给 AI 生成、传递、修改、拼接和执行，那么表层表示就不一定还要优先服务人类可读性。AI-DSL 的目标是：

- 降低代码生成阶段的 token 消耗
- 降低 AI 与 AI、AI 与本地执行环境之间交换代码的成本
- 保持和现有软件工程生态兼容

长期看，`AI-DSL -> binary -> run` 也是目标之一。理想状态下，项目甚至可以直接用 AI-DSL 构建，编译器、运行时、构建工具和调试接口都围绕 AI-DSL 展开。

## 当前实现

目前仓库里已经有：

- 缩进敏感的 AIDL 语法
- `AIDL -> Python` 翻译器
- `AIDL -> C++` 编译器雏形
- 本地解释执行入口
- 一批已验证有 token 收益的压缩宏
- OpenAI 兼容 tokenizer 的 benchmark 脚本
- 中文教程、模式分析、论文草稿

当前稳定主线仍然是 Python：

1. `ai-dsl -> python -> interpreter -> run`
2. `ai-dsl -> c++ -> compiler -> run`
3. `ai-dsl -> binary -> run`（未来目标）

## Python 方向

现阶段优先做强 `AI-DSL -> Python`。

这里还有一个当前阶段必须坚持的约束：

- 语法设计必须支持 `Python <-> AIDL` 双向转换
- 现阶段优先保证一一对应、可逆、可回译
- 任何会破坏双向可逆性的语法糖，当前都不应该进入主语法

也就是说，现在还不是去追求“更自由但不可逆的极限压缩”时候。当前原型必须先把可逆性站稳。

在这个前提下，当前语法新增了一种更适合 token 压缩的平铺写法：

- 每一行默认顶格写
- 行尾使用 ` 空格 + 1 个数字` 表示“翻译后下一行的缩进空格数”
- 当前 Python 路线里，这个数字应为偶数，例如 `0 / 2 / 4 / 6 / 8`
- 最后一行理论上可以省略这个数字，但当前原型为了保持稳定回译，默认仍会显式写出

例如：

```text
for step in range(10) 2
= loss criterion(logits, y) 2
p loss 0
```

这种平铺形式和传统缩进形式在当前原型里应当是等价的，并且都必须支持双向转换。

已经支持并实际用于压缩的宏包括：

- `F / M / FM`
- `S / A / E`
- `SFM / CF / DFM`
- `CO`
- `KV / KVF`
- `ANYN / ALLNN / CNTNN`

这些设计不是为了语法好看，而是为了压缩 Python 里的高频结构，比如：

- filter + map
- sum over filter-map
- count-if
- dict comprehension
- `None` 合并与存在性判断

## 结构化规则

当前 Python 子集的规则已经单独收敛成结构化文件：

- `src/aidsl/rules/python_aidl_rules.json`

翻译器会直接读取这份规则文件；skill 也引用同一份规则。这样做的目的，是先把“语言子集定义”和“翻译器实现”对齐。

但这只是原型期方案，不是最终形态。

如果未来规则集越来越大、越来越语义化、越来越依赖 lowering/runtime 细节，那么把这整套规则通过 prompt 或 skill 塞给模型，可能反而带来 token 负收益。长期目标仍然是让模型直接掌握 AIDL，而不是永远依赖外部 skill。

## Skill 只是临时接入层

为了让当前客户端还能输入 Python 风格任务、但要求模型直接输出 AIDL，我先做了一个本地 skill：

- `skills/aidl-python-output/`

它的作用只是原型接入，不是长期产品形态。长期看，我更希望模型能够直接用 AIDL 去训练、理解和生成，而不是靠额外 skill 纠正输出形式。

## 快速开始

```bash
cd C:\Users\renzhc\workspace\ai-dsl-prototype
python -m venv .venv
.venv\Scripts\activate
pip install -e .
```

翻译：

```bash
aidsl translate examples\fib.aidl
```

运行：

```bash
aidsl run examples\fib.aidl
```

编译到 C++：

```bash
aidsl compile benchmarks\small_task.aidl --target cpp
```

## 例子

```text
f even_square_sum(nums)
  = squares FM(nums,_%2==0,_*_)
  r S(squares)

= data [1, 2, 3, 4, 5, 6]
= result even_square_sum(data)
p result
```

翻译成 Python：

```python
def even_square_sum(nums):
    squares = [it * it for it in nums if it % 2 == 0]
    return sum(squares)

data = [1, 2, 3, 4, 5, 6]
result = even_square_sum(data)
print(result)
```

## Benchmark

当前有几类脚本：

- `scripts/compare_tokens.mjs`
- `scripts/benchmark_pipeline.mjs`
- `scripts/report_statement_savings.mjs`
- `scripts/analyze_patterns.mjs`

运行：

```bash
npm install
node scripts/compare_tokens.mjs
node scripts/benchmark_pipeline.mjs
node scripts/report_statement_savings.mjs
```

## 文档

- `docs/tutorial_zh.md`：中文教程
- `docs/paper_draft_zh.md`：中文论文草稿
- `docs/python_compression_analysis.md`：Python 压缩分析
- `docs/python_pattern_mining.md`：热门 Python 项目模式挖掘
- `docs/llm_serving_pattern_mining.md`：Transformers / vLLM / SGLang 模式挖掘
- `docs/statement_token_savings.md`：语句级 token 节省报告

## 仓库结构

- `src/aidsl/frontend.py`：DSL 前端与公共工具
- `src/aidsl/python_translator.py`：Python 翻译器
- `src/aidsl/cpp_translator.py`：C++ 编译器雏形
- `src/aidsl/compiler.py`：后端分发入口
- `src/aidsl/rules/`：结构化规则
- `skills/aidl-python-output/`：原型期 skill
- `examples/`：示例
- `benchmarks/`：基准与样例
- `docs/`：教程、分析与论文草稿

## 愿景

更激进一点，AI-DSL 也许不只是“比 Python 更短的 DSL”。

未来甚至可以继续演化出一种更偏向 AI 内部交换的语言形式：建立在更高信息密度的人类语言材料之上，主动删掉对 AI 推理帮助不大的修饰，再通过端侧翻译器快速恢复成宿主语言或人类可读文本。

未来也许可以进一步探索“无损编码 + 有损解码”这类方案，但那是后话。当前阶段不这么做；现阶段仍然以双向可逆和一一对应为硬约束。

## 共建

如果你觉得这个方向有价值，欢迎继续发扬光大，尤其欢迎真正懂这些的人：

- 编译器 / 程序语言
- 程序分析
- LLM 系统
- tokenizer / 压缩 / 训练数据设计

我现在做的事情，本质上是在先把 idea 和原型钉下来。后面把它真正做成体系，靠的是更强的人来继续推进。
