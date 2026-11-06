# Fork 说明 · Redsob/dsh-purge

## 来源与署名

本仓库 fork 自 [HunYiSage/dsh-purge](https://github.com/HunYiSage/dsh-purge)（Apache-2.0）。

按上游要求保留署名：`LICENSE`、`NOTICE` 原样保留；借用的代码、思路与提示词均标明来源。原版禁止倒卖，二开必须署名 —— 本 fork 遵守。

**改动由 Redsob 自行维护，不向上游提交，也不依赖上游更新。**

## 2026-11-06 · 同步到 1.1.92 + 全量换掉上游仓库地址

上游把仓库名从 `YuJunZhiXue/dsh-purge` 改成了 `HunYiSage/dsh-purge`，1.1.92 的 `lib/update.js` 里 `REPO` 已经是新名字。本 fork 做了一次彻底对齐：

1. **同步 1.1.92**：fork 自身的 22 个文件改动（`lib/core.js` 的 0.2.2-rc.1 漂移补丁、`lib/index.js`、`lib/update.js`、`client.js`、`fork-patches/`、`FORK_NOTES.md`、`.gitattributes`）以 3-way patch 打到 1.1.92 树上；唯一冲突是 `lib/update.js` 的 `REPO` 常量，取 fork 侧。同时吃进 1.1.92 新增的 23 个 `skills/redteam/*.md`。
2. **换地址（行为相关的全部改掉）**：
   - `lib/update.js` → `const REPO = "Redsob/dsh-purge"`（面板版本列表、zip 下载、head sha、tag 列表全走这里）
   - `lib/redteam/ui.js:362` → `return 'Redsob/dsh-purge'`（`githubRepoOf` 兜底）
   - `client.js` 两处 `welcome.repo` → `https://github.com/Redsob/dsh-purge`
   - `package.json` → `repository` / `homepage` / `bugs` / `dsh.install.tarball` / `.zip` / `.git` 全指向 Redsob
   - `.github/workflows/release.yml` → 发布守卫与回显地址
3. **保留不改（署名义务）**：`LICENSE`、`NOTICE`、`LICENSE-COMMERCIAL.md`、`release-notes.md` 以及三份 README 正文里的上游地址 —— Apache-2.0 要求保留版权与来源。三份 README 只在顶部加了 fork 横幅，正文照旧。
4. `lib/default-prompt-inject.en.md` / `.zh.md` 随 1.1.92 一起删掉：上游已移除，且没有任何代码引用（`scripts/embed-default-prompt.mjs` 只读 `lib/default-prompt-inject.md`）。

**同步方式（可复现）**：fork 与上游是两套不相干的提交历史（`merge-base` 为空，`git merge` 会报 `refusing to merge unrelated histories`），所以用增量补丁而不是 merge：

```bash
git diff --binary v1.1.90 master --output=fork-delta.patch
git fetch upstream ff4431e1ba5b7bfb1fbb8418f34dca4f4b739e5a   # 上游 v1.1.90
git checkout -B sync-1.1.92 upstream/master
git apply -3 fork-delta.patch                                  # 只有 lib/update.js 冲突
git checkout --theirs -- lib/update.js                         # 取 fork 侧 REPO
```

**回滚到上游通道**：把 `lib/update.js` 的 `REPO` 改回 `HunYiSage/dsh-purge`，再还原 `package.json` 的 `repository` / `homepage` / `bugs` / `dsh.install` 即可；其余都是纯 fork 补丁。

## 本次修复：应用后「清洗没有写进全部宿主，已取消重启」

### 现象

本机同时存在多份 dsh 安装时，勾选「放行 hooks 的 deny / ask」后点「应用」，恒定报
`失败：清洗没有写进全部宿主，已取消重启`。

### 根因

`lib/core.js` 的 `ensureRestartReady()` 用 `enumeratePatchAiBases({ discover: true })` 把本机
**所有** dsh 安装扫进 `allHosts`，再由 `allPatchHostsWritten()` 要求每一份都带清洗标记。

而 `discover` 会扫到旁边根本没在用的、甚至本插件明确不支持的版本。上游 README 写明
「不支持 dsh 0.2.1-rc.3 / rc.4 及更新」——本机那份 `0.2.2-rc.1` 永远打不上标记，于是
判定恒为 false，当前正在用的宿主也被一起拦住。

更糟的是 `ensureRestartReady()` 原本已经算出了 `hosts` 清单，`lib/index.js` 的重启接口
只取 `error` / `pending`，把清单丢掉，所以界面上看不出是哪一份出的问题。

### 改法

1. `lib/core.js` 新增导出 `evaluateRestartHosts(hosts, aiBase)`：
   - **只把当前宿主 `aiBase` 当作阻断项**；
   - 其余宿主未写进标记，从「阻断」降级为告警 `unappliedHosts`；
   - 返回 `missing` 完整路径清单。
2. `ensureRestartReady()` 末尾改用它；失败时报错文本直接列出未写进的宿主路径。
3. `lib/index.js` 重启接口把 `hosts` / `missing` 一并回给调用方。

### 边界（不是适配新版）

这个修复**没有**让插件支持 `0.2.2-rc.1`。它解决的是「旁边躺着一份不支持的宿主，
把当前宿主也拖下水」。如果当前正在运行的宿主本身就是不受支持的版本，补丁依旧打不上，
此时仍会失败 —— 但报错会指出具体路径，而不是一句没头没尾的「没有写进全部宿主」。

## 本地验证

```sh
node --check lib/core.js
node --check lib/index.js

node --input-type=module -e '
import { evaluateRestartHosts } from "./lib/core.js";
const hosts = [
  { aiBase: "C:\\host-a", hostWritten: true },
  { aiBase: "D:\\host-b", hostWritten: false },
];
console.log(evaluateRestartHosts(hosts, "C:\\host-a")); // ok: true, missing: [host-b]
console.log(evaluateRestartHosts(hosts, "D:\\host-b")); // ok: false
'
```

## 装回本机

```sh
dsh plugin --profile desktop remove dsh-purge
dsh plugin --profile desktop add https://codeload.github.com/Redsob/dsh-purge/tar.gz/refs/heads/master
```

完全退出宿主（托盘也要退）→ 重开 → 会话标题旁 `dsh-purge` →「清洗」→「应用」。
Web / 桌面两端分别安装、分别应用。

## 第六次修复：#82 桌面专属补丁（2026-11-06 08:10）

### 现象与真因

08:07 宿主重启并跑完「应用」后，状态页还剩 1 个漂移。这次直接读运行中面板的接口
`GET http://127.0.0.1:<port>/dsh-purge/status`（端口由宿主进程监听），拿到：

```
surface = desktop | ai_base = D:\deepseekh\...\@deepseek-ai | host_version = 0.2.2-rc.1
patches_drifted = 1 | patch_status["82"] = "drifted" | patches_total = 70
```

**之前两轮的差额都是它**：用户第一次报「7 漂移」= 桌面 6 条 + #82；清完 6 条后报「1 漂移」= #82。
我在独立 node 里跑 `patchStatus` 只扫到 62 条，因为 `patchAppliesHere(p, surface)` 默认
`detectSurface()` 拿不到宿主进程的环境，`#82` 的 `surfaces:["desktop"]` 被判 `na`；
它的 `file: "desktop-shell"` → `officialShellMain()` 也需要 `desktop_exe` 才能解析出
`D:\deepseekh\resources\app\lib\main.js`，独立进程里返回 `null`。

> **教训**：验收状态页必须读运行时接口，不能用独立进程的复算代替。
> 独立进程的 surface / env 不同，会静默漏掉桌面专属补丁。

### #82 是什么、为什么值得修

`DESKTOP_SHELL_PROFILE_FALLBACK`：双击 `DeepSeek Harness.exe` 从 explorer 启动时不继承
`DSH_PROFILE`，host 子进程会报 `cannot determine the boot profile`，cordis 不加载 →
**dsh-purge 插件没 activate → 注入全断**。这不是状态页装饰，是启动链路兜底。

新版 `main.js` 里 import 行逐字还在，但紧跟的 `//#region` 从
`../../packages/util/home-paths/lib/index.js` 换成了
`../../node_modules/.pnpm/mime@4.1.1/.../other.js` —— 官方两行连写 pattern 整体失配。
按「单行唯一锚点」原则改用那行 import（实测全文件命中 1 次），插入官方 marker +
`if (!process.env.DSH_PROFILE) process.env.DSH_PROFILE = "desktop"`。

### 验证与落地

- 离线：`drifted → pending → applied`，`main.js` 整文件 `node --check` 通过
- 运行时接口（改后）：**`drifted 0 / pending 0 / ready 70/70 / skipped 3`**
  （非 applied 只剩 #54 / #71 / #80 三条正常跳过）
- 备份 `main.js.bak_redsob_patch82_20261106_081000`；`core.js` 两份均追加 #82 规则、语法通过
- `fork-patches/` 两个脚本与 `patch_cases.json` 同步支持 #82；落宿主脚本加了「替换体已存在即跳过」
  的幂等判据（#82 的 replace 以 pattern 开头，否则会重复插入）

运行时宿主进程仍加载旧 `core.js`，但 `patchApplied` 用 marker 判据，所以**不重启也已生效**；
下次重启会带上新增的 #82 replacement，重放路径一致。

## 第五次修复：0.2.2-rc.1 剩余 6 条漂移全清（2026-11-06 08:00）

### 现象与口径

宿主重启后状态页仍显示漂移。用插件自己的 `patchStatus` / `tallyDisplayPatches` 复算，
桌面宿主（`D:\deepseekh\...\@deepseek-ai`，dsh 0.2.2-rc.1）的**真实口径**是
`applied 54 / drifted 6 / skipped 2 / total 62`：

- `skipped 2` = `#71 LIANGSHEN_IDENTITY_LINE`（`missing_file`）+ `#80 MINIMAL_OFFICIAL_TOOLSET`（`skipped`）。
  `tallyPatches` 把 `na` 以外的所有非 applied/pending/unmatched/drifted 状态一律归到「跳过」。
- ~~面板报的「7 漂移」比实测多 1，可能来自分组行或另一份宿主的瞬时状态。~~
  **订正（08:10，见第六节）**：这句猜错了。第 7 个是 `#82 DESKTOP_SHELL_PROFILE_FALLBACK`——
  它带 `surfaces:["desktop"]`，且 `desktop-shell` 依赖宿主进程的 `desktop_exe` 环境变量才能定位，
  独立 node 进程里 `patchAppliesHere` 返回 false / `targetFiles` 返回 null，所以我的复算只扫到 62 条、
  漏了它。运行时 `/dsh-purge/status` 扫的是 86 条。
- **这些不是重启后的回归**：#40 / #74 均为 `applied`，`hostCleanMarkersPresent=true`，
  `evaluateRestartHosts.ok=true`。`prompt-inject.md` 重启后仍是 29,223 字符、与草案逐字相同，
  `override-state.json` 为 `customized:true` —— 真实验收通过，启动/应用不会覆盖。

### 六条逐条修法

| # | 名称 | 失配类型 | 处理 |
|---|---|---|---|
| 14 | `ESCALATION_GRANT_UNCONDITIONAL` | 新版 `displayReason` 改成函数调用 | 追加 pattern，替换体沿用官方逻辑并保留新版函数 |
| 17 | `FS_OBSERVATION_INTENT_FREE` | `editIntent` 改调 `requirePresent` | 追加单条 pattern，替换为无条件放行 |
| 54 | `DELIVERABLE_DO_NOT` | 官方已删除禁句，`Static Web guidance` 锚点也没了 | **条件豁免**：文件里没有 `Do not call present just to list` → 返回 `skipped`。不是伪造 `applied`；官方若把禁句加回来，条件不成立会重新报 drifted |
| 60 | `OFFICIAL_RUN_CODE_APPROVAL_NEUTRAL` | **纯组件搬家**：四句文案逐字没变，从 `dsh-tools` 移到 `dsh-tool-executor-ptc` | 只改 `targetFiles` 的 key 映射，不动任何 pattern |
| 62 | `OFFICIAL_TOOL_ASK_FAILOPEN` | 组件搬家 + `undefined`→`void 0` 写法变化 | 新布局指向 `dsh-tools/lib/pipeline.js`；追加 1 条新 pattern，并补落官方 [8]/[9] 两个 fail-open 分支 |
| 67 | `AGENT_LOOP_MESSAGES_GUARD` | 两行被包进 `try`（缩进 4→5 层），旧 pattern 尾部空格也对不上 | 追加 5 层缩进版 pattern，替换为 `?.length ?? 0` |

`targetFiles` 里新增 `newToolsLayout` 布尔量（依据 `dsh-tools/lib/pipeline.js` 是否存在）。
新布局下 `dsh-tools` 故意返回空数组（`missing` 不计漂移），`dsh-tools-types` 改指 pipeline.js，
`dsh-tools-ptc` 改指 ptc 包两个文件；**旧布局三处映射原样保留**，老宿主不受影响。
这三个 key 只被 #60 / #62 引用，改动不外溢。

### 结果（真跑）

```
patchStatus : applied 67 / na 16 / skipped 2 / missing_file 1 / pending 0 / drifted 0
面板口径   : applied 59 / skipped 3 / drifted 0 / pending 0 / ready 62/62
注入链路   : #40 applied · #74 applied · hostCleanMarkersPresent true · 重启判定 ok=true
```

剩下 3 条不是漂移，是**正常跳过**：#54（官方已删禁句）、#71（梁神预设包没装）、
#80（极简工具表本来就没改过）。跳过数从 2 变 3 是有意的：#54 从「假漂移」归位成「不适用」。

六份被改的宿主文件 `node --check` 全过；`lib/core.js` 两份（fork + 本机）语法全过。
宿主文件备份后缀 `.bak_redsob_drift_20261106_080035` / `.bak_redsob_drift62_20261106_080101`。

### 可重放（升级宿主或插件被覆盖后）

```
cd D:/ai/code/dsh-purge
python fork-patches/apply_drift_fixes.py     # 改两份 core.js，幂等（sentinel 判重）
python fork-patches/apply_drift_to_host.py   # 落补丁到宿主，命中即替换、自带备份
node   fork-patches/verify_patches.mjs       # 验证 #14/#17/#67，幂等
```

`fork-patches/rules/` 存全部 pattern / replace 与官方规则快照。脚本锚定 **1.1.90 + 0.2.2-rc.1**；
日后合并上游或换宿主，若锚点失配会直接 assert 停下，不会静默写坏。

### 边界

- 只针对 `0.2.2-rc.1`。上游 v1.1.91 / 1.1.92 的 10 次提交没碰 `core.js` / `ALL_PATCHES`，
  升上去仍会把本 fork 的改动整片覆盖。
- #54 是**条件豁免**，不声称补丁已打上；若哪天需要真正的交付物提示词改动，得按新版源码另写。
- 改完建议完全退出 dsh 宿主再重开，让新 `core.js` 加载；本次状态复验已在当前进程外完成。

## 第四次修复：0.2.2-rc.1 下 #74 注入钩子没打上（2026-11-06）

**为什么这条最关键**：`lib/index.js:976` 会设
`globalThis.__dshPurgePrepareAssemble = prepareAssemble`，其作用是在每次 pre-step
重挂 assemble guard。**宿主里引用该钩子的文件原本是 0 个** —— #74 漂移导致钩子
定义了却没人调用。按插件源码注释，后果是「第二轮起 inject 走原生 assemble →
宿主按 token 预算裁剪 → 用户只看到部分提示词」。我们 29,223 字符的完整注入词
尤其容易被裁，所以这不是可选项，是搬家的最后一环。

**根因**：#74 原 pattern 是两行连写

```js
const claimed = this.inbox.claim(target, position.turn);
const assembly = await this.loopCtx.systemPrompt.assemble(assembleContextFor(this, signal));
```

0.2.2-rc.1 在两者之间插入了 `const selection = this.model.current()`、
`const toolSet = await this.loopCtx.tools.resolve(...)`，且 assemble 参数改成
对象展开形式 → 原 pattern 失配。

**改法**：追加一条**单行** replacement，只锚定
`\t\tconst claimed = this.inbox.claim(target, position.turn);\n`，
在其后插入原有的钩子调用（位置与旧补丁一致，语义不变）。单行锚点在该文件中
实测唯一，比整段匹配更抗后续改版。

**验证**：命中 1 次 / `filePatchOutcome` 原文 `pending`、替换后 `applied` /
整文件 `node --check` OK / 实跑 `patchStatus` 漂移 **7 → 6**、`#74 = applied`。
宿主 `dsh-agent-loop/lib/index.js` 已写入（备份 `.bak_redsob_patch74_20261106_074504`）。

## 第三次修复：应用成功后进度条卡在 7/8（2026-11-06，纯 UI）

**现象**：应用无报错、`0.1.5 兼容 1/1`、`60/70`、宿主进程已重启，
但 8 步进度条最后一格「完成」不亮，橙色线停在 7→8 之间（约 93%）。

**根因**：`client.js` 里 `jobIdx` 会把 `stage === "restart"` 映射成 `"done"`
来算索引，但 `ApplyFlow` 的末格判定写的是
`done = idx > i || (stage === "done" && !failed)` —— **只认 done，不认 restart**；
`pct` 同理只在 `stage === "done"` 时给 `jobSteps.length`（100%），
restart 阶段算 `(7 + 0.45) / 8 ≈ 93%`。
后端 `lib/index.js:2359` 的 `endApply({ stage: "done" })` 确实执行了，
但重启后前端拿到的 `apply_progress` 停在 `restart`，两者对不上。

**改法**（`client.js`，两处）：
- 新增 `finished = !failed && (stage === "done" || stage === "restart")`，
  末格判定改为 `done = idx > i || finished`；
- `pct` 的 100% 条件同步放行 `restart`，并加 `!job.error`，
  避免失败时误显 100%。

**验证**（纯逻辑真跑）：`seed → 81% / 末格不亮`；`restart → 100% / 末格亮`；
`done → 100%`；`restart + error → 末格不亮`。`node --check` 两份文件通过。

**影响**：只改前端显示，不动任何清洗逻辑。**重启 dsh 宿主后加载新 `client.js` 才生效**。

## 第二次修复：0.2.2-rc.1 下 #40 漂移导致清洗标记缺失（2026-11-06）

**现象**：在宿主 `D:\deepseekh\...\@deepseek-ai`（dsh `0.2.2-rc.1`）点「应用」，
报 `当前宿主未写进清洗标记，已取消重启；未写进的宿主：D:\deepseekh\...`。
注意这已经不是第一次修的那个「旁边宿主拖累」问题 —— 这次挡的是**当前正在用的宿主**。

**判定链**：

```
ensureRestartReady → evaluateRestartHosts → hostCleanMarkersPresent(aiBase)
  → hostPromptKeepsInject(dsh-system-prompt/lib/index.js)
```

`lib/host-clean.js` 要求 `identity` 标记（`[dsh-purge] identity stripped`）**且**
`inject` 三选一标记（如 `[dsh-purge] complete prompt keeps inject`）。
实测当前宿主只有 identity，inject 三个全无；兜底分支又因为新版源码里
`sections: completeSection === void 0 ? transformed.sections : [completeSection]`
（官方丢弃 waterfall inject 的那处）仍在而返回 false。

**根因**：`ALL_PATCHES` 的 **#40 `COMPLETE_PROMPT_KEEP_INJECT`** 原有 7 条
pattern 全针对 0.2.0 / 0.2.1-rc.2。0.2.2-rc.1 的 `assemble` 早退分支和最终
return 都新增了 `tools` 字段，旧正则/字符串一条都命中不了 → `drifted`
→ 补丁没打上 → inject 标记没写进宿主文件 → 重启判定恒失败。

**改法**：给 #40 追加第 8 条 `replacement`（放在数组首位优先匹配）：
- `pattern`：0.2.2-rc.1 原文片段**精确字符串**（含 `tools` 早退分支）
- `replace`：沿用官方 replacement[0] 的注入保留逻辑，两处补上 `tools`，
  保留 `[dsh-purge] complete prompt keeps inject` 标记

**验证**（`D:/ai/_sable/tmp/verify_patch40.mjs`，全部真跑）：

| 项 | 结果 |
|---|---|
| 原文精确命中 | true |
| 替换后 `hostPromptKeepsInject` | **true** |
| `filePatchOutcome` 原文 / 替换后 | `pending` / `applied` |
| 替换后整文件 `node --check` | OK |
| 实跑 `patchStatus` | 漂移 8 → **7**，`#40 = applied` |
| `hostCleanMarkersPresent(当前宿主)` | **true** |
| `evaluateRestartHosts` | `ok: true`，旁边宿主只列 `missing` 不阻断 |

**边界**：其余 7 条 drifted（`ESCALATION_GRANT_UNCONDITIONAL`、
`FS_OBSERVATION_INTENT_FREE`、`DELIVERABLE_DO_NOT`、两条 `OFFICIAL_*`、
`AGENT_LOOP_MESSAGES_GUARD`、`ASSEMBLE_BEFORE_PRESTEP`）本次**未适配**。
它们不阻断重启，但对应的功能在 0.2.2-rc.1 上仍不生效。要全量适配需逐条对比新版源码。

**落地**：本机插件 `lib/core.js` 已同步；宿主 `dsh-system-prompt/lib/index.js`
已直接写入补丁（备份 `.bak_redsob_patch40_20261106_073012`）。
点「应用」前建议完全退出宿主重开以加载新插件代码；直接点也能过，因为标记已在文件里。

## 面板上的「哪个版本是咱们的」（2026-11-06）

**改动前**：`lib/update.js:12` 的 `REPO` 写死 `HunYiSage/dsh-purge`，
`listGithubTags()`（`:629`）拉的是上游 tags，所以面板下拉里
`v1.1.85` ~ `v1.1.92` **全是上游官方版，没有一个是本 fork**。

顶部「本机 v1.1.90 · 当前」也不是按内容认的：`markCurrent()`（`:601`）只拿
`package.json` 的版本号去列表里做字符串匹配。本 fork 基于 1.1.90 且没改版本号，
于是被误标成上游的 `v1.1.90`。**屏幕上两个 v1.1.90，一个是咱们的，一个不是。**

危险点在「切换到此版本」：`applyUpdate()` 会先 `rm -rf lib/`、`bin/`、`docs/`，
再从 codeload 的 zip 整片覆盖（`:909`）。点上游任何一个版本，
`12af0a1` 的 `evaluateRestartHosts` 当场消失。
`autoUpdateIfNeeded()`（`:1128`）明确是 `manual-only`，启动不会自动升 —— **只要不手点就安全**。

上游 `v1.1.91` / `v1.1.92` 共 10 次提交（仓库迁移、文档、随包技能库），
`lib/core.js` / `lib/index.js` 一次都没碰，那个 bug 仍在；升上去对本修复零收益。

**本次改动**：`REPO` → `Redsob/dsh-purge`。此后面板的版本列表、zip 下载都走自有仓库；
点「切换到此版本」只会拉到本 fork 的代码，不会抹掉修复。
同时打 tag **`v1.1.90-redsob.1`** 作为可辨识身份（基于 1.1.90 + 本 fork 全部改动）。

安装指定版本：

```sh
dsh plugin --profile desktop add https://codeload.github.com/Redsob/dsh-purge/tar.gz/refs/tags/v1.1.90-redsob.1
```

**回滚到上游通道**：把 `lib/update.js:12` 改回 `HunYiSage/dsh-purge`，
再 `git checkout 12af0a1 -- lib/update.js` 亦可。改回后不要点「切换到此版本」。

## 若本仓库转为私有（2026-11-06 预案，尚未执行）

GitHub 不允许「公开仓库的 fork」直接转私有（PATCH `private=true` → 422
`Public forks can't be made private`）。要走网页 **Leave fork network** 脱离父仓库，
或删掉 fork 后用 bare clone 重建为同名私有仓库。本地完整镜像已备在
`D:/ai/_sable/github-mirrors/dsh-purge.git`（49 commits）。

**私有化会打断两处无认证链路**，需要在切换前处理：

1. **面板下拉变空**：`lib/update.js` 的 `fetchJson()` / `fetchRes()` 不带
   `Authorization`，访问 `api.github.com` / `raw.githubusercontent.com` /
   `codeload.github.com` 的私有仓库一律 404。`listRemoteVersions()` 拿不到
   tags 和 master，`ensureRunningVersion()` 只会插一条本机记录 —— 不会崩，
   但版本列表没了。
2. **`dsh plugin add` 失败**：`codeload.github.com/Redsob/dsh-purge/tar.gz/...`
   对未授权私有仓库同样 404。改用本地路径，pnpm 支持 `file:`：
   ```sh
   dsh plugin --profile desktop add file:D:/ai/code/dsh-purge
   ```

**预案 A（推荐，未实施）**：给 `update.js` 的 GitHub 请求统一加
`Authorization: Bearer <token>`，token 依次取环境变量 `GITHUB_TOKEN` / `GH_TOKEN`、
或 `~/.dsh/dsh-purge/github-token`；未配置时不加头，保持现有行为。
**预案 B**：保持这个 fork 公开（它本身是公开项目的镜像，无敏感内容），
只把自建仓库设为私有。

回滚见上一节；本节的改动与本 fork 的功能修复无关，可独立取舍。
