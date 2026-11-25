# {{feature}} — Implementation Design

> design doc: {{path}} · status: draft | gated({{n}} ≤ 2 rounds; 0 blocking or rest answered) | in-build

## 1. CUJ 实现(自由体,每条一节)

### CUJ-{{X}}: {{名字}}
{{触发 → 一步步发生什么 → 结果。散文,让 maintainer 一遍读懂。}}

## 2. 映射(每个 CUJ 步骤一行)

| CUJ 步骤 | 文件 / 函数 | EXISTING file:line / NEW 签名+归属 | NEW 的搜索证据(贴 grep,不许空) | 放置契约(贴该模块 README 的 Belongs/Doesn't 原文行;无 README 写 `无契约`) | 旧二进制 / 回滚(存储或上线的东西才填) | 证明它的测试 + 种植检查(NEW 行) |
|---|---|---|---|---|---|---|
| {{…}} | {{…}} | {{…}} | {{…}} | {{…}} | {{…}} | {{…}} |

<!-- 语料库扫描(命令+命中,贴在此处): {{全部设计目录 + grep 输出}} -->

## 3. 修订记录(门的各轮)

| 轮 | finding(含责任类) | 处置 |
|---|---|---|
| {{…}} | {{…}} | {{amended / escalated → maintainer / rejected(理由)}} |
