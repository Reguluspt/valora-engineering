import { spawn } from "node:child_process";
import { existsSync, statSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const PROBE_MODULE = "tools.pr07_onedrive_personal_if_match_probe";
const TOKEN_ENVIRONMENT_VARIABLE = "VALORA_PR07_GRAPH_ACCESS_TOKEN";
const SELF_TEST_TIMEOUT_MS = 15_000;
const PREFLIGHT_TIMEOUT_MS = 15_000;
const MAX_CAPTURE_BYTES = 1024 * 1024;
const SAFE_PROVIDER_ERROR_CODE = /^[A-Za-z][A-Za-z0-9._-]{0,63}$/;
const CLEANUP_STATES = new Set([
  "ABSENT_OR_DELETED_TO_RECYCLE_BIN",
  "DELETED_TO_RECYCLE_BIN",
  "FAILED",
  "NOT_ATTEMPTED",
]);
const SELF_TEST_REPORT = {
  dependency_import: "PASS",
  environment: "PRESENT",
  interpreter: "PASS",
  mode: "SELF_TEST",
  network: "NOT_ATTEMPTED",
  package_resolution: "PASS",
  status: "PASS",
  working_directory: "BACKEND",
};

function emit(report, exitCode) {
  process.stdout.write(`${JSON.stringify(report)}\n`);
  process.exitCode = exitCode;
}

function sanitizedStderr(stderrPresent) {
  return stderrPresent ? "PRESENT_SANITIZED" : "EMPTY";
}

function validationFailure(reason) {
  emit({ status: "FAIL", stage: "LAUNCHER_VALIDATION", reason }, 2);
}

function hasExactKeys(value, expectedKeys) {
  const actualKeys = Object.keys(value).sort();
  const sortedExpectedKeys = [...expectedKeys].sort();
  return actualKeys.length === sortedExpectedKeys.length
    && actualKeys.every((key, index) => key === sortedExpectedKeys[index]);
}

function hasOnlyKeys(value, allowedKeys) {
  return Object.keys(value).every((key) => allowedKeys.has(key));
}

function containsToken(value, token) {
  return Boolean(token) && Object.values(value).some(
    (candidate) => typeof candidate === "string" && candidate.includes(token),
  );
}

export function validateReport(report, selfTest, token) {
  if (!report || typeof report !== "object" || Array.isArray(report)) {
    return false;
  }
  if (containsToken(report, token)) {
    return false;
  }
  if (selfTest && report.status === "PASS") {
    const expectedKeys = Object.keys(SELF_TEST_REPORT);
    return hasExactKeys(report, expectedKeys)
      && expectedKeys.every((key) => report[key] === SELF_TEST_REPORT[key]);
  }
  if (report.status === "FAIL") {
    const allowedKeys = new Set([
      "cleanup",
      "http_status",
      "provider_error_code",
      "reason",
      "status",
    ]);
    if (!hasOnlyKeys(report, allowedKeys)) {
      return false;
    }
    if (
      typeof report.reason !== "string"
      || report.reason.length === 0
      || report.reason.length > 512
      || /[\r\n]/.test(report.reason)
    ) {
      return false;
    }
    if (
      report.http_status !== undefined
      && (!Number.isInteger(report.http_status)
        || report.http_status < 100
        || report.http_status > 599)
    ) {
      return false;
    }
    if (
      report.provider_error_code !== undefined
      && (typeof report.provider_error_code !== "string"
        || !SAFE_PROVIDER_ERROR_CODE.test(report.provider_error_code))
    ) {
      return false;
    }
    return report.cleanup === undefined || CLEANUP_STATES.has(report.cleanup);
  }
  if (selfTest || report.status !== "PASS") {
    return false;
  }
  const successKeys = [
    "checked_at",
    "cleanup",
    "concurrent_bytes_preserved",
    "drive_type",
    "fresh_conditional_commit",
    "isolated_item_created",
    "item_identity_preserved",
    "provider",
    "stale_commit_http_status",
    "stale_conditional_commit",
    "status",
  ];
  return hasExactKeys(report, successKeys)
    && typeof report.checked_at === "string"
    && report.checked_at.length <= 64
    && !Number.isNaN(Date.parse(report.checked_at))
    && report.cleanup === "DELETED_TO_RECYCLE_BIN"
    && report.concurrent_bytes_preserved === true
    && report.drive_type === "personal"
    && report.fresh_conditional_commit === "PASS"
    && report.isolated_item_created === true
    && report.item_identity_preserved === true
    && report.provider === "Microsoft Graph v1.0"
    && report.stale_commit_http_status === 412
    && report.stale_conditional_commit === "HTTP_412_PASS";
}

function parseArguments(argv) {
  let pythonExecutable = null;
  let selfTest = false;
  let allowLiveWrite = false;
  let cleanupTestItem = false;

  for (let index = 0; index < argv.length; index += 1) {
    const argument = argv[index];
    if (argument === "--python-executable") {
      pythonExecutable = argv[index + 1] ?? null;
      index += 1;
    } else if (argument === "--self-test") {
      selfTest = true;
    } else if (argument === "--allow-live-write") {
      allowLiveWrite = true;
    } else if (argument === "--cleanup-test-item") {
      cleanupTestItem = true;
    } else {
      return { error: "Launcher arguments are invalid." };
    }
  }

  if (!pythonExecutable || !path.isAbsolute(pythonExecutable)) {
    return { error: "Python executable must be an absolute file path." };
  }
  try {
    if (!existsSync(pythonExecutable) || !statSync(pythonExecutable).isFile()) {
      return { error: "Python executable path is unavailable." };
    }
  } catch {
    return { error: "Python executable path is unavailable." };
  }
  if (selfTest && (allowLiveWrite || cleanupTestItem)) {
    return { error: "Self-test cannot be combined with live-write flags." };
  }
  if (!selfTest && (!allowLiveWrite || !cleanupTestItem)) {
    return { error: "Both live-write acknowledgements are required." };
  }

  return {
    pythonExecutable,
    probeArguments: selfTest
      ? ["-m", PROBE_MODULE, "--self-test"]
      : [
          "-m",
          PROBE_MODULE,
          "--allow-live-write",
          "--cleanup-test-item",
        ],
    selfTest,
  };
}

export function runChild(executable, childArguments, options) {
  return new Promise((resolve) => {
    const stdoutChunks = [];
    let capturedBytes = 0;
    let stdoutOverflow = false;
    let stderrPresent = false;
    let timedOut = false;
    let spawnError = false;
    let timer = null;
    const child = spawn(executable, childArguments, {
      cwd: options.cwd,
      env: options.env,
      windowsHide: true,
      shell: false,
      stdio: ["ignore", "pipe", "pipe"],
    });

    child.stdout.on("data", (chunk) => {
      const remaining = MAX_CAPTURE_BYTES - capturedBytes;
      if (remaining > 0) {
        const captured = chunk.subarray(0, remaining);
        stdoutChunks.push(captured);
        capturedBytes += captured.length;
      }
      if (chunk.length > remaining) {
        stdoutOverflow = true;
      }
    });
    child.stderr.on("data", (chunk) => {
      stderrPresent ||= chunk.length > 0;
    });
    child.on("error", () => {
      spawnError = true;
    });
    child.on("close", (status) => {
      if (timer !== null) {
        clearTimeout(timer);
      }
      resolve({
        status,
        stdout: Buffer.concat(stdoutChunks).toString("utf8"),
        stdoutOverflow,
        stderrPresent,
        timedOut,
        error: spawnError,
      });
    });
    if (options.timeout !== undefined) {
      timer = setTimeout(() => {
        timedOut = true;
        child.kill();
      }, options.timeout);
    }
  });
}

async function main() {
  const parsed = parseArguments(process.argv.slice(2));
  if (parsed.error) {
    validationFailure(parsed.error);
    return;
  }

  const toolsDirectory = path.dirname(fileURLToPath(import.meta.url));
  const backendDirectory = path.resolve(toolsDirectory, "..");
  const preflightProgram = [
    "import importlib.util, sys",
    "requirements = ('httpx', 'tools.pr07_onedrive_personal_if_match_probe')",
    "available = all(importlib.util.find_spec(name) is not None for name in requirements)",
    "raise SystemExit(0 if sys.version_info >= (3, 12) and available else 1)",
  ].join("; ");
  const preflightEnvironment = { ...process.env };
  delete preflightEnvironment[TOKEN_ENVIRONMENT_VARIABLE];
  const preflight = await runChild(
    parsed.pythonExecutable,
    ["-c", preflightProgram],
    {
      cwd: backendDirectory,
      env: preflightEnvironment,
      timeout: PREFLIGHT_TIMEOUT_MS,
    },
  );

  if (
    preflight.error
    || preflight.timedOut
    || preflight.stdoutOverflow
    || preflight.status !== 0
  ) {
    emit(
      {
        status: "FAIL",
        stage: "DEPENDENCY_PREFLIGHT",
        reason: "Python dependency preflight failed.",
        child_exit_code: Number.isInteger(preflight.status) ? preflight.status : 1,
        child_stderr: sanitizedStderr(preflight.stderrPresent),
      },
      1,
    );
    return;
  }

  const child = await runChild(parsed.pythonExecutable, parsed.probeArguments, {
    cwd: backendDirectory,
    env: process.env,
    timeout: parsed.selfTest ? SELF_TEST_TIMEOUT_MS : undefined,
  });
  const childExitCode = Number.isInteger(child.status) ? child.status : 1;
  if (
    child.error
    || child.timedOut
    || child.stdoutOverflow
    || child.stderrPresent
  ) {
    emit(
      {
        status: "FAIL",
        stage: "PROBE_PROCESS",
        reason: "Probe process failed before a clean report was captured.",
        child_exit_code: childExitCode,
        child_stderr: sanitizedStderr(child.stderrPresent),
      },
      1,
    );
    return;
  }

  const lines = child.stdout.trim().split(/\r?\n/).filter(Boolean);
  let report = null;
  if (lines.length === 1) {
    try {
      report = JSON.parse(lines[0]);
    } catch {
      report = null;
    }
  }
  const token = process.env[TOKEN_ENVIRONMENT_VARIABLE] ?? "";
  const exitMatchesReport = report?.status === "PASS"
    ? childExitCode === 0
    : childExitCode !== 0;
  if (!validateReport(report, parsed.selfTest, token) || !exitMatchesReport) {
    emit(
      {
        status: "FAIL",
        stage: "PROBE_PROCESS",
        reason: "Probe process returned no valid sanitized JSON report.",
        child_exit_code: childExitCode,
        child_stderr: "EMPTY",
      },
      1,
    );
    return;
  }

  emit(report, childExitCode);
}

const invokedPath = process.argv[1] ? path.resolve(process.argv[1]) : null;
if (invokedPath === fileURLToPath(import.meta.url)) {
  await main();
}
