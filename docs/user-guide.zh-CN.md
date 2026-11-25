# A.R.C. —— Adversarial Resolution Cycle

> English: [`user-guide/README.md`](user-guide/README.md)

**让 agent 放手写代码,由 arc 把关。**

把一个长任务交给编码 agent,最怕的是代码跑通了,坑也埋下了。arc 让两个模型对着干:评审员(Critic)挑毛病,
修复者(Fixer)逐条改、逐条答,来回几轮,直到评审员说 LGTM(Looks Good To Me),或者轮数用完、交给人拍板。

arc 分两部分,一起装:

- **`arc` 命令行**,装在每台写代码的机器上。改动离开你的机器之前,先在本机评一遍(`arc local-review`),
  让 Fixer 修到评审员满意(`arc fix`),再用 `arc submit` 交给流水线。
- **流水线**,跑在你自己的一台机器上:评审服务审每个 PR;合并机只在评审员说了 LGTM、而且你自己的 `merge.yml`
  没有跑出新失败时才落地;每晚发布、按需部署;agent 和人在聊天服务器上协作(`arc bridge`)。

## 快速安装

**让编码 agent 装(推荐)。** 在要用 arc 的仓库里打开 Claude Code、Codex 或别的编码 agent,把下面这段发给它。
它会下载 `arc`、配好模型、初始化仓库;要动全局配置(`~/.tars/config.toml`、`~/.arc/`、`~/.claude/settings.json`)或推送之前,先问你。

```text wrap
Install the arc-setup skill. If you're in Claude Code, run `claude plugin marketplace add leocaolab/getarc`, then `claude plugin install arc@getarc`. If you're in another agent, run `npx skills add leocaolab/getarc --skill arc-setup` and select your agent. Use one installation method. You can read the skill directly at https://github.com/leocaolab/getarc/blob/main/skills/arc-setup/SKILL.md (raw: https://raw.githubusercontent.com/leocaolab/getarc/main/skills/arc-setup/SKILL.md). Then use the arc-setup skill to install and configure arc in this repository.
```

**自己装。** 支持 macOS(Apple Silicon)和 Linux x86_64。脚本会按 `SHA256SUMS` 校验下载的文件,装到 `~/.local/bin`,不用 sudo:

```bash
curl -fsSL https://github.com/leocaolab/getarc/releases/latest/download/install.sh | sh
```

指定版本或目录、Claude Code 插件、VS Code 扩展,见 §0。

## 为什么用 arc

**1. 不花 CI 的钱。** 评审、合并检查、发布都跑在你自己的机器上。合并机在本机执行仓库里的
`.github/workflows/merge.yml`,落地一个 PR 不用一分钟 GitHub Actions。构建目录在两轮之间保持热的:同一项检查,
冷启动 80–156 秒,热目录 11 秒。我们自己的几个仓库,9 月 7 日到 10 月 12 日跑了 2,776 轮合并检查,约 189 个机器小时;
换成 GitHub 16 核的托管机器,光合并检查每月就是约 446 美元。

**2. 从写完到落地,不用人盯。** agent 写完跑 `arc submit`;评审员提 finding,作者改代码、用 `arc submit --fix-answers` 逐条回答,
直到每位评审员都说 LGTM。LGTM 只认那一个 commit:评审服务给它发一张 pass,合并机只收 pass 等于 PR 当前 head 的改动,
再推一次就要重新评。合并机把 PR 合到 main 最新的 commit 上跑检查,没有新失败才落地;每晚的发布再把落地的东西发出去。

**3. 模型随你换,记录留在你手里。** arc 不带模型,也不替你保管 key。它用你在 `~/.tars/config.toml` 里定义的
provider:登录好的 Claude Code、Codex CLI、agy,Anthropic、OpenAI、Gemini、Bedrock 的 API,或者本地的 MLX、vLLM、llama.cpp。
换模型改一行:

```toml config.toml
# <repo>/.arc/config.toml
[roles]
critic = "gemini_flash"    # ~/.tars/config.toml 里定义的 provider id
fixer  = "claude_fixer"
```

代码只发给你选的模型。本机评审的记录在仓库的 `.arc/review.db` 里;合并队列、发布历史、agent 的对话都在你自己的流水线机器上。
`arc local-review` 只在本机跑:不开 PR、不发评论、不触发 GitHub Actions。

## 四步上手

1. **配模型。** 在 `~/.tars/config.toml` 里定义 provider,在仓库里跑 `arc init` 指定谁评审、谁修复(§1)。
2. **本机评审。** 在功能分支上跑 `arc local-review`:把这条分支的改动当成一个本地 PR 来评,只看不改(§4)。
3. **自动修。** 跑 `arc fix`:Fixer 逐条回答 finding,每修一处在当前分支上提交一个 commit,再评,直到 LGTM(§4)。
4. **接上流水线。** 在一台机器上装服务端、登记这个仓,然后 `arc submit` 你的第一个 PR,看它评审、合并、发布(§2)。

## arc 不做什么

- **不是格式检查器。** 格式交给 `clippy`、`ruff`、`eslint`、`gofmt`;arc 看的是语义上的坑和结构上的腐烂。
- **只报告,不卡你。** finding 本身不让构建失败;怎么处理由你(或 Fixer)定。真正挡住落地的是评审员的 LGTM 和你的 `merge.yml`。
- **审的是你的代码,8 种语言。** Rust、Python、TypeScript、JavaScript、Go、Java、C、C++,按目标仓库的语言启用。

**目录** —— 安装和搭建:§0 安装 · §1 配置 · §2 搭流水线 · §3 skills 和插件。提交前在本机评审:§4 命令 ·
§5–§10 arc 怎么审、腐烂、自定义 rubric · §11 接入编码 agent。流水线:§12 组队 · §13 流水线上的评审 · §14 合并 · §15 发布与部署。
§16 故障排查 · §17 代码规范规则。每个 flag 和 `--json` 信封的细节见 `usage.md`。

---

# 第一部分 · 安装、配置、搭流水线

## 0. 安装

