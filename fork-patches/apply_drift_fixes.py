"""[Redsob fork] dsh 0.2.2-rc.1 全量漂移适配，可重放。

- #14/#17/#62/#67：追加新版 replacement（保留全部旧 pattern）
- #60：原文逐字未变，只是组件搬家 -> targetFiles 按布局择一改 file key 映射
- #54：禁句已被官方移除、效果天然达成 -> 条件豁免为 skipped（不是伪造 applied）
同时写入 fork 源码与本机已装插件，原子写 + 备份。
"""
import json
import os
import shutil
import datetime
from pathlib import Path

T = Path(__file__).resolve().parent / "rules"
TARGETS = [
    Path(r"D:/ai/code/dsh-purge/lib/core.js"),
    Path(r"C:/Users/sobo/.dsh/profiles/desktop/node_modules/dsh-purge/lib/core.js"),
]
TS = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
SENTINEL = "[Redsob fork] 0.2.2-rc.1 全量漂移适配"

# ---------- 1. 追加的 4 条新版 replacement ----------
NEW_RULES = {}
for pid in (14, 17, 62, 67, 82):
    NEW_RULES[pid] = {
        "pattern": (T / f"patch{pid}_022rc1_pattern.txt").read_text(encoding="utf-8", newline=""),
        "replace": (T / f"patch{pid}_022rc1_replace.txt").read_text(encoding="utf-8", newline=""),
    }

# ---------- 2. targetFiles 布局择一 ----------
OLD_LAYOUT = '''  const root = packageRootFromAiBase(aiBase);
  const files = {'''
NEW_LAYOUT = '''  // [Redsob fork] 0.2.2-rc.1 起 dsh-tools 内部拆包：#62 的 serviceAsk 移到
  // lib/pipeline.js，#60 的 run_code 文案移到 dsh-tool-executor-ptc。
  // 这三个 key 只被 #60/#62 引用，按布局择一即可；旧宿主保持原映射不动。
  const newToolsLayout = fs.existsSync(path.join(aiBase, "dsh-tools", "lib", "pipeline.js"));
  const root = packageRootFromAiBase(aiBase);
  const files = {'''

OLD_KEYS = '''    "dsh-tools": allExisting([
      ...nestedPkg(aiBase, "dsh-tools", "lib", "index.js"),
    ]),
    "dsh-tools-types": allExisting([
      ...nestedPkg(aiBase, "dsh-tools", "lib", "types", "index.js"),
    ]),
    "dsh-tools-ptc": allExisting([
      ...nestedPkg(aiBase, "dsh-tools", "lib", "types", "ptc.js"),
    ]),'''
NEW_KEYS = '''    // [Redsob fork] 新布局下这个 key 故意返回空：#60/#62 的原文都已搬走，
    // 让 index.js 参与判定只会虚报 drifted（missing 不计入漂移）。
    "dsh-tools": newToolsLayout ? [] : allExisting([
      ...nestedPkg(aiBase, "dsh-tools", "lib", "index.js"),
    ]),
    "dsh-tools-types": newToolsLayout ? allExisting([
      ...nestedPkg(aiBase, "dsh-tools", "lib", "pipeline.js"),
    ]) : allExisting([
      ...nestedPkg(aiBase, "dsh-tools", "lib", "types", "index.js"),
    ]),
    "dsh-tools-ptc": newToolsLayout ? allExisting([
      ...nestedPkg(aiBase, "dsh-tool-executor-ptc", "lib", "index.js"),
      ...nestedPkg(aiBase, "dsh-tool-executor-ptc", "lib", "types", "ptc.js"),
    ]) : allExisting([
      ...nestedPkg(aiBase, "dsh-tools", "lib", "types", "ptc.js"),
    ]),'''

# ---------- 3. #54 条件豁免 ----------
OLD_OUTCOME = '''  if (isSelfMarkedPatch(patch)) return "skipped";
  return "drifted";
}'''
NEW_OUTCOME = '''  if (isSelfMarkedPatch(patch)) return "skipped";
  // [Redsob fork] #54 的禁句在 0.2.2-rc.1 已由官方移除，效果天然达成：
  // 文件里找不到禁句就说明不需要补丁，标 skipped 而不是虚报 drifted。
  // 若官方哪天把禁句加回来，条件不成立，会重新报 drifted 提醒适配。
  if (patch.id === 54 && !text.includes("Do not call present just to list")) return "skipped";
  return "drifted";
}'''

for path in TARGETS:
    text = path.read_text(encoding="utf-8", newline="")
    if SENTINEL in text:
        print("已应用过，跳过:", path)
        continue
    nl = "\r\n" if "\r\n" in text else "\n"
    # fork 是 CRLF、本机是 LF，锚点必须按目标文件的换行符归一
    old_layout, new_layout = OLD_LAYOUT.replace("\n", nl), NEW_LAYOUT.replace("\n", nl)
    old_keys, new_keys = OLD_KEYS.replace("\n", nl), NEW_KEYS.replace("\n", nl)
    old_outcome, new_outcome = OLD_OUTCOME.replace("\n", nl), NEW_OUTCOME.replace("\n", nl)
    assert text.count(old_layout) == 1, f"布局锚点不唯一: {path}"
    assert text.count(old_keys) == 1, f"key 块不唯一: {path}"
    assert text.count(old_outcome) == 1, f"outcome 锚点不唯一: {path}"
    text = (text.replace(old_layout, new_layout)
                .replace(old_keys, new_keys)
                .replace(old_outcome, new_outcome))

    # 逐条追加 replacement
    lines = text.splitlines(keepends=True)
    for pid, rule in NEW_RULES.items():
        anchor = f"id: {pid},"
        idx = next(i for i, l in enumerate(lines) if anchor in l)
        j = next(i for i in range(idx, idx + 20) if lines[i].strip() == "replacements: [")
        obj = (
            "      {" + nl
            + f"        // {SENTINEL}: #{pid} 在 0.2.2-rc.1 的原文（保留全部旧 pattern）。" + nl
            + "        pattern: " + json.dumps(rule["pattern"], ensure_ascii=False) + "," + nl
            + "        replace: " + json.dumps(rule["replace"], ensure_ascii=False) + "," + nl
            + "      }," + nl
        )
        lines.insert(j + 1, obj)
    out = "".join(lines)

    bak = str(path) + f".bak_redsob_drift_{TS}"
    shutil.copy2(path, bak)
    tmp = str(path) + ".fixtmp"
    Path(tmp).write_text(out, encoding="utf-8", newline="")
    os.replace(tmp, path)
    print("写入:", path)
    print("  备份:", Path(bak).name, "| 新增字符:", len(out) - len(text))
print("DONE")
