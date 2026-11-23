---
name: error-check
description: 审一段 Rust 代码（一个 crate、几个文件或一个 diff）的错误处理：普查每一处会失败、会吞错、会 panic 的地方，按守则原文逐处判断它在现实里会不会发生、失败域多大、谁有能力决定、人怎么知道，写清触发条件和多常见，再按类型上的改法模式给出改法清单。用户说「error check」「错误处理检查」「审一下错误处理」「看看哪里会 panic / 吞错」，或者批量清理 unwrap 之前使用。只审不改。
---

# 错误处理检查

## 守则

按规则原文判，不凭这里的摘要，也不凭记忆。规则原文随插件附带：

- `${CLAUDE_PLUGIN_ROOT}/rubrics/l4_contracts.yaml`：`swallowed-exception`、`missing-error-classification`、`untyped-error-origin`、`incomplete-error-context`、`silent-default-on-config-miss`、`silent-continue-past-corrupt-own-data`、`ignored-error-return`。
- `${CLAUDE_PLUGIN_ROOT}/rubrics/rust_best_practices.yaml`：`no-unwrap-in-library`、`default-substituted-for-absent-or-failed`、`error-not-stringly`。
- `${CLAUDE_PLUGIN_ROOT}/rubrics/security_common.yaml`：`unchecked-arithmetic-on-input`。
- 本插件 `shift-left-rust` skill 的「Don't swallow, don't hide」一节：每个 `Option` / `Result` 的四步判断、按时期的 panic 表、改类型的写法清单。
- 项目自己的 `CLAUDE.md` 和编码规范。

守则本身，几句话：

- **每个 `Option` / `Result` 先问真实世界里会不会发生**（IO、外部输入、两次调用之间状态变了、并发、配置、容器和平台差异）。会，就带着原始输入和真实错误传给能决定的那一层；不会但编译器不知道，就改类型或结构，让它写不出来；类型改不了，才 `expect("<证明>")`，消息是审查者能核对的证明。
- **panic 只在**：编译期 `const`；最外层的启动代码（库返回 `Result`，启动方决定死）；测试。稳态不 panic：告警并隔离最小的单位（拒掉这一个请求、停掉这一个任务、断开这一条连接），进程继续跑，照 Linux 内核用 `WARN_ON` 而不用 `BUG_ON` 的做法。外部输入永不 panic。`tokio::spawn` 或子线程里的 panic 等于任务悄悄消失。
- **吞错是同一种病的另一面**：`unwrap_or(默认)`、`.ok()`、`let _ =` 和 panic 一样过上面的判断。降级是调用方的决定，并记下原因。
- **失败带真实原因**：失败时手里那份原始数据和真实错误就是真相，带出去；不要用 `invalid`、`unknown` 一类固定文字顶替。

## 步骤

1. **普查。**只看生产代码（去掉 `#[cfg(test)]`、`testkit`、`tests/`），列出每一处：
   - 会 panic 的：`.unwrap()`、`.expect(`、`panic!`、`unreachable!`、`todo!`、下标 `v[i]` / `map[&k]` / `&s[a..b]`、整数除法、`Instant` / `Duration` 的加减、`as` 截断；
   - 会吞错的：`.ok()`、`unwrap_or*`、`unwrap_or_default`、`let _ =`、`if let Ok(..)` 丢了 `Err`、`Err(_) =>`；
   - 会悄悄丢失失败的：`tokio::spawn` / `spawn_local` / 子线程丢掉的 handle、`Drop` 里做的会失败的事、没有上限的等待（丢掉一个 tokio 运行时、无超时的 join）；
   - 失败被改写的：`map_err` 把带类型的错误格式化成字符串、用固定文字顶替原始错误。
2. **每一处按上面守则的顺序判。**这个失败在现实里会不会发生？会，就该传出去，带上原始输入和真实错误；不会但编译器不知道，就改类型；类型改不了，才用 `expect("<证明>")`。
3. **会发生的，回答五个问题：**
   - **失败域：**一个请求、一条连接、一个任务、一个线程、一次运行，还是整个进程？
   - **谁有能力决定：**传上去的那一层真能决定吗？主循环里一个 `?` 会不会把一条连接的失败放大成停机？反过来，该停的会不会被吞掉？
   - **恢复：**重试、降级、隔离还是停？失败之后状态还一致吗？
   - **人怎么知道：**有日志、计数、告警吗？会不会被外部输入刷爆？
   - **性质：**暂时的、永久的，还是来自边界（外部输入）？
4. **写触发条件和多常见。**写出会触发它的具体输入、配置或时序，以及多常见（常见、少见、几乎不会）。按概率乘以后果排序：要配一个天文数字的超时才会溢出的，排在每个连接都可能撞上的后面。不写条件的发现不收。
5. **按下面的模式定改法。**守则要求批量清理先普查分类、再按模式定改法、最后才动代码，所以这个 skill 只出清单，改法给人看过才动。

