# Fork 说明 · Redsob/dsh-purge

## 来源与署名

本仓库 fork 自 [HunYiSage/dsh-purge](https://github.com/HunYiSage/dsh-purge)（Apache-2.0）。

按上游要求保留署名：`LICENSE`、`NOTICE` 原样保留；借用的代码、思路与提示词均标明来源。原版禁止倒卖，二开必须署名 —— 本 fork 遵守。

**改动由 Redsob 自行维护，不向上游提交，也不依赖上游更新。**

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
