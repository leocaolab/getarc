---
name: name-check
description: 审一段改动(一个 PR、一个分支、或「今天落地的」)里新加的每个类型 —— 先用脚本把新类型全部找出来、按 enum / struct / trait / type 归类，再逐个判：名字合不合规(type-naming)、有没有必要、要它的理由、住对地方没有(跟主人走)、形状三条(透明度和不变量匹配 / total / 一个事实一种表示，和类型要覆盖整个家族)。Use when 有人问「看看有没有新概念 / 怪名字」「检查今天新加的类型」「review 新类型」,审 agent 交回的 PR 时，或放行一批改名之前。只看给定范围里新加的，不审全仓。脚本目前只认 Rust。
---

# name-check:一段改动里新加的类型，逐个过关

为读的人优化：每个新类型都要能用一句外行听得懂的话说清它是什么;说不清就没必要。**判据的原文在
`${CLAUDE_PLUGIN_ROOT}/rubrics/type_design.yaml`**(一条规则一问一答，各带 why 和 Rust 正反例;arc 的评审员审新类型读的也是这一份),
TypeScript / Python 的类型读 `type_design_typescript.yaml` / `type_design_python.yaml`(同名规则翻成那种语言、配那种语言的例子)。
写新类型时的过关顺序在 `type-naming` skill。这里只管**怎么一个不漏地过一遍**,判据不在这里另写一份。

## 1. 找出所有新类型(脚本，不靠记忆)

在要审的仓库根目录跑(只要 `python3` 和 `git`):

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/name-check/find_new_types.py" [BASE] [HEAD]   # 默认 merge-base(origin/main, HEAD)..HEAD
python3 "${CLAUDE_PLUGIN_ROOT}/skills/name-check/find_new_types.py" <某个提交> origin/main   # 某个时刻以来落地的
python3 "${CLAUDE_PLUGIN_ROOT}/skills/name-check/find_new_types.py" --all                     # 全仓:HEAD 上的每个类型
```

- 只算「这段改动里**新加**的定义」:同名同种类在同一段里被删过的(搬家、改缩进、改路径)不算。
- 测试文件(`*tests.rs`、`tests/`、testkit)和内联 `#[cfg(test)] mod` 里的替身默认不算;要看加 `--tests`。
- 每个类型打印原文(doc 注释 + 定义),不转述 —— 判断要对着原文做。
- 范围只给这一段：没人要全仓就不审全仓。要全仓时用 `--all`(从空树比到 HEAD)。
- 字符串里写的样例代码(解析器的 fixture)不是类型，脚本一律跳过。
- 脚本只找 Rust 类型。别的语言照同一个思路从 diff 里取新定义(`git diff BASE..HEAD | grep -E '^\+\s*(export )?(class|interface|type|enum) '` 之类)。
- 脚本只找类型。这段改动里新加的**模块名、公开函数名、测试夹具名**从 diff 里取出来
  (`git diff BASE..HEAD --name-status` 看新文件, `git diff BASE..HEAD | grep -E '^\+\s*(pub(\(crate\))? )?(fn|mod|struct) '`),
  只问 `metaphor-word-in-place-of-the-fields-term` 这一条 —— 比喻词常在这里(`world.rs`、`settle()`、测试里的 `World`)。

## 2. 按种类归类

脚本已经按 `enum` / `struct` / `trait` / `type` 分好组。每种的词性规矩不同(rubric 第一组:
`data-type-named-by-verb`、`variant-tense-mismatches-its-role`、`error-variant-not-named-by-its-cause`、
`trait-not-a-capability-or-doer`、`alias-restates-its-structure`),所以按组审，不混着审。

## 3. 逐个过 rubric

对每个类型，把 `type_design.yaml` 的规则**逐条**问一遍(每条的 `gate_question` 就是那一问),
不凭印象说「total」「没问题」。答案对着脚本打印的原文做，写进一张表:

| 列 | 对应的规则 |
|---|---|
| **是什么** | `type-not-sayable-in-one-sentence` —— 写出那一句话 |
| **要不要** | `action-disguised-as-type`、`parameter-bag-type`、`outcome-enum-is-a-disguised-result`、`existing-type-already-fits`、`type-only-read-to-print`;错误类型再加 `error-variant-without-a-real-failure`、`error-shape-ignores-its-callers`。能删就写「删」和怎么删 |
| **要的理由** | 留下的，写出非它不可的理由(例：两个实现都要交回这一份) |
| **住对地方吗** | `type-lives-away-from-its-owner`、`type-visibility-wider-than-its-use` |
| **形状** | `transparency-mismatches-invariant`、`type-not-total`、`sum-type-misses-family-member`、`two-representations-of-one-fact` |
| **弱类型字段** | `weak-typed-field` —— 脚本标出的每个 `String` / `PathBuf` / `&str` / 整数字段逐个答 |
| **名字合规吗** | 第一组五条 + `type-name-names-format-or-mechanism`、`junk-or-coined-word-in-type-name`、`metaphor-word-in-place-of-the-fields-term`、`type-name-collides-or-is-generic`;不合规给 1–2 个候选名。形式合规不等于过关:比喻那一条要写出「这件事在行业里叫什么」,再把名字放进一行真实调用里念一遍 |
| **结论** | 删 / 改名(写新名) / 留 |

撞名用 `git grep -nwE '(struct|enum|trait|type) <Name>' -- '*.rs'` 查。

能用脚本先筛的规则(撞名、动词开头、`XxxError` 没有 `#[from]`、别名右边是 `Vec`/`HashMap`)筛出的是**候选**,
不是结论:全仓筛一轮时，候选常常是逐个看过之后剩下的好几倍。报数时说清哪个是候选数、哪个是看过后的数。

## 4. 交回

- 一张表(每个新类型一行，按种类分组):名字 | 种类 | 文件:行 | 是什么 | 要不要 / 理由 | 名字 | 结论。
- 统计：共几个，删几个、改名几个、留几个。
- 要给人对照看时，把表连同每个类型的原文做成一个网页;文字要大、分组清楚。
- 删和改名放进一个待办，按第 5 节做，只改名不改逻辑。

## 5. 改名(结论是「改名」的那些)

先改定义，再改引用，最后一次 `cargo clippy --workspace --all-targets -- -D warnings`,再一次跑改到的 crate 的测试 ——
不要改一个编一个。

- **同名的不止一个时，按定义划范围**:定义所在文件、同目录的 `*_tests.rs` / `tests.rs`、`use` 了那条路径的文件;
  不要对全仓做整词替换(`Open`、`Read`、`Post` 在别处是别的东西)。注释里只改反引号里的名字。
- **一整套约定整套改，或者都不改**:一组 `*In` / `*Out`、一对 `Ask` / `Answer` —— 只改其中一个，读的人反而看不出它们是一套。
- **起新名字前 grep 本模块**:已经有一个装得下它的类型(`Submit` 旁边的 `Submission`)时，那是
  `existing-type-already-fits`,不是改名能解决的。
- 新名字自己再过一遍 `git grep -nwE '(struct|enum|trait|type) <New>'`;README 和用户文档里写到的旧名一起改，
  已发布的迁移和记录过去状态的设计文档不改。