## 改法模式

这些是在真实代码上用过的写法。先找能套上的模式，套不上再想新的。

- **失败按类型带真实原因。**错误是枚举，变体带上下文（线程名、路径、原文）和 `#[source]` 原始错误；不格式化成字符串，不用固定文字顶替。缺陷也带真实数据：用 `String` 带 panic 原文，不用 `&'static str` 省那一次分配，这一次分配换来的是知道发生了什么。
- **只有调用方要做出不同决定时，才拆成不同的变体或类型。**「环境失败」和「代码缺陷」如果调用方处理方式一样（比如都是停掉这次运行、报告根因），就留在同一个枚举里，不为了分类而分类。
- **状态用枚举，不用「几个 `Option` 加一个哨兵」。**`Finished { outcome: Ok, failed_at: Some }` 这种写得出来的非法组合，改成 `enum Finished { Ended(T), Failed { error, place } }`；先后顺序交给派生的 `Ord`，不用 `unwrap_or(u64::MAX)`。
- **让转换失败本身就是合法状态。**`RunningSlot` 把「空闲」存成 `u64::MAX`，它超出了 `u32` 的范围，于是 `u32::try_from(raw).ok()` 里的 `.ok()` 没有吞掉任何东西：「不是一个 u32」正好就是「什么都没在跑」的定义。
- **非法值在边界上用现有的错误类型挡住。**用户配置的时长在解析时就设上限，用已有的 `SecondsError`（带设置项名字和原值）拒绝，而不是在下游每处加 `checked_add` 兜底。
- **需要清理的资源，不论成败都交还给调用方。**`Result<Runtime, E>` 在失败时只能就地丢掉运行时，而丢运行时会无限期等它的 blocking pool。改成 `#[must_use] struct Served<E> { outcome: Result<(), E>, runtime: Runtime }`，由调用方先看结果，再有上限地清理。
- **先公布失败，再清理。**失败要先让该知道的人知道（取消 stop token、记下失败顺序），然后才做可能很慢的拆除。
- **子线程和任务里的失败要有人接住。**线程退出时必须做的事用守卫保证，比如 `CancellationToken::drop_guard()`，正常返回和 panic 都算；任务里的 panic 用 `catch_unwind` 接住，交给调用方。
- **库不打日志、不决定死。**库把失败交给调用方：返回值，或者一个调用方必须实现的报告方法（例如线程钩子 trait 里的 `pin_failed(core, error)`）。调用方去计数、节流、决定降级还是退出。
- **降级是调用方的决定，并写下原因。**库里不 `unwrap_or(默认)`；调用方选择降级时，留一行日志或一个计数。

## 常见的错误建议

外面流传的错误处理建议，有几条和我们的守则冲突，碰到时按守则判：

- 「缺陷只带 `&'static str`，不在内核里分配」：会丢掉真实原因：失败时手里的原文才是真相。
- 「把错误硬拆成 Domain 和 Defect 两个类型」：只在调用方决定不同的时候才拆。
- 「在下游到处加检查」：先问能不能在边界或类型上让这个状态表达不出来。

## 输出格式

```
| # | file:line | 现在的写法 | 会不会发生 | 触发条件 | 多常见 | 后果 | 失败域 / 谁该决定 | 改法（套用哪个模式） | 依据（规则名或守则条目） |
```

表按概率乘以后果排序。表后用一段话写：哪些其实是同一个根因；先改哪条最划算；哪些地方已经做对了、不要动。

## 例子：一个线程运行时模块

- **先拆运行时、后公布失败**（`threads.rs:151`）：失败域是一次运行，按设计应该停。触发条件是同时遇到致命的 accept 错误（监听 socket 坏了、未知 errno，或者 panic）和一个卡在 blocking pool 里的 Python handler。少见，但后果是服务器无声地半死。改法：交还资源（`Served<E>`），先公布、再清理。
- **stop watcher 不取消 token**（`threads.rs:601`）：触发条件是 stdout 是一个已关闭的管道，`println!` panic。少见，修法一行（`drop_guard()`）。
- **超时相加溢出**（`threads.rs:459`）：要把 `shutdown_timeout` 配到约 9.2e18 秒才会触发，几乎不会；而且这是运维写的配置，不是客户端输入。改法：在配置边界用 `SecondsError` 加上限，排在最后。
- **做对了、不要动的：**生产代码里没有一处 `unwrap`、`expect`、`panic`；错误枚举每个变体都带线程名和 `#[source]`；线程里的 panic 在边界被接住，变成带原文的 `Panicked { payload: String }`；钉核失败交给调用方实现的报告方法，库不替调用方决定。
