---
name: type-naming
description: 新加一个类型(struct / enum / type 别名)之前先过的四道关 —— 说得清它是什么吗、已有的类型能不能装、名字是名词还是动词、名字撞不撞。说不清 = 没必要;类型名(struct / enum / 别名)一律用名词，形容词/分词只用在 enum 的变体上(错误 `XxxError` 是个 enum,变体说死因，如 `NotDelivered`);别名可以，但要用说得出角色的名词。Load 在写或审一个新类型、给类型改名、或评审一个 diff 里冒出来的新名字时。Triggers include "这个类型有必要吗", "起个名字", "有没有新概念", "review 新类型", adding a struct/enum/type alias.
---

# 类型命名(先问必要，再问名字)

一句话：**为读的人优化，不为写的人优化。** 一个新类型要先能用一句外行听得懂的话说清它是什么;
说不清，就是没必要。说得清了，再看已有的类型能不能装下;装不下，才起名 —— 名词、具体、不撞名。

**判据的原文在 `${CLAUDE_PLUGIN_ROOT}/rubrics/type_design.yaml`**(一条规则一问一答，各带 why 和 Rust 的正反例,
arc 的评审员审新类型读的也是这一份)。TypeScript / Python 的类型读 `type_design_typescript.yaml` / `type_design_python.yaml`(同名规则翻成那种语言、配那种语言的例子)。这份 skill 只给**写一个新类型时按什么顺序过**;每一关要判什么,
读 rubric 里点名的那几条，不在这里另写一份。

## 第 1 关：说得清它是什么吗？

写下一句话:「<名字> 是 <业务上的什么>,由 <谁> 产出，给 <谁> 读」。写不出来就停下 ——
多半是参数袋或动作，不是概念。

规则:`type-not-sayable-in-one-sentence`、`parameter-bag-type`、`action-disguised-as-type`、
`type-only-read-to-print`。

## 第 2 关：已有的类型装得下吗？

起名之前先 grep:同一份数据，仓里常常已经有一个类型，或它就是某个已有类型的一部分。
成功和失败要混进一个 enum 时，已有的就是 `Result`。
把边界数据换成仓里已有的校验类型之前，先拿真实录制的数据过一遍它的解析:外部系统的合法值
可能比你的语法宽(GitHub 的 login 可以带 `[bot]`)。
同形的类型已经在别的 crate:先问是不是同一个概念、同一个产出方。是 ⇒ 搬到主人那里合成一个，不另起近义的新名字
(一个测试工具自己定义的 `Head`,该搬进产出它的 git 适配器所在的类型包);同一个形状、两个主人(写侧 / 读侧适配器
各自的 wire 类型，如服务端和网页各自的 `QueuePr`)⇒ 两个类型，在边界转换一次，同名见第 4 关。

规则:`existing-type-already-fits`、`outcome-enum-is-a-disguised-result`;
放在哪里:`type-lives-away-from-its-owner`、`type-visibility-wider-than-its-use`;
形状:`transparency-mismatches-invariant`、`type-not-total`、`sum-type-misses-family-member`、
`two-representations-of-one-fact`、`weak-typed-field`;
错误类型另过:`error-variant-without-a-real-failure`、`error-shape-ignores-its-callers`。

## 第 3 关：名词还是动词？

按种类各有规矩(struct / enum / 别名是名词;错误是 `XxxError` enum、变体说死因;trait 是能力或执行者;变体按状态 / 事件 / 原因):
`data-type-named-by-verb`、`variant-tense-mismatches-its-role`、`error-variant-not-named-by-its-cause`、
`trait-not-a-capability-or-doer`、`alias-restates-its-structure`、`type-name-names-format-or-mechanism`。

类型以外的名字(rubric 不审，写的时候照这个):

| 东西 | 词性 | 例 |
|---|---|---|
| 函数 | 动词、动宾短语;问布尔用 `is_` / `has_` / `can_` | `admit()`、`queue_update()` |
| 变量、字段 | 说意图不说机制 | `open_prs` 不是 `pr_map` |

**并列的字段用同一种说法。** 两个窗口合计一个带 `_total` 一个不带(`caught` 配 `missed_total`),读的人会以为口径不同 → ✅ `caught_total`、`missed_total`。

**布尔用正向。** ❌ `is_not_empty`、`skip_cache`(调用处会写出 `!is_not_empty` 这种双重否定)
→ ✅ `has_items`、`use_cache`。命令行 flag 按命令行惯例写 `--no-cache` 可以;代码里的字段和函数用正向。

**Rust 转换方法的前缀是契约**,调用者靠它预估开销:`as_` 借用、零成本(`as_str()`);
`to_` 克隆或较贵、会分配(`to_string()`);`into_` 拿走所有权(`into_inner()`)。

## 第 4 关：太空泛、撞名了吗？

起名后 grep 一遍:

```bash
git grep -nwE '(struct|enum|trait|type) <Name>' -- '*.rs'
```

撞了，但同名的每一个都只带模块路径用(`review::Outcome`),或只在自己文件里用，可以留;
有一处裸 `use …::Outcome;` 就要改名。
两个互不依赖的 crate 各有一个同名类型(写侧 / 读侧适配器各自的 wire 类型)不算撞名 —— 两个域本该两个类型;
撞名只算同一个 crate 里，或会被同一处 `use` 一起引入的。

`Info` / `Data` / `Manager` / `Helper` / `Util` 一律换掉;`Context` 不一刀切 —— 一次运行的环境确实是个概念，
它成了什么都往里塞的袋子时才算参数袋。

起名前先问这件事在行业里叫什么, 用那个词, 不用日常比喻 (`World`、`Place`、`Answer`、`Death`、`settle`):
形式全部合规的词照样要读的人先猜比喻再翻回来。

规则:`type-name-collides-or-is-generic`、`junk-or-coined-word-in-type-name`、`metaphor-word-in-place-of-the-fields-term`。

## 名字由负责人定

能删掉的就删，不需要名字。删不掉、需要新名字的:
- 先用负责人和设计文档里已经有的词。
- 照抄仓里已有子系统的命名格式不算自创(新子系统照已有子系统的 `Request` / `Refusal` 套名)。
- 实在没有，**给 2–3 个候选并各说一句它的角色**,交负责人挑。被委派的 agent 先选一个写进代码，
  候选列在 PR 描述里，由审查的人定。

## 审一个 diff 时

一段改动里新加的类型，用 `name-check` skill 一个不漏地找出来，逐条过 `type_design.yaml`。
