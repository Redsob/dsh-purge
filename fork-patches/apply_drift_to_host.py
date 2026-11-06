"""[Redsob fork] 把 5 条 0.2.2-rc.1 适配补丁落到宿主文件（可重放）。

不调用插件的 apply（会触发重启），只做精确字符串替换；每个文件先备份。
"""
import json
import os
import shutil
import datetime
from pathlib import Path

BASE = Path(r"D:/deepseekh/resources/app/dsh/node_modules/@deepseek-ai")
T = Path(__file__).resolve().parent / "rules"
TS = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

# pid -> [(相对路径, pattern, replace)]
JOBS = {}
for pid, rel in [
    (14, "dsh-sandbox/lib/index.js"),
    (17, "dsh-fs-observation-policy/lib/index.js"),
    (67, "dsh-agent-loop/lib/index.js"),
    (62, "dsh-tools/lib/pipeline.js"),
]:
    JOBS.setdefault(str(BASE / rel), []).append((
        pid,
        (T / f"patch{pid}_022rc1_pattern.txt").read_text(encoding="utf-8", newline=""),
        (T / f"patch{pid}_022rc1_replace.txt").read_text(encoding="utf-8", newline=""),
    ))

# #82 的 desktop-shell 不在 @deepseek-ai 下，而是 officialShellMain() 解析出的
# resources/app/lib/main.js（宿主进程靠 desktop_exe 环境变量才能定位）。
DESKTOP_SHELL = BASE.parents[2] / "lib" / "main.js"
JOBS.setdefault(str(DESKTOP_SHELL), []).append((
    82,
    (T / "patch82_022rc1_pattern.txt").read_text(encoding="utf-8", newline=""),
    (T / "patch82_022rc1_replace.txt").read_text(encoding="utf-8", newline=""),
))

# #60 是纯组件搬家，官方 4 条 pattern 逐字仍在新包里
rules60 = json.loads((T / "patch60_official_rules.json").read_text(encoding="utf-8"))
for rel in ["dsh-tool-executor-ptc/lib/index.js", "dsh-tool-executor-ptc/lib/types/ptc.js"]:
    key = str(BASE / rel)
    for i, r in enumerate(rules60):
        JOBS.setdefault(key, []).append((f"60.{i}", r["pattern"], r["replace"]))

changed = []
for fp, rules in JOBS.items():
    p = Path(fp)
    s = p.read_text(encoding="utf-8", newline="")
    out = s
    applied = []
    for tag, pat, rep in rules:
        # 幂等：#82 的 replace 以 pattern 开头，若不先判「替换体已存在」会重复插入
        if rep in out:
            continue
        n = out.count(pat)
        if n:
            out = out.replace(pat, rep)
            applied.append(f"{tag}×{n}")
    if out == s:
        # main.js 不在 @deepseek-ai 下，按 app 根取相对路径
        print("无改动:", p.relative_to(BASE.parents[2]))
        continue
    bak = str(p) + f".bak_redsob_drift_{TS}"
    shutil.copy2(p, bak)
    tmp = str(p) + ".fixtmp"
    Path(tmp).write_text(out, encoding="utf-8", newline="")
    os.replace(tmp, p)
    print("写入:", p.relative_to(BASE.parents[2]))
    print("  备份:", Path(bak).name, "| 命中:", ", ".join(applied), "| 长度变化:", len(out) - len(s))
    changed.append(str(p))

# 改动清单只打印，不写进 rules/（避免污染仓库）
print("改动文件数:", len(changed))
