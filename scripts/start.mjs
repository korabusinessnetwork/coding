import { spawn } from "node:child_process";

const serverUrl = "http://127.0.0.1:8082/health";
const children = [];
let shuttingDown = false;

function startProcess(name, args) {
  const child = spawn("uv", args, {
    cwd: process.cwd(),
    stdio: "inherit",
    windowsHide: false,
  });
  child.on("error", (error) => {
    console.error(`[${name}] ${error.message}`);
    shutdown(1);
  });
  child.on("exit", (code, signal) => {
    if (!shuttingDown && code !== 0) {
      console.error(`[${name}] encerrou com código ${code ?? "null"}${signal ? ` (${signal})` : ""}.`);
      shutdown(code || 1);
    }
  });
  children.push(child);
  return child;
}

async function waitForServer(child) {
  for (let attempt = 0; attempt < 60; attempt += 1) {
    if (child.exitCode !== null) {
      throw new Error("fcc-server encerrou antes de ficar saudável.");
    }
    try {
      const response = await fetch(serverUrl);
      if (response.ok) return;
    } catch {
      // O servidor ainda está iniciando.
    }
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  throw new Error(`fcc-server não respondeu em ${serverUrl}.`);
}

function shutdown(code = 0) {
  if (shuttingDown) return;
  shuttingDown = true;
  for (const child of children) {
    if (!child.killed) child.kill("SIGINT");
  }
  setTimeout(() => process.exit(code), 1000).unref();
}

process.once("SIGINT", () => shutdown(0));
process.once("SIGTERM", () => shutdown(0));

const server = startProcess("fcc-server", ["run", "fcc-server"]);
try {
  await waitForServer(server);
  console.log("FCC saudável. Iniciando OpenCode...");
  startProcess("fcc-opencode", ["run", "fcc-opencode"]);
} catch (error) {
  console.error(error.message);
  shutdown(1);
}