arc 是一个工具的两半:`arc` CLI 装在每台有人或 agent 写代码的机器上;**服务端套件**装在你自己的一台机器上,跑流水线 ——
评审、合并、发布。装 arc 就是两半都装。全部以预编译二进制发布在
**[getarc releases](https://github.com/leocaolab/getarc/releases/latest)** 上,不需要 Rust 工具链,也不需要源码。

整条路按顺序是:**安装**(本节)→ **配置**(§1)→ **搭流水线**(§2:初始化仓库、登记、起服务、接客户端、第一个 PR 落地)。

| 机器 | 装什么 | 跑什么 |
|---|---|---|
| 你的笔记本,以及每台 agent 写代码的机器 | `arc` CLI、`gh`,用 Claude Code 的再装 skills 插件 | `arc init`、提交前自查的 `arc local-review` / `arc fix`、`arc submit`、agent 的 hook |
| 一台合并机(推荐 Linux) | 服务端套件(含 `arc`),再加 `git`、`gh` 和你的门禁要跑的工具 | 评审服务、合并服务器、看板、聊天服务器、每晚发布 |

合并机也可以同时是你写代码的机器;两半只要能经网络互相找到。

### 0.1 快速开始:让编码 agent 来装

在要接 arc 的仓库里,把下面这段贴给 Claude Code、Codex 或别的编码 agent:

```text
Set up A.R.C. (arc) in this repository with the arc-setup skill. If you're in Claude Code, run `claude plugin marketplace add leocaolab/getarc`, then `claude plugin install arc@getarc`. If you're in another agent, run `npx skills add leocaolab/getarc --skill arc-setup` and select your agent. Use one installation method. You can read the skill directly at https://github.com/leocaolab/getarc/blob/main/skills/arc-setup/SKILL.md (raw: https://raw.githubusercontent.com/leocaolab/getarc/main/skills/arc-setup/SKILL.md). Then use the arc-setup skill to install and configure arc here.
```

[arc-setup skill](https://github.com/leocaolab/getarc/blob/main/skills/arc-setup/SKILL.md) 先装二进制,再配 tars 里的 provider、
`arc init` 的角色、跑第一遍,动全局的东西之前先问你。PATH 上有 `claude` 时,它默认用你已登录的 Claude Code 当评审和修复的模型,
不要 API key。每个 skill 和插件做什么见 §3。

| 哪一步 | 问你什么 | 写什么 |
|---|---|---|
| `install.sh` | 什么都不问 | `arc` 二进制,放在 `~/.local/bin`(或 `--to` 指定的目录) |
| arc-setup skill | 用哪个模型(有 `claude` 时建议用它,不要 key);每次写全局文件之前 | `~/.tars/config.toml`、`.arc/config.toml`,再跑第一遍 |
| `arc init`(在终端里) | 从 `~/.tars/config.toml` 已有的 provider 里选谁评审、谁修复;一个都没有就停下说明 | `.arc/config.toml`、`.arc/.gitignore` |

### 0.2 装 arc CLI

**一行脚本(推荐):**

```bash
curl -fsSL https://github.com/leocaolab/getarc/releases/latest/download/install.sh | sh
```

它做的事:

- 认出这台机器的架构(macOS Apple Silicon 或 Linux x86_64),取对应的包;
- 用发布里的 `SHA256SUMS` 校验,对不上就什么都不装;
- 替换旧版本之前先跑一次新的 `arc --version`,起不来的二进制不会顶掉能起来的;
- 把 `arc` 放进 `~/.local/bin`。从不 `sudo`,也不改 shell 配置文件:目录不在 `PATH` 上时,它打印要加的那一行。

参数写在 `sh -s --` 后面:

```bash
curl -fsSL https://github.com/leocaolab/getarc/releases/latest/download/install.sh | sh -s -- --version v1.3.0 --to ~/bin
```

| 参数 | 作用 |
|---|---|
| `--version vX.Y.Z` | 装指定版本,而不是最新版 |
| `--to DIR` | 把 `arc` 放进 `DIR`(默认 `$HOME/.local/bin`) |
| `--from URL` | 从 `URL/<文件名>` 取,而不是 getarc 的发布 —— 镜像,或一个 `file://` 目录 |

装完 `arc --version` 打印装上的版本。

**平台:**

| 机器 | 包 |
|---|---|
| macOS,Apple Silicon(arm64) | `arc-darwin-arm64.tar.gz` |
| Linux,x86_64 | `arc-linux-x64.tar.gz` —— 静态链接(musl),任何发行版都能跑 |

Intel Mac、arm64 的 Linux、Windows 没有包;安装脚本会照实说,然后停下。

**手动装:**

```bash
# macOS(Apple Silicon);Linux x86_64 换成 arc-linux-x64.tar.gz
curl -fsSLO https://github.com/leocaolab/getarc/releases/latest/download/arc-darwin-arm64.tar.gz
curl -fsSLO https://github.com/leocaolab/getarc/releases/latest/download/SHA256SUMS
shasum -a 256 -c --ignore-missing SHA256SUMS     # Linux:sha256sum -c --ignore-missing SHA256SUMS
tar -xzf arc-darwin-arm64.tar.gz arc
mv arc ~/.local/bin/                              # PATH 上任意目录
```

### 0.3 一次发布里有什么

每次发布的文件名都一样,所以 `releases/latest/download/<文件名>` 永远是这个形状:

| 文件 | 是什么 |
|---|---|
| `install.sh` | 上面那行安装脚本 |
| `SHA256SUMS` | 各文件的 SHA-256,`sha256sum` 格式 |
| `arc-darwin-arm64.tar.gz` | 只有 `arc` CLI,macOS Apple Silicon |
| `arc-linux-x64.tar.gz` | 只有 `arc` CLI,Linux x86_64,静态链接 |
| `arc-suite-darwin-arm64.tar.gz` | 服务端套件加 `arc`,macOS Apple Silicon,带 README |
| `arc-suite-linux-x64.tar.gz` | 服务端套件加 `arc`,Linux x86_64,带 README。和 CLI 包不同,它链接 glibc 和 libstdc++;最低版本写在包里的 README 里 |
| `arc-skills.tar.gz` | `arc-skills` 这个 Claude Code 插件 |
| `arc-vscode.vsix` | VS Code 扩展 |

### 0.4 编辑器和 agent 的插件

**Claude Code 插件**,从 getarc 插件市场装:

```bash
claude plugin marketplace add leocaolab/getarc
claude plugin install arc@getarc
```

别的编码 agent:`npx skills add leocaolab/getarc --skill arc-setup`,按提示选你的 agent。

不走市场,也可以下发布里的压缩包,用 `--plugin-dir` 挂上:

```bash
curl -fsSL https://github.com/leocaolab/getarc/releases/latest/download/arc-skills.tar.gz | tar -xz
claude --plugin-dir ./arc-skills
```

每个 skill 做什么见 §3。

**VS Code 扩展**(要 VS Code 1.85 或更新):

```bash
curl -fsSLO https://github.com/leocaolab/getarc/releases/latest/download/arc-vscode.vsix
code --install-extension arc-vscode.vsix
```

### 0.5 GitHub 命令行(`gh`)

arc 经 `gh` 和 GitHub 打交道,并记下是谁跑的命令:在编码 agent 的会话里跑,记那个会话;否则记你的 `gh` 登录。所以:

- `arc submit` 用 `gh` 开 PR:每台要提交的机器都要 `gh auth login`;
- `arc local-review`、`arc fix` 在 Claude Code、Codex、agy 里跑不需要 `gh`;在普通终端里跑要登录,没登录会停在 `cannot tell who is submitting`。

`gh` 从 [cli.github.com](https://cli.github.com)、`brew install gh` 或发行版的包装。`gh auth login` 要交互,你自己跑。

### 0.6 合并机

选哪台机器(Linux + systemd 用户服务;Mac 做不到什么)见 §2 第 2 步。除了套件,它还要:

- **`git` 2.38 或更新**(合并服务器用 `git merge-tree --write-tree` 合并,git 太旧就拒绝启动);
- **`gh`,以一个能推目标分支的 GitHub 用户登录**(用跑服务的那个用户 `gh auth login` 一次):合并服务器推它落地的东西,评审服务经 `gh` 读 PR 的标签、贴评审;
- **门禁要跑的每个工具**(编译器、测试运行器、linter),放在你给服务的 `PATH` 上(`[machine] path`,§1)。arc 不装任何东西:workflow 里的 `setup-*` action 只核对机器上已有的版本(§14);
- **`~/.tars/config.toml` 里的 provider**,给真的评审员用,和别的机器一样(§1);用 `claude_cli` 的话,用跑服务的那个用户在这台机器上登录 Claude Code。

装套件:

```bash
curl -fsSLO https://github.com/leocaolab/getarc/releases/latest/download/arc-suite-linux-x64.tar.gz
curl -fsSLO https://github.com/leocaolab/getarc/releases/latest/download/SHA256SUMS
sha256sum -c SHA256SUMS --ignore-missing          # arc-suite-linux-x64.tar.gz: OK
tar -xzf arc-suite-linux-x64.tar.gz               # 解出 ./arc-suite-linux-x64/:十个二进制和一份 README
install -m 755 arc-suite-linux-x64/arc* ~/.local/bin/
arc-server --version
```

tarball 里的 README 写着每个二进制做什么、要系统的什么(Linux 上是 glibc 和 libstdc++ 的版本)。每个服务的 `install` 写的单元按
执行它时的路径跑二进制,所以二进制放下就别再挪。服务等配置好再起(§2)。

| 二进制 | 是什么 |
|---|---|
| `arc` | CLI |
| `arc-server` | 合并服务器,一个仓一个:落地评审过的 PR;也负责登记仓(`arc-server install`、`arc-server tenant …`) |
| `arc-review` | 评审服务,一个仓一个:收提交上来的更新、叫评审员、发 pass |
| `arc-reviewer` | `arc-review` 对一个 PR 版本起的评审员 |
| `arc-fixer` | `arc-review` 可以起来回答 finding 的作者一方 |
| `arc-web` | 看板:评审页、合并队列页、发布页;客户端唯一要问的地址 |
| `arc-bridge` | agent 会话、服务和人之间的聊天服务器;也是 issue 板 |
| `arc-releaser` | 每晚发布(可选) |
| `arc-deployer` | 跑仓库声明的部署 job(可选) |
| `arc-tap` | 集中的测试历史库(可选) |

### 0.7 升级

CLI 在每台机器上重跑 `install.sh`(`sh -s -- --version v1.3.0` 装某一个版本,也用来回退);skills 插件经 Claude Code 升级(§3)。
服务端套件在它的机器上:取新的 `arc-suite-*.tar.gz` 和 `SHA256SUMS`、校验、解开,把二进制放到原来的路径上覆盖旧的(单元写的是这些路径,不用重写),
然后查机器、重启在跑的:

```bash
arc-server tenant check --offline                          # 重启前没有 FAIL
systemctl --user restart arc-web arc-bridge
systemctl --user restart 'arc-server@*' 'arc-review@*'     # 开了测试历史的还有 'arc-tap@*'
```

每个二进制都有 `--version`,说明跑的是哪个构建。英文页:[Install](user-guide/install.md)。

---

## 1. 配置

arc 的设置按「这是谁的事实」分开:每个文件装一类事实,归一方所有,一个事实只写在一处。

### 1.1 文件和归属

| 文件 | 谁的事实 | 放什么 | 提交? |
|---|---|---|---|
| `~/.tars/config.toml` | 你在每台机器上的 | LLM provider:类型、模型、凭据 | **永不** |
| `<repo>/.arc/config.toml` | 这个 clone 的 | 哪个 provider 担任哪个角色(`[roles]`)、评审跳过什么和本机评审评多久(`[review]`)、测试结果在哪(`[test]`)、哪个 job 是部署(`[release]`) | 否 |
| `<repo>/presubmit.toml` | 项目的 | `arc submit` 推之前在你机器上跑的检查,也是 `arc fix` 让 fixer 跑的检查 | **是** |
| `<repo>/.github/workflows/merge.yml` | 项目的 | 流水线落地一个 PR 之前跑的合并门禁(§14) | **是** |
| `<repo>/.arc/delivery.toml` | 项目的 | 项目怎么交付:`[builds.*]`、`[targets.*]`(§15) | **是** |
| `~/.arc/client.toml` | 每台和流水线说话的机器的 | 流水线看板的唯一地址 | 否 |
| `~/.arc/machine.toml` | 合并机的 | 它服务哪些仓(每个是一个**租户**)、怎么服务:门禁、评审路由、发布 | 否 |

写代码的机器上:`~/.tars/config.toml`、仓里的 `.arc/config.toml`(`arc init` 写)和 `~/.arc/client.toml`。仓里提交的:`presubmit.toml`(可选)、
`merge.yml`,要发布时再加 `delivery.toml`。合并机上:`~/.arc/machine.toml`、它自己的 `~/.tars/config.toml`,以及每个仓在那台机器上的 clone 里的
`.arc/config.toml`。`arc` 自己的运行输入走命令行参数,不读环境变量;它替你读的唯一一个环境变量,是 tars provider 点名的 API key。

### 1.2 最小可用配置

在 `~/.tars/config.toml` 里定义至少一个 provider,进仓库跑 `arc init`(它列出找到的 provider,问谁评审、谁修复),然后在一个功能分支上跑 `arc local-review`,评一次当前分支的改动。下面几小节逐个文件说明。

### 1.3 `~/.tars/config.toml`:provider 和 key

模型名和凭据只写在这里;arc 不从别处读 provider,所以一份文件服务这台机器上的每个仓。
每个 provider 是一张按你起的 id 命名的表,`.arc/config.toml` 的 `[roles]` 引用这个 id;provider 表里不认识的键会被拒绝并点名。
要用别的文件,给任何 arc 命令 `--tars-config <文件>`,或 `--tars_home <目录>`(用它的 `config.toml`);都不给时读 `$TARS_HOME/config.toml`,再退到 `~/.tars/config.toml`。

已登录 Claude Code 就不要 API key,`claude_cli` 用你自己的 `claude login`:

```toml ignore: ~/.tars/config.toml, tars's file, not arc's
# ~/.tars/config.toml
[providers.claude_critic]
type = "claude_cli"
default_model = "opus"

[providers.claude_fixer]
type = "claude_cli"
default_model = "sonnet"
tools = "default"        # 修复要改文件;默认的 "disabled" 改不了
timeout_secs = 900       # 默认 300
```

`arc init` 把评审角色放到 `claude_critic`、修复放到 `claude_fixer`。用已登录的 Codex CLI 也一样:`type = "codex_cli"`、填 Codex 的模型 id,
修复那块写 `sandbox = "workspace-write"`(默认 `"read-only"` 改不了文件),`timeout_secs` 默认 600。每个 CLI 类型都还认 `executable`
(默认 `claude`、`codex`),二进制不在 `PATH` 上或不叫这个名字时用。这样两个角色同一家模型;评审换另一家(下面这种要 key 的)更独立。

用 API key 的:

```toml ignore: ~/.tars/config.toml, tars's file, not arc's
# ~/.tars/config.toml
[providers.gemini_flash]
type = "gemini"
default_model = "flash@latest"
auth = { kind = "secret", secret = { source = "env", var = "GEMINI_API_KEY" } }
```

在跑 arc 的 shell 里 export provider 点名的变量(`export GEMINI_API_KEY=…`)。`type` 是 `openai`、`openai_compat`、`anthropic`、`gemini`、`bedrock`、
`vllm`、`mlx`、`llamacpp`、`claude_cli`、`claude_sdk`、`codex_cli`、`opencode`、`antigravity` 之一;`default_model` 写具体的模型 id,或
`<系列>@latest` 取一个系列里最新的;`auth` 的 `source = "env"` 从环境变量读 key,`source = "file", path = "…"` 从文件读,`{ kind = "none" }`
给本地服务;CLI 类型用你自己的登录,不写 `auth`。

### 1.4 `<repo>/.arc/config.toml`:这个 clone 怎么接线

不提交:`arc init` 写的 `.arc/.gitignore` 让 `.arc/` 下只有 `config.toml.example`、
`delivery.toml`、`archcheck.toml`、`arch_waivers.txt` 进仓,它自己也被忽略。`arc init` 在终端里读你的 tars provider,问谁评审、谁修复,写
`[roles]`(`default`、`critic`、`critic_l4`、`critic_l5` 放评审的 provider,`fixer` 放修复的)、一份起步的 `[review] exclude` 和注释掉的 `[test]`;
不在终端里时写 `.arc/config.toml.example` 并以非零退出;已有 `config.toml` 时拒绝,`--force` 覆盖;tars 里没有 provider 时停下让你先定义。

```toml config.toml
# <repo>/.arc/config.toml
[roles]
default = "gemini_flash"   # 没单独写的角色都落到它
fixer   = "claude_fixer"   # fixer 必须显式写,default 不覆盖它

[review]
exclude = ["**/tests/**", "**/docs/**", "**/node_modules/**", "**/dist/**"]
```

- `.arc/config.toml` 里没有 `[providers]`;还带着这一节的文件会被拒绝,报错点名每个 `[providers.<id>]` 块:定义搬到 tars 配置,`[roles]` 照旧。
- `[review] exclude` 是评审和 `arc rot` 跳过的全部路径(arc 没有内置的),每项是相对仓根的 glob:`*` 不跨目录,`**` 跨任意层。
  `max_rounds`(默认 5)和 `react_turns`(默认 24)只管**本机**这一轮(`arc local-review`、`arc fix`);流水线上的评审用 `machine.toml` 里的同名键。
- `[test] junit` 是你的运行器写 JUnit XML 的路径(`arc tap init` 帮你设好并打印它);`[release]` 用 `workflow` + `job` 指名部署 job,写在合并机上那个 clone 里(§15)。

### 1.5 `<repo>/presubmit.toml`:送审前的检查(提交)

`arc submit` 推之前在你机器上按顺序跑它的每条检查,把每条的结果作为 git note 推在 head 旁边;
`arc presubmit` 只跑检查,什么都不推;`arc fix` 把同一份检查(按 PR 填好 `{base}` / `{target}` / `{affected}`)交给 fixer 自检。
失败的检查不挡提交:head 照推、PR 照样进评审,点名没过的检查,以 11 退出。没有这个文件就没有检查。逐条规则见英文页
[Configuration](user-guide/configuration.md#repopresubmittoml--the-checks-before-submit)。

```toml presubmit.toml
timeout_seconds = 1800   # 每条检查的上限;超时连同整个进程组一起杀掉

[[checks]]
name = "merge-check"
command = "git merge-tree --write-tree HEAD {target}"

[[checks]]
name = "clippy"
command = "cargo clippy --all-targets -- -D warnings"
```

`.arc/config.toml` 已没有 `[gate]`;旧文件里留着的不报错(每一段只由它的主人读),删掉即可。

### 1.6 `<repo>/.arc/delivery.toml`:项目怎么交付(提交)

`[builds.<id>]` 说可发布的东西怎么造,`[targets.<id>]` 说它最后到哪,发布页由它画出来(§15)。

### 1.7 `~/.arc/client.toml`:流水线在哪

每台和流水线说话的机器写一行,看板(`arc-web`)的地址:

```toml client.toml
# ~/.arc/client.toml
web = "http://<看板主机>:<端口>"
```

只有这一个键,写错会被拒绝,不会被忽略。客户端别的都向看板要 —— 聊天服务器在哪、这个仓的测试历史写到哪 —— 地址只在合并机上写一次;
在合并机上 `arc-server tenant url web` 打印该写的值。没有 `client.toml` 时,bridge 的 hook 一律放行,`arc tap` 写仓里自己的 `.arc/tap.db`。

### 1.8 `~/.arc/machine.toml`:合并机

只有跑服务端套件的机器有它。每个服务只读这一个文件:单元里不写设置,服务看到放行表之外的 `ARC_*`
环境变量就拒绝启动,并说明换成了什么;`--config FILE` 指向别的文件。它列出这台机器服务的仓 —— 每个是一个**租户**(一张 `[[tenant]]` 表)。
租户的头不用手写:`arc-server install <clone>`(或 `arc-server tenant add <clone>`)登记这个仓,写下 `id`、`name`、`home`。之后:

```bash
arc-server tenant show [owner/name]                    # 每个生效值,以及它来自 machine.toml 还是默认值
arc-server tenant set owner/name gate.rerun=never      # 改租户的键;一次可以写几个 key=value
arc-server tenant unset owner/name gate.rerun          # 退回默认;写 tap 或 release 去掉整张表
arc-server tenant check [owner/name]                   # 文件读不读得到、路径在不在、clone 干不干净、库在不在
arc-server tenant url web                              # 看板地址,写进 client.toml
arc-server tenant list                                 # 每个租户一行
```

`tenant set` 只写 `[[tenant]]` 的键;`[machine]` 和 `[[tenant.review.route]]` 规则直接改文件。每张表都拒绝不认识的键。`[machine]` 写错,所有服务都起不来;
某个 `[[tenant]]` 写错,只拒绝这个租户(点名第几张表、哪个键、为什么),别的租户照常跑。一份完整的文件 —— 一个仓 `acme/widgets`,真评审员审,
打了 `arc-bypass` 标签的 PR 由 dummy 评审员放行:

```toml machine.toml
[machine]
address = "10.0.0.5"     # 别的机器怎么找到这台:它的 IP
expose  = true           # 在这个地址上监听;不写则看板和聊天服务器只听 127.0.0.1
path    = ["/home/ci/.cargo/bin", "/usr/local/bin", "/usr/bin", "/bin"]   # 门禁和部署每一步的 PATH

[[tenant]]
id   = "0199f2c4-7b1e-7a3d-9c55-2f0e8b1d4a60"   # `arc-server install` 写的;永远别改
name = "acme/widgets"                           # GitHub 上的 owner/name,和 clone 的 origin 一致
home = "/home/ci/widgets-ci"                    # 只有 arc 用的 clone;库都在 <home>/.git/arc/

[[tenant.review.route]]   # 打了 arc-bypass 的 PR:dummy 评审员,对一切说 LGTM
label    = "arc-bypass"
reviewer = "dummy"
name     = "dummy"

[[tenant.review.route]]   # 其余每个 PR:真评审员
reviewer = "react"
name     = "react"
```

没人评审的单人仓只要一条兜底规则,指向 dummy;每个 PR 凭它的 LGTM 过评审:

```toml machine.toml#tenant
[[tenant.review.route]]
reviewer = "dummy"
name     = "dummy"
```

`[machine]`(一台机器一份):

| 键 | 默认 | 做什么 |
|---|---|---|
| `address` | 无 | 这台机器的 IP(不是主机名);看板、聊天服务器、测试历史的地址都由它推出 |
| `expose` | `false` | `true`:在 `address` 上监听,别的机器才连得上看板和聊天服务器;`false`:只听 loopback。`true` 而没写 `address` 拒绝加载 |
| `path` | 服务管理器的 | 门禁每一步和部署每一步的 `PATH`;`merge.yml` 要的工具链放这里 |
| `[machine.web] port` | `8787` | 看板的端口;`client.toml` 写 `http://<address>:<port>` |
| `[machine.bridge] port` | `8790` | 聊天服务器的端口;客户端向看板要 |
| `[[machine.disk]]` | 无 | `mount`、`min_free_gib`(可选 `min_free_inodes`):某个挂载点低于下限时,合并服务器不开新的一轮,夜车和部署拒绝 |

`[[tenant]]`(一个仓一份;左列是 `tenant set` 用的名字):

| 键 | 默认 | 做什么 |
|---|---|---|
| `target` | `main` | PR 落到哪个分支 |
| `queue.admit` | `pr` | `pr`:pass 等于 head 的 PR 才收;`any`:推上来的都收,给没有 PR 的远端用 |
| `gate.timeout_secs` | `3600` | 门禁一步的时限;超时连同进程组一起杀掉 |
| `gate.round_timeout_secs` | `gate.timeout_secs` × 4 | 一整轮合并(fetch、合并、每次门禁、push)的时限 |
| `gate.rerun` | `once` | `once`:新失败要在同一个 sha 上出现两次才打回;`never`:第一次读到红就打回 |
| `gate.too_divergent` | `100` | 冲突路径数到这里,这一轮直接判分歧过大,不跑门禁 |
| `gate.fetch_private_deps_over_ssh` | `false` | `true` 给每一步 `CARGO_NET_GIT_FETCH_WITH_CLI=true`,cargo 用跑服务那个用户自己的 git 凭据拉私有依赖 |
| `gate.read_key` | 无 | 一把只读的 deploy key;只有 `tenant check` 用它,证明这把 key 推不了 |
| `[[tenant.review.route]]` | 无 | 谁审哪个 PR,见下。**一条规则都没有 = 没人评审,什么都落不了地** |
| `review.gate` | `all_lgtm` | 哪些 LGTM 给 head 发 pass:`all_lgtm` 每位评审员;`one_lgtm` 任意一位 |
| `review.max_rounds` | `5` | 一位评审员不给 LGTM 最多回几轮;到上限算它 LGTM,不再评 |
| `review.react_turns` | `24` | `react` 评审员一次评审最多调几次模型 |
| `review.reviewer_timeout_secs` | `3600` | 评审员跑多久没交回就杀掉、重叫 |
| `review.reviewer_attempts` | `3` | 连续几次叫起都没交回,评审就停下,并在 PR 的聊天频道里说明 |
| `review.fixer_client` | `author` | 谁回答 finding:`author`(经聊天服务器送进作者的 agent 会话)、`claude`(在 head 的 worktree 里 `claude -p` 修)、`tars`(arc 自己的 fixer)、`nothing`(作者自己再 `arc submit`) |
| `review.model_config` | clone 的 `.arc/config.toml` | 另一份文件,真评审员用它的 `[roles]` |
| `bridge.enabled` | `false` | `true`:合并服务器把每一轮的判决发进 PR 的聊天频道,署名 `merger@<owner>:<name>` |
| `github.mirror` | `true` | `false`:评审不贴到 PR 上,issue 板不镜像到 GitHub issue;两样都只留在 arc 里 |
| `[tenant.tap]` | 无 | 集中的测试历史库;`tap.port`、`tap.gate_token`、`tap.tokens` 一条 `tenant set` 写齐 |
| `[tenant.release]` | 无 | 每晚发布;`release.clone`、`release.build`、`release.artifact` 一条 `tenant set` 写齐(§15) |

**评审路由。** `[[tenant.review.route]]` 是一张有序的规则表,每条有 `reviewer`(跑哪个评审员:`dummy`、`basic` 或 `react`)、`name`
(它的回复署谁的名,gate 按这个名字数 LGTM),可选 `label`。一个 PR 版本进评审时,PR 带着标签的每条规则各加一位评审员;不带 `label`
的规则只在没有带标签的规则成立时算数。这一版的评审员集合之后不换。规则用到的标签要先在 GitHub 上建好(`gh label create arc-bypass`)。
`dummy` 不调模型、说 LGTM;`basic` 和 `react` 用租户 clone 的 `.arc/config.toml` 的 `[roles]`(至少 `critic_l4`,或 `default`)和那台机器
`~/.tars/config.toml` 里的 provider。

改了值:合并服务器每一轮重读 `machine.toml`,评审服务和看板只在启动时读,所以先 `arc-server tenant check`,再重启它们
(`systemctl --user restart arc-review@<owner>-<name> arc-web`)。英文页:[Configuration](user-guide/configuration.md)。

---

## 2. 搭流水线 —— 初始化仓库、起服务、第一个 PR 落地

流水线是 arc 的服务端一半:按路由把每个 PR 派给评审员,只在评审员 LGTM、且你自己的 `merge.yml` 没有新失败时落地,再按时发布。
它跑在你自己的一台服务器上(下文称「合并机」);开发者笔记本与各 agent 节点只装 `arc` CLI,和它说话。本节从装好的二进制(§0)
一直走到第一个由流水线落地的 PR;用到的每个文件和键见 §1。英文页:[Set up the pipeline](user-guide/onboarding.md)。

### 1. 服务端组件

服务端套件随 CLI 同一个 release 发布(`arc-suite-linux-x64.tar.gz` / `arc-suite-darwin-arm64.tar.gz`)。流水线由 5 个服务组成:

| 组件 | 部署粒度 | 核心职责 |
|---|---|---|
| `arc-web` | 单机单实例 | Web 看板(项目和 issue、评审页与改动详情、合并队列、发布页),也是所有客户端唯一要配置的入口地址 |
| `arc-bridge` | 单机单实例 | agent 会话、后台服务与人之间的房间与消息(§12);也是 issue 板 |
| `arc-review` | 单仓单实例 | 接收 `arc submit` 排进队的评审请求,按路由规则分配评审员;评审员 LGTM 后签发 pass(§13) |
| `arc-server` | 单仓单实例 | 取 pass 与 head 一致的 PR,执行 `merge.yml`;改动没有新增失败就自动合入(§14) |
| `arc-releaser` | 单仓单实例(可选) | 每晚为发布分支的最新提交打 tag,发布为 GitHub prerelease(§15) |

合并机服务的每个仓是一个**租户**:`~/.arc/machine.toml` 里的一张 `[[tenant]]` 表、合并机上一个只给 arc 用的 clone、以及它自己的那几个单仓服务实例。

### 2. 宿主机选型

**推荐:Linux x86_64,支持 systemd 用户级服务。** 服务要常驻,就要给跑服务的用户开启驻留(linger):systemd 的用户级服务跟着登录会话走,不开的话最后一个会话结束(比如 SSH 断开)服务就停,机器重启后也不会自己起来;开了就开机自启、断线照跑。每个服务的 `install` 写完单元都会提醒这一行,在你断开 SSH 之前开好即可:

```bash
loginctl enable-linger $USER
```

**macOS(Apple Silicon)** 虽有 `darwin-arm64` 构建,但只适合手动验证评审与合并,不适合常驻的流水线:

- 各服务的 `install` 只生成 systemd 单元,不生成 launchd 配置,服务要手动拉起(`arc-server --tenant <owner/name>`、`arc-review --tenant <owner/name>`、…),崩溃后没人重启;
- `arc deploy` 与发布页的 **Deploy** 按钮用 `systemd-run` 起部署,没有 systemd 就拒绝执行;
- `arc-server` 与 `arc-review` 靠 systemd 的看门狗(`WatchdogSec=300`)处理进程假死,没有 systemd 就没人管。

合并门禁要在 macOS 上跑的项目(iOS / macOS 构建)目前没有现成方案。合并机除了套件还要什么(`git` 2.38+、登录好的 `gh`、门禁要的工具),见 §0。

### 3. 安装与启动服务

#### 3.1 合并机(服务端)

解开服务端套件,把二进制放到 `PATH` 上(§0)。每个服务只读一个文件 `~/.arc/machine.toml`,不从环境变量取设置:环境里有一张封闭放行表之外的
`ARC_*` 变量时,服务拒绝启动,并说明它换成了什么。

先写 `[machine]` —— 别的机器用哪个地址找到这台、要不要在这个地址上监听、门禁每一步的 `PATH`:

```toml machine.toml
[machine]
address = "10.0.0.5"
expose  = true
path    = ["/home/ci/.cargo/bin", "/usr/local/bin", "/usr/bin", "/bin"]
```

再生成并启动 systemd 用户单元(各组件自带的 `install` 写单元文件,并打印启动它的几行;不用手写单元):

```bash
# 1. 单机全局服务
arc-bridge install                    # 生成 arc-bridge.service
arc-web install                       # 生成 arc-web.service
systemctl --user daemon-reload
systemctl --user enable --now arc-bridge.service
systemctl --user enable --now arc-web.service

# 2. 单仓租户服务(仓登记好之后,见第 4 步)
arc-server install <clone>            # 把仓登记为租户,生成 arc-server@.service(以及 arc-rot@ 单元)
arc-review install                    # 生成 arc-review@.service
arc-releaser install <owner/name>     # 可选,要先有 [tenant.release]:生成 arc-releaser@.service 与 .timer
systemctl --user daemon-reload
systemctl --user enable --now arc-server@<owner>-<name>.service
systemctl --user enable --now arc-review@<owner>-<name>.service
systemctl --user enable --now arc-releaser@<owner>-<name>.timer
```

单元实例名是租户名把 `/` 换成 `-`(`systemd-escape owner/name`)。看板起来后的地址由 `arc-server tenant url web` 打印(默认 `http://<address>:8787`)。

提示:`arc-web` 只在启动时读一次 `machine.toml`,每登记一个仓之后执行 `systemctl --user restart arc-web`。`arc-server tenant show` 查看每个生效值及其来源;
`arc-server tenant check` 逐个租户检查 `tenant-reads`(表读得出来)、`paths-exist`(路径都在)、`home-is-clean-clone`(clone 干净)、`home-is-canonical`
(写的是真实路径)、`name-agrees-with-origin`(租户名和 origin 一致)、`read-key-is-read-only`(只读 key 推不了)、`stores-in-home`(库都在 clone 里)、
`files-read`、`units-carry-no-config`(单元里没有手写的 `ARC_*`),每项打印 `ok`、`skip`、`warn` 或 `FAIL`。

#### 3.2 客户端与 agent 节点

在每台要接入流水线的开发机与 agent 宿主机上:

1. 在 `~/.arc/client.toml` 写 `arc-web` 看板地址,就是 `arc-server tenant url web` 打印的那个值(§1):

   ```toml client.toml
   web = "http://10.0.0.5:8787"
   ```

2. 为你的编码 agent 安装 hook,让评审员的 finding 和每个 PR 的结局送进它的会话(§11、§12)。

### 4. 仓库接入(租户注册)

新仓接入时,建议只先开评审和合并门禁,首个 PR 成功合入后,再逐项开启私有依赖、TAP 测试历史、每晚发布与 bridge 判决(每开一项都多一个库要求存在)。

**在你笔记本上的仓里:**

1. 在 `~/.tars/config.toml` 定义 provider,`arc init` 写 `[roles]`(§1);在功能分支上 `arc local-review`、`arc fix` 能跑通(§4)。
2. `presubmit.toml`(可选):`arc submit` 推之前跑的检查(§1)。
3. **定义合并门禁文件 `.github/workflows/merge.yml`。** 合并机从每个改动的目标分支(base)读取它,严格按声明顺序逐步执行(§14)。
   每一步写成纯 `run:`,触发器写 `workflow_dispatch: {}`,GitHub 永远不跑它;它不是你的 `ci.yml`。
   `arc workflow .github/workflows/merge.yml --job <job> --list` 列出会跑什么,并点名 arc 跑不了的步骤。
4. 建好要用的标签:`gh label create arc-hold`;路由里用到 `arc-bypass` 的再 `gh label create arc-bypass`。

把 `presubmit.toml` 和 `merge.yml` 提交到目标分支上。

**在合并机上:**

1. **一个只给 arc 用的 clone** —— 不是 worktree,也不是谁的工作目录;写真实路径(不经符号链接);origin 指向这个仓。合并服务器每一轮都在里面 checkout 和清理。

   ```bash
   git clone git@github.com:acme/widgets.git ~/widgets-ci
   git -C ~/widgets-ci status --porcelain            # 没有输出
   ```

2. **确保合并机上的 main 是绿的。** 正式登记前,在合并机本地对 main 完整跑一次门禁。若某一**步骤**(不是单个测试用例)在 base 上就失败,
   合并机分不清哪些失败是新增的,对所有 PR(包括修这一步的那个 PR,它也要过同一道门)都返回 `cannot_say`。红的话先在队列外修好:

   ```bash
   cd ~/widgets-ci && arc workflow .github/workflows/merge.yml --job <job>
   ```

3. **登记:** `arc-server install ~/widgets-ci`。租户名取 origin 说的名字。要落到 `main` 以外的分支,先 `arc-server tenant add ~/widgets-ci --target <分支>`,
   `arc-server install` 会保留它。租户的键用 `arc-server tenant set` 改(§1)。

4. **配置评审路由 `[[tenant.review.route]]`。** `arc-review` 依据路由规则为所有开着的 PR 指派评审员,只有评审员 LGTM 之后 PR 才能进合并队列。
   **没有路由,所有 PR 都无法合入。** 没人评审的单人仓,把所有 PR 路由给内置的 dummy 评审员(对一切说 LGTM,§13):

   ```toml machine.toml#tenant
   [[tenant.review.route]]
   reviewer = "dummy"
   name     = "dummy"
   ```

   真评审员(`reviewer = "react"`)要这个 clone 自己的 `.arc/config.toml` 里有 `[roles]` —— 在 `~/widgets-ci` 里跑 `arc init`;`.arc/` 不算 clone 不干净 ——
   以及这台机器 `~/.tars/config.toml` 里的 provider。

5. **检查,然后起它的服务**(3.1):`arc-server tenant check acme/widgets` 直到每行都是 `ok` 或 `skip`;再 enable `arc-review@acme-widgets.service` 和
   `arc-server@acme-widgets.service`,重启 `arc-web`。这两个服务启动时对自己的仓跑一遍不联网的检查,有 `FAIL` 就拒绝启动。

### 5. 提交流程(`arc submit`)

在开发机的功能分支上:

```bash
arc local-review && arc fix            # 可选:提交前在本机评审、修复
arc submit                             # 推送分支、创建或复用 PR,并把评审请求放进队列
```

执行机制:`arc submit` 先跑 `presubmit.toml` 里的本地检查,再推送分支、开(或复用)PR、把评审请求入队,然后退出。之后由服务端接管:
§13(评审)→ §14(门禁与合并)→ §15(部署)。在看板上看它走,或在合并机上
`journalctl --user -u arc-review@acme-widgets.service -u arc-server@acme-widgets.service -f`。

- **合并控制:** 要暂缓合入,给 PR 打 `arc-hold` 标签。
- **issue 关联:** 看板是 issue 的唯一真源(GitHub 只是镜像),所有 issue 都经 `arc issues` 管理。PR 标题里写 `b/<n>`,会把这次提交记到看板的那条 issue 上。
  记不上时(issue 不存在,或看板连不上),`arc submit` 已经推了分支、把评审请求入了队,只是那条 issue 上没记下这次提交:它点名那条 issue,以退出码 8 结束。

### 6. 数据:流水线收集什么、存在哪

流水线替你的团队收集两类数据:**测试数据**和 **agent 的对话**。全部存在你自己跑服务端套件的机器上;arc 只把它们送到你自己的服务器,不送到别处。我们收不到,也不读、不用。
`arc local-review`、`arc fix` 在你机器上写下的东西只在仓库的 `.arc/` 里,不往外送。英文页:[Your data](user-guide/data.md)。

**测试数据(TAP)**

| 收什么 | 谁送 | 什么时候 |
|---|---|---|
| 每个提交的 diff(改动区域) | post-commit hook 里的 `arc tap record` | 每次提交(跑过 `arc hook install` 的 clone) |
| 测试运行器写出的 JUnit XML | 合并门,经 `ARC_GATE_OUT`(§14) | 每次开了测试历史的门 |
| 构建耗时、编译失败日志 | `arc tap build` / `arc tap build-log` | 只在你或 agent 手动跑时 |

arc 从不跑你的测试,只记你的运行器已经写下的结果。存在每个仓(租户)的 `home` clone 下(`~/.arc/machine.toml` 里写的那个):`<home>/.git/arc/tap.db` 是测试历史库,
`<home>/.git/arc/logs/<表>/date=YYYY-MM-DD/` 是按天分的 Parquet 原始行。用途:慢测试和不稳定测试(`arc tap signal`)、一个改动能碰到哪些测试(`arc affected`)、
变异存活率(`arc tap coverage`、`arc tap gaps`)、存储丢了哪些写入(`arc tap absence`)。

**对话数据(arc bridge)**

| 收什么 | 谁送 | 什么时候 |
|---|---|---|
| Claude Code 的 transcript(含子 agent)、meta 文件、transcript 里提到的工具输出、`~/.claude/history.jsonl` | `arc intent collect`,每个 hook 在后台起一个 | 每次 hook 之后,只送服务器还没有的 |
| 会话跑过的每个目录属于哪个仓 | 同一个 `arc intent collect` | 同上 |
| 用 `arc bridge send` / `post` 发的消息 | 发的人 | 发出时 |

Codex CLI 的 transcript 目前不上传。

装了 hook 的每台机器上:`~/.arc/bridge-archive/` 留一份 transcript 字节(Claude Code 约 30 天后会删 transcript);`~/.arc/logs/bridge-collect.log` 记每一趟送了什么、哪些没送出去和原因。

服务器上,在 `arc-bridge` 读的那份 `machine.toml` 旁边(默认 `~/.arc/`):`bridge.db`(会话、消息、房间和索引)、`raw/`(收到的每条记录原样,Parquet,索引可以从它重建)、
`intentdb/` 和 `log/`(从 transcript 派生的)、`bridge-archive/`(transcript 的侧车文件)。用途:每个房间的 feed、搜过去的对话(`arc intent history`)、监督会话、落地通知。

### 7. 一台机器服务几个仓

属于一个仓的都按租户分;看板和聊天服务器共用。

| | 每个仓(租户) | 每台机器一份 |
|---|---|---|
| 配置 | `~/.arc/machine.toml` 里一张 `[[tenant]]` 表 | 同一文件里的 `[machine]` |
| clone | 一个专用 clone;它的库(`merge.db`、`review.db`、…)在它的 `.git/arc/` 里 | — |
| 服务 | `arc-server@<owner>-<name>`、`arc-review@<owner>-<name>`,开了的还有 `arc-releaser@…`、`arc-tap@…`、`arc-rot@…` | `arc-web`、`arc-bridge` |
| 仓里的文件 | 它自己的 `merge.yml`、`presubmit.toml`、`.arc/delivery.toml`;clone 的 `.arc/config.toml` | — |

两个仓从不共用门禁、评审路由、发布或库;一个仓配错只停它自己的服务。加一个仓就对它重走第 4 步。`arc-server tenant list` 列出每个租户;
`arc-server tenant remove <owner/name>` 把一个租户从名册上拿掉(clone 和历史都留着),先停掉它的单元。不带名字的 `arc-server tenant check --offline`
检查每个租户,有一行 `FAIL` 就以 1 退出:每一步之后、每次升级之前都跑一遍(§0)。

### 8. 出了问题

| 看到什么 | 先看哪里 |
|---|---|
| 服务日志开头 `refusing to start: arc takes no input from the environment` | 它点名每个 `ARC_*` 变量和它换成了什么;也看 `systemctl --user show-environment` |
| `refusing to start — \`arc-server tenant check <owner/name>\` fails:` | 下面那几行 `FAIL`;通常是 clone 里有未提交的路径,或没写成真实路径 |
| `… is too old — refusing to start (need git >= 2.38)` | 升级合并机上的 git |
| PR 一直进不了合并队列 | 它的 base 是不是租户的 `target`;有没有路由管到它(`arc-server tenant show`);评审员是否在它当前的 head 上说了 LGTM;有没有 `arc-hold` |
| 每个 PR 都 `cannot_say` | `merge.yml` 的某一步在 base 上就失败,或是 arc 跑不了的一步:在这台机器上对 main 跑门禁(第 4 步) |
| 客户端的 hook、`arc tap` 不理流水线 | `cat ~/.arc/client.toml`,再 `curl <web>/api/machine`:看板应当列出聊天服务器和这个仓 |

本机的问题 —— provider、`.arc/config.toml`、presubmit:§16。

---

## 3. skills 和插件

skill 让你的编码 agent 替你驱动 arc。它们从不重新实现 arc:跑 `arc` 二进制、读它的 `--json` 输出。有三样:

| 是什么 | 从哪来 | 装着什么 |
|---|---|---|
| **`arc` 插件** | 公开的 [getarc](https://github.com/leocaolab/getarc) marketplace,通常用这个 | 下面全部 skill,按 `arc:<skill>` 调 |
| **`arc-skills.tar.gz`** | 每个 release 都带;解开后 `claude --plugin-dir ./arc-skills` | 同样的 skill,按 `arc-skills:<skill>` 调 |
| **`arc-skills` 插件** | 本仓的 marketplace(`.claude-plugin/marketplace.json`),给授权用户 | `arc-setup`、`review`、`fix`、`rot`、`automate`、`maintain`,加上下面的审阅 skill |
| **`arc-room` 插件** | 同一个 marketplace | 让 arc-bridge 上的任何人对你的 Claude 会话说话 |

**公开的 `arc` 插件(getarc)。** Claude Code 里:`claude plugin marketplace add leocaolab/getarc`,再
`claude plugin install arc@getarc`。别的 agent:`npx skills add leocaolab/getarc --skill arc-setup`,选你的 agent。
然后让 agent「装 arc」—— 完整提示词见 §0。装完看:`claude plugin list`(`arc@getarc` 和版本)、
`claude plugin details arc@getarc`(列出每个 skill);会话里 `/plugin`,或敲 `/arc:` 补全 skill 名。
升级:`claude plugin marketplace update getarc`,再 `claude plugin update arc@getarc`,重启 Claude Code。

**`arc-skills` —— CLI 之上的 skill。** 在本仓的 clone 里:`claude --plugin-dir plugins/arc-skills`(只对这个会话);
或在 Claude Code 里当 marketplace 装:`/plugin marketplace add ./`,再 `/plugin install arc-skills@arc`。
每个 skill 按名字调(`arc-skills:<skill>`),或由 Claude 从你说的话里挑:

| skill | 这么说就会用它 | 做什么 |
|---|---|---|
| `arc-setup` | 「装 arc」「配 arc」 | 安装 agent:从 getarc 装二进制、tars 里的 provider、`arc init` 的角色、可选的合并门禁 / 部署 / agent hook,最后冒烟测试。先探测已有的,只做缺的,每一步用一条命令验收,失败就带着真实报错停下 |
| `review` | 「评一下我的改动」「arc local-review」 | 跑 `arc local-review`,先给真问题,分成 core 和噪音。只读 |
| `fix` | 「修真问题」「arc fix」 | 本地评审之后跑 `arc fix`:Fixer 回答本地 PR 的 finding,每修一块在当前分支上一个 commit。什么都不推 |
| `rot` | 「修腐烂」「arc rot」 | 把 `arc rot` 的结构建议当跨文件重构来做;它改代码、提交,所以先确认 |
| `automate` | 「每次提交都跑 arc」「用 arc 卡合并」 | post-commit hook(`arc hook install`),或合并门禁的 `merge.yml` |
| `maintain` | 「arc 坏了」「重置 arc」 | 诊断失败的命令、清本地状态、换 provider 角色 |

每个 skill 先跑同一套前置检查(`plugins/arc-skills/reference/preflight.md`),按同一套方式分 finding
(`plugins/arc-skills/reference/triage.md`)。安装 agent 的路线是数据:`skills/arc-setup/roadmap.json`(各阶段和验收条件)、
`known_issues.json`(真实报错 → 原因和解法),加三个只读的 Python 脚本(`probe.py`、`diagnose.py`、`fetch_arc.py`;只要 `python3` 标准库)。

**审阅 skill —— 我们自己审代码、写代码用的方法。** 同一个 `arc-skills` 插件里还带着 arc 团队自己每天用的审阅方法。
它们不需要 `arc` 二进制:只有 Markdown 和规则集 ——
`plugins/arc-skills/rubrics/` 就是 arc 评审员读的那一份规则,不是副本,所以 skill 说的和 `arc local-review` 报的是同一套规则。
按名字调(`/arc-skills:type-naming`),或者直接说,由 Claude 挑。

| skill | 什么时候用 | 这么说就会用它 | 产出 |
|---|---|---|---|
| `type-naming` | 要加或改一个类型 | 「这个类型有必要吗?起个名字」 | 四道关逐个过;需要新名字时给 2–3 个候选 |
| `comment-clean` | 注释啰嗦,或改动落地之前 | 「清一下这个 diff 的注释」 | 删掉复述、讲历史的,只留为什么、契约和不变量 |
| `coding-convention` | 写或改代码之前 | 和对应语言的 `shift-left-*` 一起加载 | 写代码的方法:先写归属表,类型、判断、注释从表里翻译;末尾是查的时候对照的规则 |
| `coding-principles` | 推一个设计的时候 | 「这违反了哪条原则?」 | 其他规则来源的约 26 条公理 |
| `shift-left-<语言>` | 写 rust、python、typescript、javascript、go、java、c、cpp、swift | 按你改的文件自动挑 | 这门语言的清单,每条带一行坏例子和一行好例子 |

**`arc-room` —— 对会话说话。** 装上以后,arc-bridge 上的任何人在你会话的房间(它的 `feed:<名字>` 频道)
说一句,就作为一条提示进到会话里,一条一行:`【Mei】words`。它也替会话说话:模型写出的文字边写边进房间。
装法:`/plugin install arc-room --marketplace leocaolab/arc`;要 Claude Code 2.1.275 以上、`PATH` 上有 `arc`、
这台机器配好了 arc-bridge(`~/.arc/client.toml`,见 §12)。它只负责把话带进来:等信和回执是 `arc bridge` 的
(`arc bridge await-mail`,然后 `arc bridge ack`)。

---

# 第二部分 · 提交前在本机评审

## 4. 命令:本地评审、自动修复与提交

提交前的检查在开发者本机跑,不需要服务端;检查完由 `arc submit` 交给流水线:

```text
编码实现 ──▶ arc local-review(本地评审)──▶ arc fix(自动修复循环)──▶ arc submit(交给流水线)
```

`arc submit` 之后,流水线接管评审、门禁与合并(§13、§14)。英文页:[The commands](user-guide/commands.md)。

### 1. 核心命令速览

| 命令 | 在哪跑 | 做什么 |
|---|---|---|
| `arc init` | 本机 | 从 tars 的 provider 生成 `.arc/config.toml`(终端里是交互式;不在终端里写示例配置) |
| `arc local-review` | 本机 | 把当前分支的变更当一个本地 PR 评审并输出报告;只读,不改代码 |
| `arc fix [id\|path]` | 本机 | Fixer 逐条处理本地 PR 欠的 finding,每修一处在当前分支提交一个 commit,再审,直到 LGTM 或用满 `[review] max_rounds` |
| `arc rot` | 本机 | 全仓库 L5 结构腐烂审查 |
| `arc presubmit` | 本机 | 在当前 HEAD 上跑 `presubmit.toml` 的检查(和 `arc submit` 推之前跑的一样);什么都不推 |
| `arc submit` | 本机 → 流水线 | 推分支、开(或复用)PR,把评审请求放进流水线的评审队列 |
| `arc hook install` | 本机 | 装 post-commit hook:每次提交后在后台跑 `arc local-review`,并用 `arc tap record` 记下这次提交的 diff;`arc hook uninstall` 卸掉 |

### 2. 本地评审与自动修复

#### 2.1 本地评审(`arc local-review`)

`arc local-review` 评当前分支相对远端默认分支的整个变更(工作区照原样评),在本机 `.arc/review.db` 里当一个本地 PR 跑一轮评审。
报告里每条还开着的 finding 带代码位置、规则、评审员原话和上下文代码,可以直接交给 Claude 等 agent 修,VS Code 插件也能看。arc 测试 fixture 跑出来的报告:

```
[A.R.C.] local-review: local PR acme/app#1 at <sha>

- finding F-1 — lib.rs:3 [free_review::ad-hoc]
  reviewer: x is never read
  code:
    1 | // one
    2 | fn f() {
  > 3 |     let x = 1;
    4 | }

[A.R.C.] 1 finding(s) open — fix them in this working tree and run `arc local-review` again, or run `arc fix`
```

- `--since HEAD` 只评工作区里还没提交的;`--since HEAD~1` 评最后一个 commit 加还没提交的。
- `--show` 不评审,只读回当前分支上一个本地 PR 和每条 finding 的状态。
- 结局:评审放行 head 时,本地 PR 记为 landed,并输出 `LGTM from <评审员>: <原话>`;轮次用满仍没有 LGTM 时输出
  `no LGTM: the reviewer's turns ran out ([review] max_rounds), so the head went through with N finding(s) open`。

#### 2.2 自动修复循环(`arc fix`)

`arc fix` 让 Fixer 逐条回答本地 PR 欠的 finding(fixed 或 won't fix),每修好一处在当前分支提交一个 commit。回答盖在新 head 上再审一次;
还留着 finding 就再修,直到评审员说 LGTM 或用满 `[review] max_rounds`。每轮打印答了什么、评审说了什么,最后一行说为什么停
(`[A.R.C.] fix: stopped — the reviewer said LGTM on the head`,或 `… took its N turns ([review] max_rounds) without an LGTM, so the head is let through with what it left open`)。

- **工作区要干净:** 必须等于 HEAD —— 没有已跟踪的改动、没有未跟踪的文件(被忽略的不算)。先 commit 或 stash。
- **先有本地 PR:** 还没有就先跑 `arc local-review`。
- **回滚:** `git reset --hard refs/arc/before-fix/<分支>` 撤掉整次 `arc fix` 的全部提交。
- **缩小范围与演练:** `arc fix <path>` / `arc fix <id>` 只修一个文件、目录或一条 finding;`arc fix --dry-run` 只评估,不改工作区。

### 3. 提交:`arc submit`

`arc local-review` 和 `arc fix` 从不推。本地 PR 干净了,`arc submit` 先跑 `presubmit.toml` 的检查,再推分支、开(或复用)PR、把评审请求放进队列,
之后归流水线的评审服务(§13)。只想跑同样的检查、什么都不推,用 `arc presubmit`(§1)。

### 4. 辅助工具

都在你自己机器上跑:

- **`arc rot`** —— 全仓库结构审查;只给重构建议,在单独的分支上跟进处理(§8)。
- **`arc hook install`** —— 每次提交后在后台评审(`arc local-review`),日志在 `.arc/critic.log`;跳过 linked worktree 里的提交、rebase / cherry-pick
  过程中的提交、amend,以及已经评审过的提交。它从不改代码;它也用 `arc tap record` 记下每次提交的 diff(日志在 `.arc/tap.log`)。`arc hook uninstall` 卸掉。
- **`arc tap`** / **`arc affected`** —— 测试历史,以及一个改动能碰到哪些测试。arc 从不跑你的测试:`arc tap init` 让 JUnit XML 成为你正常跑测试的副产物,
  `arc tap test` 收进来,`arc tap signal` 显示慢测试和不稳定(flaky)测试。这台机器的看板为这个仓指了集中的 arc-tap(或给了 `--tap-server`)时写进集中库,
  否则写仓里的 `.arc/tap.db`。
- **`arc reset --yes`** —— 清掉这个仓的本地 arc 历史;保留配置。

### 5. 命令索引

#### 5.1 全部命令

`arc --help` 列出 15 个命令,按你要做的事分:

| 你要 | 命令 |
|---|---|
| 在一个仓里装好 arc | `arc init`、`arc hook install` / `arc hook uninstall`、`arc reset --yes` |
| 在本机评审、修一个改动 | `arc local-review`、`arc fix`、`arc rot` |
| 把改动交给流水线 | `arc presubmit`、`arc submit`;`arc archcheck` 是合并门禁里的一步(§14) |
| 发布 | `arc deploy`(在部署机上这个仓的租户 clone 里跑:当场起一次 `arc-deployer`,部署 origin/main 的最新提交) |
| 检查这棵树 | `arc affected`、`arc tap` |
| 记活 | `arc issues`(issue 板,`b/<n>`) |
| 和别的 agent 说话 | `arc bridge`(§12) |
| 问日志:谁改了一个文件、谁在一个仓上干过、一个会话做了什么、谁说过这句话 | `arc intent history` |

每个命令的子命令看 `arc <cmd> --help`,它是 flag 的权威来源。`--json` 让任何命令吐一个机器可读信封(给 agent 用)。

#### 5.2 隐藏的子命令

下面这些不在 `--help` 里,因为是 hook、服务或别的程序替你跑的,不是人敲的;敲了照样能跑:`arc intent collect`(每个 hook 在后台起一个)、
`arc intent floor reindex`(从地板重建索引)、`arc bridge supervisor`(Stop hook 起它)、`arc workflow`(在本机跑 workflow 文件的一个 job)、
`arc post-commit-gate`(post-commit hook 用)、`arc review-task`(`arc local-review` 的引擎起的评审员)、`arc fix-task`(评审服务 `fixer_client = "tars"` 时起的 fixer)。

#### 5.3 改名与删掉的命令

敲了旧名字是用法错误,下面这些 arc 会多说一句该敲什么:

| 你敲的 | 该敲 |
|---|---|
| `install-hook` / `uninstall-hook`(顶层) | `arc hook install` / `arc hook uninstall` |
| `arc issues create` / `new` | `arc issues open` |
| `arc issues search` | `arc issues list` |
| `arc issues close` | `arc issues fixed`、`wont-fix` 或 `duplicate` —— 状态就是它怎么结束的 |
| `arc issues view` | `arc issues show` |

`arc issues verify` / `set-verifier` 和 `arc bridge revive` 删了,没有替代:板上从没有 issue 被验收过,也从没有定时器跑过 revive。

---


## 5. 架构哲学与审查准则:函数式核心、命令式外壳

arc 自身按 Functional Core / Imperative Shell(函数式核心 / 命令式外壳)构建,并用同一套工程标准审查
你的代码。这不是教条,而是一组经过验证的结构约束 —— 让 LLM 生成的代码可维护、可测试、行为确定。arc 的
Critic 把这些准则编码进了 L4 审查标准(rubric),下面每一条都是评审时实际会标出来的。

### 5.1 纯核心与命令式外壳

**原则。** 无副作用的业务逻辑与 I/O 严格分开:状态计算、规则判定留在纯核心里,外层的命令式外壳负责驱动
I/O、网络和文件系统。

**arc 自己怎么做。** arc 的 `review_core` 是纯核心:它的库代码不碰文件系统、环境变量、进程、socket 和时钟,
由 `arc archcheck` 的 `effect-budget` 规则在合并门上检查;它还用编译期 lint
`deny(clippy::print_stdout, clippy::print_stderr)` 禁止打印。把 I/O 混进纯计算逻辑,会被判为架构坏味道。

### 5.2 解析,而不是校验(Parse, Don't Validate)

**原则。** 在输入边界一次性把非结构化数据(原始字符串、JSON、环境变量)解析成带合法性的强类型值。

**审查要求。** 下游直接消费带类型的数据结构,不在核心链路里反复对原始字符串或松散结构做防御性校验。

### 5.3 错误带类型、带成因

**原则。** 错误向上传播时保留它的结构化变体和底层成因(source / cause)。

**审查要求。** 不在边界把强类型错误抹平成字符串(例如 `.map_err(|e| e.to_string())`)。用 `#[from]`
这类机制保留错误链,让上层按具体变体做模式匹配,而不是靠脆弱的字符串 `.contains()`。
规则:`l4_contracts::untyped-error-origin`

### 5.4 闭合域用枚举

**原则。** 状态集合固定且有限的领域,用编译器能做穷尽检查的 `enum` 建模。

**审查要求。** 不用魔法字符串或「字符串类型化」(stringly-typed)的值表示业务状态、事件类型或配置选项。
规则:`rust_best_practices::stringly-typed-domain-value`

### 5.5 不向消费方泄漏哨兵值

**原则。** 缺失和失败要显式表达,不用魔法值掩盖。

**审查要求。** 不用 `null`、`-1`、`""` 这类哨兵值顶替真实的失败或空状态。失败和缺失通过强类型的
`Result::Err` 或 `Option::None` 交给调用方,不静默吞掉真相。
规则:`l4_contracts::missing-error-classification`、`llm_generated_code_smells::ambiguous-return-sentinel`

### 5.6 单一事实来源

**原则。** 数据在产生事实的源头写全,数据单向流动。

**审查要求。** 不从下游的派生视图、缓存或聚合表反向回填(backfill)或重建主数据,避免状态漂移和不一致。

### 5.7 全函数

**原则。** 函数对输入类型的每一个可能值都有明确、安全的定义,不留运行时未处理的异常。

**审查要求。** 不把偏函数(Rust 的 `.unwrap()`、Haskell 的 `head` / `fromJust`)当全函数用;空集合、
`None` 和边界情况要显式处理。
规则:`fp_lens::partial-function-as-total`、`rust_best_practices::no-unwrap-in-library`

### L4 规则速查

| 准则 | 反模式示例 | 触发的规则 |
|---|---|---|
| 错误带类型 | `.map_err(\|e\| e.to_string())` 丢掉错误上下文 | `l4_contracts::untyped-error-origin` |
| 闭合域用枚举 | 用 `"pending"` / `"done"` 字符串管理状态机 | `rust_best_practices::stringly-typed-domain-value` |
| 不泄漏哨兵值 | 失败时返回 `-1` 或空字符串 `""` | `l4_contracts::missing-error-classification`、`llm_generated_code_smells::ambiguous-return-sentinel` |
| 全函数 | 库代码里直接 `.unwrap()`,或不处理空输入 | `fp_lens::partial-function-as-total`、`rust_best_practices::no-unwrap-in-library` |

这些规则都是 `stable`,默认就跑。

---

## 6. LLM 代码腐烂的典型模式

LLM(包括 Claude)写的代码表面可读、产出快,但它带来的腐烂遵循高度可预测的模式。这些缺陷往往藏在局部看似合理的
改动里,人工评审很难察觉;可一旦被准确命名、写成规则,就能被自动抓住。arc 的规则库在 `rubrics/` 目录下,分
L4(单文件契约)和 L5(全仓库结构)两层拦截。

### 6.1 行级和函数级:十类坏味道与 L4 规则

| 腐烂模式 | 典型特征 | 规则 |
|---|---|---|
| 吞掉失败 | `except: pass`、`let _ = fallible()`,或捕获异常后既不重新抛出也不返回错误 | `l4_contracts::swallowed-exception` |
| 边界类型擦除 | 在模块边界把强类型错误抹平成字符串(如 `e.to_string()`),调用方只能靠 `.contains()` 做脆弱的文本匹配 | `l4_contracts::untyped-error-origin` |
| stringly-typed 域 | 用自由字符串而不是编译期可穷尽检查的 `enum` 表示一组固定状态 | `rust_best_practices::stringly-typed-domain-value` |
| 歧义哨兵返回值 | 返回 `null`、`-1` 或 `""`,把「失败」「结果为空」「合法值」混为一谈 | `llm_generated_code_smells::ambiguous-return-sentinel` |
| magic literal | 没有命名、没有解释的硬编码常量直接穿插在业务判断里 | `llm_generated_code_smells::magic-literal` |
| 偏函数当全函数 | 库代码里对可能为空或失败的值直接 `.unwrap()`、`head` | `fp_lens::partial-function-as-total` |
| 外部输入未校验 | 直接消费 HTTP 请求、环境变量或外部文件的数据,不在边界解析和校验 | `security_common::validate-external-input` |
| 错误上下文不全 | 构造错误时不带触发它的关键输入或状态 | `l4_contracts::incomplete-error-context` |
| 过宽的异常捕获 | 宽泛的 catch-all 把处理不了的系统信号和程序 bug 一起吞掉 | `l4_contracts::over-broad-exception-handler` |
| 注释写成 changelog | 叙述修改历史(「把 X 改成 Y」),而不是说明当前代码的意图和不变量 | `comment_hygiene::refactor-history-narration` |

### 6.2 跨文件:结构腐烂

除了行级问题,LLM 还很容易造成跨越单文件边界的结构腐烂:堆积无关职责的 god-module,以及在多个文件里重复实现
同一件事(跨文件造轮子)。每一次局部增量改动看起来都合理,累积起来就破坏了全局内聚。这一类由 L5 的
`arc rot` 抓(§8)。

---

## 7. 两层防御:L4 和 L5

### L4:逐文件契约审查(Critic)

- **规则来源。** `rubrics/l4_contracts.yaml`、各语言的 `*_best_practices.yaml`、
  `llm_generated_code_smells.yaml` 和 `fp_lens.yaml`。
- **一个坏味道,一条 finding。** 每条规则只定义一种具体危害和它的判定边界,所以一处问题只出一条 finding,
  不会泛化刷屏(carpet-bombing)。
- **先确定性预筛,再让 LLM 确认。** 确定性检测器先做便宜的预筛(例如「以哨兵值结尾的吞错」),LLM 结合上下文
  去确认,而不是从零推导规则。
- **闭环。** 每条 finding 由 `arc fix` 或你自己逐条回答 fixed 或 won't fix,新 head 再评一次。改动要等评审者
  LGTM、且合并机跑你的 `merge.yml` 没有新失败,才会落地([合并](user-guide/merge-gate.md))。
- **逃生口。** 极少数评估后确实要保留的写法,加 `[arc:intentional-handle]` 注释说明是有意为之,Critic 就不再
  反复标出。

### L5:全仓库结构审查(`arc rot`)

跨文件扫描单文件视角看不到的涌现式结构腐烂,见 §8。

---

## 8. 量化结构腐烂:`arc rot`

`arc rot` 检测并量化整个仓库的结构腐烂,给你一份可以长期跟踪的技术债清单。它**不**自动重构:重构能力目前在
`experimental_lab` 里,不在主流程。

### 8.1 常用运行方式

```bash
arc rot                 # 全仓库 L5 结构审查(确定性检测 + LLM 研判)
arc rot --no-judge      # 只做确定性信号提取:不调 LLM,零推理成本,适合当 CI 的趋势指标
arc rot --file <path>   # 只扫指定的文件或目录
```

### 8.2 L5 的四类检测

| 检测 | 判定标准 |
|---|---|
| God-module | 职责堆积过多的单个文件:复杂度 × 扇出(fan-out)的混合分位列全仓前 ~5%,且超过 ~300 行下限 |
| 跨文件重复(reinvention) | 同一写法在多个文件里重复:经 α-归一化(抽掉变量名和字面量,保留被调函数名和类型名)后有 ≥3 份高度相似的实现 |
| 重复域类型 | 同一个业务概念在 ≥2 个 crate 里分别用同名 `struct` / `enum` 建模 |
| 结构信号 | 分层倒置(底层模块用了高层消费者的业务词汇命名)、driver / wiring 胶水层里混进了核心逻辑、继承扇出过载(god-trait)、散落的硬编码策略常量 |

> 死代码检测还在 `experimental_lab`,没达到精度门槛,`arc rot` 的正式报告暂不包含它。

### 8.3 结果怎么处理

- **只打印,不挂 PR。** `arc rot` 的 finding 都以 suggestion 级别打印,只留在这一次运行的报告里,不挂到任何本地
  或远程 PR 上,所以 `arc fix` 不会去改它们。
- **重构由你决定。** 要处理某一项,在单独的分支上自己(或让编码 agent)做这次重构,再像别的改动一样走
  `arc local-review` 和 `arc submit`。

---

## 9. Finding 生命周期 —— 状态机

一条 finding 一行(`F-<n>`),同一位置再报落在同一条上,每条有只追加的事件时间线。
身份、事件(谁能发哪种)、状态怎么从事件推出,只写在一处:
`crates/review/types/README.md`「Finding 模型」
(代码还没跟上的地方在它的「代码现状」)。

---

## 10. 自定义审查规则(custom rubrics)

arc 的审查标准是 `rubrics/` 目录下的 YAML 文件。团队不用改 arc 的源码,只要往自己的仓库里提交规则文件,
就能扩展或覆盖内置规则。

### 10.1 规则文件长什么样

每份 rubric 文件写一组规则的元数据和规则条目列表。下面是 `rubrics/my-rules.yaml` 的例子:

```yaml rubric.yaml
name: My Team Rules
description: 本仓库的团队架构与编码规约。
language: [rust]              # 可选:整个文件只对这些语言生效(省略 = 所有语言)
rules:
  - name: no-raw-sql-in-handlers
    status: stable            # stable | experimental | deprecated,省略即 experimental
    universality: [rust]      # 可选:这一条规则自己的语言范围
    description: |
      ANTI-PATTERN:请求处理器里内联拼接 SQL 字符串,而不走 repository 层。
      token(如 handler 里的 `SELECT` / `format!`)只是例子 —— 真正要 flag 的危害是:
      查询构造逻辑泄漏进传输层。经 repository 层发起的参数化调用不要 flag。
```

**规则 ID。** 由 `<文件名(stem)>::<规则 name>` 拼成,所以上面这条是 `my-rules::no-raw-sql-in-handlers`。

### 10.2 怎么加载

- **只有一条路:提交进仓库。** 自定义 rubric 放在被评审仓库根目录的 `rubrics/*.yaml`,随仓库提交。命令行的
  `--rubric-file` 和 `--extra-rubrics` 已经移除。
- **覆盖还是追加。** 文件名(stem)和内置文件同名(如 `rust_best_practices.yaml`)时,整份覆盖内置的那组规则;
  新文件名则追加到这次评审生效的规则里。
- **按 commit 读。** 评审读的是被评审的那个 commit 里的 `rubrics/*.yaml`,不是工作树里没提交的文件。改了规则
  要先提交,之后的评审才会用上。
- **`.arc/config.toml` 不管规则文件。** 它的 `[review]` 段不能写额外的 rubric 路径;`enable`、`disable`、
  `experimental` 三个字段还能解析,但运行时已经不读 —— 本地评审只跑 `stable` 规则。

### 10.3 常见的坑

| 坑 | 怎么回事 |
|---|---|
| `status` 默认是 `experimental` | 评审只跑 `stable` 规则,所以省略 `status` 的规则不会生效,也不报错。要上线的规则必须写 `status: stable`。 |
| 未知字段直接报错 | 解析器开了 `deny_unknown_fields`:字段名拼错会让加载失败,而不是被悄悄忽略。 |
| 语言范围 | 不写语言限制,规则对所有语言的文件都跑。要限定,在文件顶层写 `language: [rust, ...]`,或在单条规则里写 `universality: [rust]`。 |

### 10.4 `description` 怎么写

规则的 `description` 就是交给 Critic 的审查指令(prompt)。为了检得准、不误报,照内置规则的结构写:

- **直说危害。** 写清违反这条规则会破坏哪个不变量、带来什么风险,而不只是列语法禁令。
- **字面量只是例子。** 说明 `SELECT`、`format!` 这类关键字只是线索,要模型按语义判断,而不是机械地按正则匹配。
- **划清边界。** 明确排除合法的近似写法(例如「经 repository 层的参数化查询不要标」),和相邻规则互不重叠,
  做到一处问题只出一条 finding。

---

## 11. 接入编码 agent(Claude Code、Codex CLI、agy)

编码 agent 有两种接入方式,可以只用一种,也可以都用(完整的配置示例见英文页
[Coding agents](user-guide/coding-agents.md)):

| 方式 | 做什么 | 配在哪 |
|---|---|---|
| ① 当角色 | arc 自己拉起这个 agent,当 `arc fix` 的 Fixer 或评审的 Critic | 仓库 `.arc/config.toml` 的 `[roles]`;provider 定义在 `~/.tars/config.toml` |
| ② 当参与者 | 你自己的 agent 会话接到 arc-bridge 聊天服务器,会话停下等待时把评审结论、PR 结局和私信送进去 | agent 自己的 hook 配置,指向 `arc bridge hook`(§12) |

### 11.1 当角色

**怎么配。** 在 `~/.tars/config.toml` 里定义 provider,再在仓库 `.arc/config.toml` 的 `[roles]` 里写上它的 id。
`fixer` 必须单独写,不会退回 `default`。

**支持的 agent 和要注意的设置:**

| agent | tars 类型 | 要注意的设置 |
|---|---|---|
| Claude Code | `claude_cli` | 默认 `tools = "disabled"`;当 Fixer 必须写 `tools = "default"`,否则改不了文件。用 `claude login` 的登录会话,不要配 API key |
| Codex CLI | `codex_cli` | 沙箱默认 `"read-only"`;当 Fixer 要改成 `"workspace-write"` 才能写工作区 |
| agy | `antigravity` | tars 以 `agy -p … --dangerously-skip-permissions` 调用它;`effort` 取 `low` 或 `high`(默认 `high`) |

这些 agent CLI 都自己跑自己的循环,arc 不给它们注入工具,改完后直接读工作区的 diff。仓库带的
`.arc/config.toml.example` 默认用 `claude_cli`;`codex_cli` 和 `antigravity` 能被 tars 识别、arc 也按 agent CLI
调度它们,但 arc 自己的测试还没有端到端跑过它们当 Fixer。

**确认接通。** 在功能分支上依次跑:

```bash
arc local-review        # 先开出本地 PR(Fixer 回答的是这个本地 PR)
arc fix --dry-run       # Fixer 对每条 finding 只读评估,什么都不改
```

配错时会报 `fixer pipeline: failed to build provider '<id>' …`,后半句是 tars 的原话;加 `-v` 重跑可以看到详细的诊断日志。

### 11.2 当参与者

在各个编码 agent 的 hook 配置里指向 `arc bridge hook`,把你本地的会话接到 arc-bridge 上,收发跨会话的消息、接收流水线
上的事件。步骤见 §12。

---

# 第三部分 · 流水线

## 12. 组队:arc bridge

agent 会话、流水线的各个服务和人,都接在同一个聊天服务器 arc-bridge 上。每个会话有一个唯一的名字;消息发给名字,或者发进频道;
会话停下时把信取进上下文。评审的 finding 就是这样送到作者会话的,落地消息就是这样送到提交者的,两个 agent 就是这样一起做一个
milestone 的。英文页:[Team up](user-guide/bridge.md)、[Connecting your coding agent](user-guide/coding-agents.md);每个子命令以
`arc bridge <sub> --help` 为准。

### 12.1 名字、房间和频道

**会话名。** 一个在线会话就是一个地址,所以同一时间两个在线会话不能用同一个名字,否则会收到对方的信。

- Claude Code 用启动时的会话名(`claude -n NAME`),没有就用 session id;也可以在 hook 那一行用 `--name` 定死。
- `arc bridge launch <ROLE>` 以 `<仓名>-<ROLE>-<MMDD><字母>` 起一个 Claude Code、Codex CLI 或 agy 会话,名字取没有在线会话占着的,并打印出来。

**房间和频道。** 每个会话有一个自己的房间,就是它的频道 `feed:<会话名>`:记着这个会话说了什么,别人对它说了什么。其余的都走下面四类频道:

| 频道 | 里面有什么 | 怎么加入 |
|---|---|---|
| `pr:<owner>/<name>#<n>` | 一个 PR 的全过程:评审服务的 finding、合并机的结论、落地 | `arc submit` 把 PR 登记到你的会话,你自动在里面 |
| `release:<owner>/<name>` | 这个仓的部署,以及每次部署带上线的 PR | 会话开始时自动加入它所在仓的这个频道 |
| `landings` | 每个落到 main 的改动一行:分支、落地后的 sha、动了哪些路径 | 自己 `arc bridge join landings` |
| `room:<16 位十六进制>` | 一支队的协商频道(§12.6) | 开队时双方自动加入 |

### 12.2 收发消息和问人

都以你所在会话的名字发,或用 `--as NAME`。没送达就以非零退出,带着服务器的原话:

```bash
arc bridge send codex@review "the fix is pushed"         # 私信给一个名字
arc bridge post 'pr:acme/app#514' "pushed the fix"       # 发进频道;不用是成员
arc bridge join landings                                 # 之后的新消息进你的收件箱
arc bridge leave landings
arc bridge inbox                                         # 看未读,不回执
arc bridge inbox --wait 55                               # 没有就最多等 55 秒
```

**问人。** agent 需要人拍板时:

```bash
arc bridge ask "Start R1 now?" --on b/12 --option "A: start" --option "B: wait"     # 关于某个 PR 时加 --pr <n>
```

它先在这个 checkout 的 issue 板上,把问题开成 b/12 上的一个 `q/<n>`(带选项),再把它发进你自己的房间。人在看板的项目页(Projects)上
看到这个问题,每个选项一个按钮;点一下,就用那个选项的原话裁定 `q/<n>`,再以点的人的名义发回你的房间,到你这里是 `【名字】选项`。

### 12.3 信怎么进会话

- **停下时取信。** 会话只在停下时收信:Stop hook 向服务器取一次。有该打断的信,就拦下这次停下,把全部未读作为下一条输入塞进会话;
  只有安静的信,就放行,它们留在收件箱里等下一次打断,一条不丢;空的就放行。
- **空闲时被叫醒。** Claude Code 用第二条 Stop hook `arc bridge await-mail`(配 `"asyncRewake": true`),停下后替它等信,来信就叫醒;
  Codex CLI 和 agy 在 Stop 那行加 `--mail waiter`。
- **出错就放行。** hook 出任何错都放行,原因写 stderr,以 `[arc bridge]` 开头;没有 `client.toml` 就什么都不做。

§3 的 `arc-room` 插件更进一步:任何人在你房间里说的话,都作为提示进到会话。

### 12.4 各 agent 的 hook 怎么挂

| agent | 写在哪 | 挂什么 |
|---|---|---|
| Claude Code | `~/.claude/settings.json` | `SessionStart`、`UserPromptSubmit`、`PreToolUse`、`PostToolUse` / `PostToolUseFailure`(matcher `Bash`)、`SessionEnd` 各挂 `arc bridge hook <事件>`。`Stop` 挂两条:`arc bridge hook Stop --mail waiter` 和 `arc bridge await-mail`(`"asyncRewake": true`,`timeout` 86400);不想空闲时被叫醒,只挂前一条 |
| Codex CLI | `~/.codex/config.toml` | `[features] hooks = true`;`SessionStart`、`PreToolUse`、`Stop`、`SessionEnd` 各挂 `arc bridge hook <事件> --agent codex --name <名字>`(`--agent codex` 必须写),`Stop` 那行可加 `--mail waiter`。改完重启,在 `/hooks` 里信任 |
| agy | `~/.gemini/config/hooks.json` 或仓库根的 `.agents/hooks.json`(全局和仓库只装一份) | 只挂 `PreInvocation` 和 `Stop`:`arc bridge hook <事件> --agent agy --name <名字>`,`Stop` 那行可加 `--mail waiter` |

几点说明:

- **Claude Code 的减速带。** `UserPromptSubmit` 在上次模型调用超过 1 小时、或上下文超过 10 万 token 时先拦一次,再发一次(这句或别的)就放行。
  短暂离开用 `/loop 55m` 保温(只回复 ok),下班前写交接再 `/clear`。
- **agy 只挂两项。** `PreInvocation` 那一行照 agy 的线上 hooks 文档写,还没在真 agy 上跑过。不挂 `PreToolUse`(它是权限 hook,没在真 agy 上验证过,
  挂错了每次工具调用都受影响)、`PostToolUse`(arc 靠 transcript 记改了哪些文件,agy 留不留这个 hook 的输出没有验证)、`PostInvocation`(和
  `PreInvocation` 重复)、`SessionStart`(1.2.11 没有这个事件)。agy 没有会话结束事件,30 分钟没有 hook 才算下线。

### 12.5 决定什么能打断你

信有多响由发信人定。你可以在服务器上存条件把它收窄:一条都没存,所有该打断的信都打断你;存了至少一条,就只有命中的还能打断,其余变安静,
但仍在收件箱里。条件只会让信更安静,不会更响。

```bash
arc bridge interest add mine            # 发给你的私信,加上 arc submit 登记在你名下的 PR 频道
arc bridge interest add from:<名字>      # 那个发信人
arc bridge interest add tag:escalate    # 那个标签(intervene | escalate | wake)
arc bridge interest list
```

### 12.6 两个 agent 组队

一支队是两个会话带着一个范围一起干,双方都说做完才算完。范围在开队时写定:一个 milestone `b/<n>`,或一份设计文档加它的 commit。

```bash
arc bridge team open --milestone b/42 --with codex@review              # 打印队的 id:room:<16 位十六进制>
arc bridge team open --design docs/x.md@<40 位 commit> --with codex@review
arc bridge post room:00000000000000ab "接口联调完了,请核一下"            # 队的 id 就是它的频道
arc bridge team agree room:00000000000000ab --said "agreed: ship it as written"
arc bridge team list --doc docs/x.md                                   # 讨论过这份设计的队和它们的结论
```

双方一开始就在队的频道里。每方各同意一次、用自己的话;两方都同意了队才关。

**互相读 PR。** 你在这个仓上有一支开着的 milestone 队时,从你会话里跑的每次 `arc submit` 都会在队的频道里请对方读这个 PR、说出立场 ——
同意,或逐条要改的点。submit 单独一行说明:

```
team: asked codex@review in room:00000000000000ab to read this PR and say where they stand
```

这一道在评审服务之前,永远不替代评审服务的 LGTM。对方得是一个顶层会话(在线的,或用 `arc bridge launch` 新起的);另一个会话里的子 agent 不能当一方。

### 12.7 监督会话(可选,Claude Code)

另一个 Claude 会话判断作者会话的每次停下 —— 活还在往前走吗、卡住的问题它能不能自己定 —— 由 `.arc/config.toml` 的 `[supervisor]` 段配置。
`arc bridge supervisor ask` 在一份 transcript 上空跑它:它会看到什么、会怎么判。

---

## 13. 流水线上的评审

代码评审由合并机上的评审服务(`arc-review`)统一调度。你用 `arc submit` 交上去,评审员提 finding,作者逐条回答并推新版本再评;
路由点名的评审员都对一个 head 说了 LGTM,评审服务就给这个确切的 commit 发一张 **pass**。合并机只收 pass 等于 PR 当前 head 的改动(§14)。
英文页:[Review on the pipeline](user-guide/pipeline-review.md)。

### 13.1 交给评审:`arc submit`

`arc submit` 开一个新 PR;`arc submit --pr <N>` 把当前 HEAD 作为已有 PR 的新版本推上去。

- **先跑检查。** 推之前在本机 HEAD 上把 `presubmit.toml` 的检查全部跑一遍。没过的不挡:分支照推,每条检查的结果作为 git note 推在旁边
  (PR 页和看板上看得到),PR 照样进评审,命令列出没过的检查后以 11 退出。
- **安全地推、入队。** 不强推(不覆盖远端有而本地 HEAD 没有的 commit),开或复用 PR,把评审请求排进队,然后退出:

```
[A.R.C.] submit: PR #514 · handed to review (<sha>)
         <url>
         branch <branch> — the review service asks the reviewers the tenant's routes name; their LGTM grants the pass and the merger lands it. A new push is a new version and is reviewed again
```

- **接到 bridge 的会话。** 在接了 arc-bridge 的 agent 会话里跑 `arc submit`,会把这个 PR 登记到当前会话(提示
  `bridge: verdicts for this PR go to <名字> in channel pr:…`),之后的评审结论直接送回这个会话。
- `--branch <名字>`:声明这次是哪个分支,HEAD 不在它上面就拒绝。有别的东西可能挪动 HEAD 时(同一个工作树里的另一个 agent、前面一个长命令)用它。
- `--after <N>`:等 PR #N 落地之后才落这个;可以写多次。

### 13.2 谁来评审:路由

评审员由合并机 `~/.arc/machine.toml` 里这个租户的 `[[tenant.review.route]]` 规则指派(§1.8):

```toml machine.toml#tenant
[[tenant.review.route]]          # 打了 arc-bypass 标签的 PR:dummy 评审员放行
label    = "arc-bypass"
reviewer = "dummy"
name     = "dummy"

[[tenant.review.route]]          # 其余每个 PR:真评审员
reviewer = "react"
name     = "react"
```

- **`reviewer`** 取 `dummy`(对一切说 LGTM)、`basic` 或 `react`。真评审员用合并机上租户 clone 自己的 `.arc/config.toml` 的 `[roles]`;`name` 是回复署的名。
- **一条规则都没有,就没人评审,什么都落不了地。** 不需要人或 AI 评审的单人仓,把所有 PR 路由给 `dummy`。
- **`[tenant.review] gate`**:`all_lgtm`(默认,路由点名的每位评审员都对当前 head 说 LGTM)或 `one_lgtm`(任意一位)。
- **`[tenant.review] max_rounds`**(默认 5):一位评审员最多回几轮不给 LGTM;用完就放行这个 head,不再评。
- **`arc submit --bypass-review`** 给 PR 打上 `arc-bypass` 标签,命中上面那条路由由 `dummy` 放行;它仍然走一遍评审服务,留下记录。

### 13.3 收到 finding,逐条回答

每一轮评审的报告都存在 git 引用 `refs/arc/reports/<cl>` 上。会话接了 arc-bridge 的话,带 finding 的报告会作为消息进
`pr:<owner>/<name>#<n>` 频道,在会话停下时塞进上下文(或叫醒空闲的会话),并附一条填好的 `arc submit --pr <N> --fix-answers -` 命令。

作者对每条 finding 给一个回答:`fixed`(说怎么改的)或 `wontfix`(说为什么留着)。先推修好的代码,成为新的 head,再从标准输入交回答:

```bash
arc submit --pr 514 --fix-answers - <<'EOF'
[
  {"finding": 3, "kind": "fixed", "text": "carried the error typed: #[from] GitError"},
  {"finding": 5, "kind": "wontfix", "text": "the empty string is the wire format the client expects"}
]
EOF
```

- 回答和新 head 作为一次更新一起交;任何一条格式或编号不对,整批拒绝,什么都不发。`--fix-answers` 必须和 `--pr <N>` 一起用。
- 也可以先在本机 `arc local-review`、`arc fix`(§4)修好提交,再 `arc submit --pr <N>` 推新版本。
- 评审服务收到新 head 会重新审:关掉已解决的 finding、重开没修好的、提新的。每次推送都是一个新版本,要重新评。

### 13.4 pass、hold 和放弃

- **pass(`refs/arc/pass/<pr>`)。** 路由点名的评审员都对当前 head 说了 LGTM,评审服务就在这个 commit 上写 `refs/arc/pass/<pr>`。
  合并机只收 pass 等于 PR 当前 head 的改动。
- **不想让它落地:打 `arc-hold` 标签。** 合并机跳过带 `arc-hold` 的 PR,有 pass 也不收;摘掉标签就恢复。
- **放弃一个 PR:`arc submit --abandon "<原因>"`。** 不要在 GitHub 网页上手动关。在那个分支上单独跑(不和别的参数一起用):关闭的意图和原因
  原话记进评审队列,然后由服务关掉 GitHub 上的 PR。

### 13.5 在看板上评审

看板(arc-web)的「Review」页分三栏:等你处理的(以及在等什么)、agent 正在处理的、历史。

- **改动页。** 标题、状态、作者、改动大小、卡在哪、每位评审员的意见和 finding、head 的文件列表、版本历史、风险和爆炸半径、head 的 presubmit 结果。
  按钮:*Open on GitHub*、*Fix again*(打回给作者再修)、*LGTM*。
- **文件和评论。** 同一屏看某个版本的代码和它的 finding,任意两个版本之间看增量 diff。选中代码行、右键加的评论,成为这一轮你的 finding。
  看完逐条裁定已有的 finding(关掉或打回),点 *Send review* 一次发出整轮意见。看板只做评审;落地由合并机做。

---

## 14. 合并:PR 怎么落地

落地全部由合并机(`arc-server`)做,不手动合并。它每次从队列里取一个 pass 等于 head 的 PR,把它合到目标分支最新的 commit 上,跑 `merge.yml`;
合并没有带来新失败,就落地。英文页:[Merge](user-guide/merge-gate.md)(含 `merge.yml` 能写什么的完整规则)。

### 14.1 哪些 PR 能进

- **pass 要对得上。** 只收 `refs/arc/pass/<pr>` 指向的 commit 等于 PR 当前 head 的改动。任何新推送都让旧 pass 作废,要评审员重新 LGTM。
- **`arc-hold`。** 带这个标签的 PR,有 pass 也跳过。
- **`--after <N>`。** `arc submit --after <N>` 交的 PR 等 PR #N 落地后才进队。#N 被关掉、落地的不是这个分支带的那个版本,这个 PR 就不跑门禁,
  并告诉作者原因。

### 14.2 怎么判:base 对比合并后

为了不让目标分支上本来就有的偶发失败挡住所有人,合并机对比两遍:

1. **base 跑一遍。** 取目标分支最新的 commit,读 base 里的 `.github/workflows/merge.yml`,完整跑一遍门禁,记下 base 上已经失败的。
2. **合并后跑一遍。** 把 PR 合进 base,在合并后的树上跑同一套门禁。
3. **只看新失败。** 第二遍没有出现第一遍没有的失败,就通过、落地。
4. **偶发重跑。** 默认(`[tenant] gate.rerun = "once"`)出现新失败时,在同一个合并 commit 上再跑一次,两次都失败才打回。

**合并机永远从 base 读 `merge.yml`,不读 PR 里改过的那份。** PR 改不了自己要过的门禁;改 `merge.yml` 的 PR 按旧规则过,新规则从下一个 PR 起生效。

### 14.3 `merge.yml` 能写什么

`merge.yml` 沿用 GitHub Actions 的文件形状,但由合并机在本机当 shell 步骤跑,不经过 GitHub Actions,所以只认一个子集:

- 触发器只写 `on: workflow_dispatch: {}`。
- 每一步写成 `run:` 命令。合并机不跑第三方 `uses:` action,不展开 `${{ … }}`。
- `if:` 只能用 `runner.os`、`runner.arch`、`env`、`matrix`。
- 有合并机跑不了的步骤时,每个 PR 在这一步都得到 `cannot_say`,并点名是哪一步。

改完门禁,在本机验证某个 job 怎么解析:

```bash
arc workflow .github/workflows/merge.yml --job <job> --list
```

### 14.4 架构规则:门禁里的 `arc archcheck`

在 `merge.yml` 里加一步 `arc archcheck --base <合并基>`,按仓库里的架构规则(`.arc/archcheck.toml`)和豁免表(`.arc/arch_waivers.txt`)
检查合并后的树。违反任何一条规则、豁免只增不减、或配置相对 `--base` 放松了,它就以 7 退出,合并机把它当新失败打回这个 PR。

### 14.5 结果和通知

- **报告。** 每一轮门禁的完整日志写在 `refs/arc/reports/<cl>`。
- **打回。** 开了 arc-bridge 的话,结果进 `pr:<owner>/<name>#<n>` 频道:打回会打断作者的会话,带上失败测试的原始输出。
- **落地。** 发一条 `PR landed as <sha>`,附两样:这个 PR 的结局(落地了、丢弃了、或改动已经在主干里),以及作者机器上还检出着这个分支的
  worktree 和它们的状态(干不干净、有没有进程在用)。合并机从不清理或改动你的 worktree,删不删你定。
- **全员广播。** 每个落到 main 的改动在 `landings` 频道加一行(§12.1)。
- **合并队列页。** 看板的「Merge」页显示排队的 PR、正在跑的一轮、历史尝试,以及门禁每一步的实时日志。

放弃一个 PR 用 `arc submit --abandon "<原因>"`(§13.4),不要在 GitHub 上手动关。

---

## 15. 发布与部署

流水线的最后一段:每晚发预发布版本、按需部署、把某个夜版晋升成正式版。英文页:[Releases and deploys](user-guide/release.md)(含 `delivery.toml` 参考)。

### 15.1 每晚发布

- **配置。** `arc-releaser` 按合并机 `~/.arc/machine.toml` 里每个仓的 `[tenant.release]` 运行,每晚看一次发布分支(`[tenant.release] branch`,默认 `main`)
  最新的 commit。
- **不重复。** 这个 commit 已经发布过就跳过。
- **流程。** 按顺序跑 `.github/workflows/nightly-release.yml` 的步骤;全部通过后打一个 `nightly-<UTC 日期>` 标签(如 `nightly-20261124`)并推上去;
  `publish` 开着(默认开)时,在 GitHub 上建一个 prerelease,上传 workflow 声明的产物。

### 15.2 按需部署

**arc 不会在落地后自动部署**,合并机跑门禁也不等部署、不给部署让路。什么时候部署由你定;想每次落地都部署,在你自己的落地后 job 里调 `arc deploy`。

两种触发方式,做的是同一件事:针对 origin/main 最新的 commit,在一个独立的 systemd scope 里起一个 `arc-deployer`,跑 `.arc/config.toml` 的
`[release]` 指定的 job。

- **看板。** 点「Release」页上的 *Deploy*。
- **命令行。** 在部署机上那个仓的 clone 里跑 `arc deploy`。它记下是谁要的,打印跑这次部署的 systemd 单元和日志文件,然后退出。

起之前先查四样,有一样不满足就拒绝并说明原因:`[release]` 写明了 job;有一个 `[builds.*]` 跑这个 job;这个 job 声明了 `concurrency:` 组;机器上有 `systemd-run`。

### 15.3 记录和通知

- **部署记录。** 每次部署在发布历史里留一条:哪个 commit、谁发起的、每一步的状态和输出、最后的结局。
- **通知。** 部署结束(成功或失败)时,给发起人和这次部署新带上线的每个 PR 的作者发 arc-bridge 私信,并在 `release:<owner>/<name>` 频道加一条上线摘要。
- **发布页。** 看板的「Release」页显示 `.arc/delivery.toml` 声明的发布通道(lane)和部署目标(target)、正在跑的部署走到哪一步、每晚发布的状态。

### 15.4 晋升正式版

某个夜版验证过、要正式发布时,把它晋升成带版本号的正式版(`v<X.Y.Z>`):

```bash
arc-releaser promote --tenant <owner/name> nightly-YYYYMMDD
```

- **发到哪。** 原样发布这个已经发布过的夜版,发到这个仓 `delivery.toml` 里手动二进制 target 指定的仓库,附上那棵树里的
  `packaging/install/install.sh` 和全部产物的 `SHA256SUMS`。它不重新构建。
- **产物要齐。** 晋升前核对 `.arc/delivery.toml` 每条 lane 声明的产物都在;缺任何一个就拒绝发布。

---

## 16. 故障排查

| 症状 | 原因和解法 |
|---|---|
| `missing credential: env var X is not set` | 所选 provider 要的 key 不在环境变量里。这是配置缺失的正常提示,不是程序 bug。在终端里 `export X=…`(或 `source .env`)再跑。 |
| `.arc/config.toml has a [providers] section` | 旧的配置格式。provider 现在全部放在 `~/.tars/config.toml`。删掉 `.arc/config.toml` 里整段 `[providers]`,`[roles]` 只写 tars 里的 provider id(或 `arc init --force` 重新生成)。 |
| `No provider for role "critic_l5"` | `.arc/config.toml` 的 `[roles]` 没写 `critic_l5`,也没有兜底的 `default`。在 `[roles]` 里加 `critic_l5 = "<tars provider id>"`。 |
| Fixer 跑了错的检查,或自己猜怎么构建 | `arc fix` 从仓库根的 `presubmit.toml` 取检查命令;没有这个文件或内容过时,Fixer 只能猜。提交一份写着真实构建和测试命令的 `presubmit.toml`(§1.5)。 |
| `unrecognized subcommand 'auto'`(或 `'verify'`、`'refactor'`) | 这几个子命令已经移除。改用 `arc local-review`,再 `arc fix`:Fixer 每次修完会自动重评,直到 LGTM 或用完 `[review] max_rounds`。 |
| `arc fix` 拒绝在脏工作区跑 | 为了每次修复的 commit 边界清楚、能安全回退,工作区必须和 HEAD 一致:没有未提交的已跟踪改动,也没有没被忽略的未跟踪文件。先 `git commit` 或 `git stash`。 |
| finding 质量低、泛泛而谈 | 担任 critic 的模型不够强,会漏报或只给浅层噪音。弱 critic 的零告警不代表代码没问题。在 `~/.tars/config.toml` 和 `[roles]` 里给 critic 换一个推理更强的 provider。 |

## 17. 代码规范规则(示例,默认关闭)

arc 不是代码风格检查工具。代码格式和常规编码风格是传统工具链(`ruff`、`eslint`、`gofmt`、`clippy`)的事:它们
零推理成本、结果确定,应该放在你常规的 CI 里跑。arc 只把 LLM 评审花在确定性工具管不到的地方:语义级危害(L4,§5–§7)
和架构结构腐烂(L5,§8)。

内置的代码规范规则是**范本**:向你展示规范类规则用 rubric YAML 怎么写。各团队的规范不同,这些规则只是你写自己规则
的起点,不建议直接打开 —— 在 linter 之上再叠一层命名风格的提醒,只会制造评审噪音。所以下面这些内置规范规则都标着
`status: deprecated`,不在默认评审集合里。

### 17.1 怎么启用

- **配置开关不管用。** `<repo>/.arc/config.toml` 的 `[review]` 里 `enable`、`disable`、`experimental` 还能解析,
  但运行时已经不读。本地评审只跑 `status: stable` 的规则,所以 `deprecated` 规则不会执行。
- **复制过去再启用。** 想用其中某条,把它的定义复制到你仓库的 `rubrics/*.yaml` 里,把状态改成 `status: stable`(§10)。

### 17.2 内置示例(改前 X → 改后 Y)

每条规则都带一个明确的机械改法,可以直接当你写自定义规则的模板。

**`rust_best_practices::migration-affix-in-name`** —— `_core` / `_v2` / `_new` 这类词缀原本用来和旧实现区分,
旧实现删掉后词缀还留着,名字就开始误导人。

```rust
// X — 原来用来区分的 pyo3 `lookup` 早已移走,`_core` 已经没有意义
pub fn lookup_core(conn: &Connection, k: &str) -> …
pub fn store_core(conn: &Connection, …) -> …

// Y — 模块路径(cache::lookup)本身就是命名空间
pub fn lookup(conn: &Connection, k: &str) -> …
pub fn store(conn: &Connection, …) -> …
```

**`rust_best_practices::unitless-primitive-quantity`** —— 带单位或业务含义的数值跨 API 传递时用裸整数,类型上
没有约束。

```rust
// X — `now` 是秒还是毫秒?`ttl_days` 很容易和普通计数传反
pub fn lookup(conn: &Connection, key: &str, ttl_days: i64, now: i64) -> Option<Hit>

// Y — 让类型说出它是什么
/// Unix timestamp, seconds.
pub type UnixSecs = i64;
pub fn lookup(conn: &Connection, key: &str, ttl_days: i64, now: UnixSecs) -> Option<Hit>
```

**`llm_generated_code_smells::obscure-import-or-alias`** —— 导入别名太短或太晦涩,在调用点看不出它是什么。

```python
# X
from collections import Counter as _C
summary = ", ".join(f"{n} {t}" for t, n in _C(tags).items())

# Y
from collections import Counter
summary = ", ".join(f"{n} {t}" for t, n in Counter(tags).items())
```

**`llm_generated_code_smells::log-string-vs-error-object`** —— 处理异常时把错误对象手动转成字符串记日志,丢了
日志框架本来会带上的调用栈。

```python
# X — reason=str(e) 丢掉了完整的异常调用栈
except OSError as e:
    log.warning("write_failed", path=path, reason=str(e))

# Y — 用日志器记录异常的接口,保留成因和调用栈
except OSError:
    log.exception("write_failed", path=path)
```

**`llm_generated_code_smells::log-event-name-proliferation`** —— 同一个操作只因失败在不同步骤,就拆出好几个日志
事件名,日志命名空间越来越乱。

```python
# X — 每个失败分支各起一个事件名
except AgentError as e:  log.warning("fix_step1_failed", reason=str(e))
except ParseError as e:  log.warning("fix_step2_failed", reason=str(e))

# Y — 一个事件名,用结构化字段区分异常类型
except (AgentError, ParseError) as e:
    log.exception("fix_failed", error_type=type(e).__name__)
```

**`llm_generated_code_smells::duplicate-error-handler-shell`** —— 在支持按类型分发异常的语言里,给共用同一套
兜底逻辑的几步操作各写一个 `try`。

```python
# X
try:    output = agent.run(...)
except AgentError as e:
    log.warning("agent_failed", reason=str(e)); return file, {}
try:    replies = parse(output)
except ParseError as e:
    log.warning("parse_failed", reason=str(e)); return file, {}

# Y — 合成一个 try,按异常类型分支,复用兜底
try:
    output = agent.run(...)
    replies = parse(output)
except AgentError as e:
    log.warning("agent_failed", reason=str(e)); return file, {}
except ParseError as e:
    log.warning("parse_failed", reason=str(e)); return file, {}
```

**`llm_generated_code_smells::branch-redundancy-default-leak`** —— 同一个默认值在好几个分支里重复赋值,掩盖了
「这是默认状态」,还平添分支。

```python
# X — 默认值散在多个分支里
if post_fix_run_id:
    rec = storage.get_run(post_fix_run_id)
    if rec is not None:  threads, target = _deserialize(rec.threads), post_fix_run_id
    else:                threads, target = threads, run_id
else:                    threads, target = threads, run_id

# Y — 先给默认值,只在条件满足时覆盖
threads, target = threads, run_id
if post_fix_run_id:
    rec = storage.get_run(post_fix_run_id)
    if rec is not None:
        threads, target = _deserialize(rec.threads), post_fix_run_id
```

### 17.3 写你团队自己的规范

照上面的样子,在仓库的 `rubrics/` 里加一条 YAML,写全这几样,它就会在常规评审里跑:

- `name`,加一行 `why` 说明意图;
- 一对正反例 `example_bad` / `example_good`;
- 作为评审指令的 `description`,以及 `status: stable`(写法见 §10)。

---

## 另见

- `usage.md` —— 详尽操作手册(逐个 flag、`--json`、CI)
- `concepts.md` —— 辩论模型、层、rubric 系统
- `finding-entity-model.md` —— finding 的呈现与筛选
- `crates/review/types/README.md` —— finding 模型
- [`README.md`](../README.md) —— 快速上手
