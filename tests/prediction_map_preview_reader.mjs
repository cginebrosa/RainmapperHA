// Persistent JSON-lines bridge for isolated preview readers only.
import { spawn } from "node:child_process";
import { createInterface } from "node:readline";

export function startPreviewReader(python, args, root, unavailable, timeoutMs = 5000) {
  const child = spawn(python, args, { cwd: root, stdio: ["pipe", "pipe", "inherit"] });
  let serial = 0, alive = true;
  const waiting = new Map();
  const finish = (id, data) => { const task = waiting.get(id); if (task) { clearTimeout(task.timer); waiting.delete(id); task.resolve(data); } };
  const stop = () => { alive = false; for (const id of waiting.keys()) finish(id, unavailable); };
  child.on("exit", stop); child.on("error", stop); child.stdin.on("error", stop);
  createInterface({ input: child.stdout }).on("line", line => {
    try { const { id, ...data } = JSON.parse(line); finish(id, data); } catch { stop(); }
  });
  process.on("exit", () => child.kill("SIGTERM"));
  return input => new Promise(resolve => {
    if (!alive || waiting.size >= 4) return resolve(unavailable);
    const id = ++serial;
    const timer = setTimeout(() => { finish(id, unavailable); stop(); child.kill("SIGTERM"); }, timeoutMs);
    waiting.set(id, { resolve, timer });
    child.stdin.write(JSON.stringify({ id, ...input }) + "\n");
  });
}
