import fs from "node:fs";
import { fileURLToPath } from "node:url";
import { ALL_PATCHES, filePatchOutcome, targetFiles } from "file:///C:/Users/sobo/.dsh/profiles/desktop/node_modules/dsh-purge/lib/core.js";

process.chdir(fileURLToPath(new URL("./rules/", import.meta.url)));
const cases = JSON.parse(fs.readFileSync("patch_cases.json", "utf8"));
const BASE = "D:/deepseekh/resources/app/dsh/node_modules/@deepseek-ai";
const F = targetFiles(BASE);

let ok = true;
for (const c of cases) {
  const p = ALL_PATCHES.find((x) => x.id === c.id);
  const src = fs.readFileSync(c.fp, "utf8");
  const test = { ...p, replacements: [{ pattern: c.pattern, replace: c.replace }, ...p.replacements] };
  const hits = src.split(c.pattern).length - 1;
  const patched = src.replace(c.pattern, c.replace);
  const before = filePatchOutcome(src, test, c.fp);
  const after = filePatchOutcome(patched, test, c.fp);
  const original = filePatchOutcome(src, p, c.fp);
  

  console.log(`#${c.id} ${p.name}`);
  console.log(`  pattern 命中 ${hits} | 原补丁 ${original} | 加规则后 ${before} -> ${after}`);
  // 幂等：未落地时应 pending->applied；已落地时 hits=0 且状态为 applied 也算通过
  // #82 的 replace 以 pattern 开头，落地后 pattern 仍命中（hits=1），
  // 但 marker 判据已让状态为 applied —— 同时接受这两种幂等形态。
  const pass = (hits === 1 && before === "pending" && after === "applied")
            || (before === "applied" && after === "applied");
  console.log(`  ${pass ? "PASS" : "FAIL"}`);
  if (!pass) ok = false;
}
console.log(ok ? "ALL PASS" : "SOME FAILED");
if (!ok) process.exit(1);
