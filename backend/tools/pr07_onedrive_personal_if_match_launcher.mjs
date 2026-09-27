import { spawn } from "node:child_process";
import { existsSync, statSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const PROBE_MODULE = "tools.pr07_onedrive_personal_if_match_probe";
const TOKEN_ENVIRONMENT_VARIABLE = "VALORA_PR07_GRAPH_ACCESS_TOKEN";
const C2_CANDIDATE = "C2_AUTO_V2";
const C2_SCHEMA_VERSION = 3;
const SELF_TEST_TIMEOUT_MS = 15_000;
const PREFLIGHT_TIMEOUT_MS = 15_000;
const MAX_CAPTURE_BYTES = 1024 * 1024;
const CLEANUP_STATES = new Set([
  "ABSENT_OR_DELETED_TO_RECYCLE_BIN",
  "DELETED_TO_RECYCLE_BIN",
  "FAILED",
  "NOT_ATTEMPTED",
]);
const C2_REPORT_KEYS = [
  "schema_version", "candidate", "runtime_gate", "checked_at", "status", "outcome",
  "reason_code", "phase", "fresh_final_http_status", "stale_final_http_status",
  "provider_error_code", "partial_observations", "checks", "cleanup", "cleanup_issue",
];
const C2_CHECK_KEYS = [
  "fresh_partial_preserved", "fresh_commit_verified", "stale_partial_preserved",
  "concurrent_write_verified", "item_identity_preserved", "concurrent_bytes_preserved",
  "concurrent_etag_preserved", "stale_candidate_observed",
];
const C2_OUTCOMES = new Set([
  "OBSERVED_SAFE_STALE_REJECTION", "UNSAFE_STALE_OVERWRITE", "SAFETY_VIOLATION", "INCONCLUSIVE",
]);
const C2_REASON_CODES = new Set([
  "SAFE_412", "STALE_BYTES_OVERWROTE_CONCURRENT", "NONFINAL_MUTATION", "IDENTITY_CHANGED",
  "RESPONSE_IDENTITY_MISMATCH", "ALTERNATE_REJECTION", "FINAL_NOT_COMPLETED",
  "TRANSPORT_UNKNOWN", "POST_STATE_UNAVAILABLE", "POST_STATE_INCONSISTENT", "THIRD_STATE",
  "FRESH_CONTROL_FAILED", "RACE_SETUP_FAILED", "SESSION_CREATION_FAILED", "FIXTURE_FAILED",
  "UNEXPECTED_SANITIZED_FAILURE", "PARTIAL_HTTP_UNEXPECTED", "PARTIAL_RANGE_MISSING",
  "PARTIAL_RANGE_MALFORMED", "PARTIAL_RANGE_UNEXPECTED",
]);
const C2_PHASES = new Set(["FIXTURE", "FRESH", "STALE", "COMPLETE"]);
const C2_PROVIDER_CODES = new Set([
  "accessDenied", "invalidRequest", "invalidRange", "nameAlreadyExists", "resourceModified",
  "itemNotFound", "quotaLimitReached", "tooManyRequests", "generalException", "unknown", null,
]);
const C2_CLEANUP_ISSUES = new Set([
  "NONE", "SESSION_UNKNOWN", "CANCEL_FAILED", "ITEM_DELETE_FAILED", "EVIDENCE_INCOMPLETE", "MULTIPLE",
]);
const PARTIAL_RANGE_CLASSES = new Set([
  "EXPECTED_START", "MALFORMED", "MISSING", "NOT_APPLICABLE", "NOT_OBSERVED",
  "UNEXPECTED_START",
]);
const SELF_TEST_REPORT = {
  candidate: C2_CANDIDATE,
  dependency_import: "PASS",
  environment: "PRESENT",
  interpreter: "PASS",
  mode: "SELF_TEST",
  network: "NOT_ATTEMPTED",
  package_resolution: "PASS",
  runtime_gate: "BLOCKED",
  schema_version: C2_SCHEMA_VERSION,
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

function containsToken(value, token) {
  if (!token) return false;
  if (typeof value === "string") return value.includes(token);
  if (!value || typeof value !== "object") return false;
  return Object.values(value).some((candidate) => containsToken(candidate, token));
}

function validPartialObservations(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)
      || !hasExactKeys(value, ["fresh", "stale"])) return false;
  return ["fresh", "stale"].every((role) => {
    const observation = value[role];
    if (!observation || typeof observation !== "object" || Array.isArray(observation)
        || !hasExactKeys(observation, ["http_status", "range_class"])) return false;
    const { http_status: httpStatus, range_class: rangeClass } = observation;
    const validStatus = httpStatus === null
      || (Number.isInteger(httpStatus) && httpStatus >= 100 && httpStatus <= 599);
    if (!validStatus || !PARTIAL_RANGE_CLASSES.has(rangeClass)) return false;
    if (rangeClass === "NOT_OBSERVED") return httpStatus === null;
    if (rangeClass === "NOT_APPLICABLE") return httpStatus !== null && httpStatus !== 202;
    return httpStatus === 202;
  });
}

export function validateReport(report, selfTest, token, expectedCandidate) {
  if (!report || typeof report !== "object" || Array.isArray(report)) {
    return false;
  }
  if (containsToken(report, token)) {
    return false;
  }
  if (selfTest && report.status === "PASS") {
    const expectedKeys = Object.keys(SELF_TEST_REPORT);
    return hasExactKeys(report, expectedKeys)
      && expectedKeys.every((key) => report[key] === SELF_TEST_REPORT[key])
      && report.candidate === expectedCandidate;
  }
  if (selfTest || !hasExactKeys(report, C2_REPORT_KEYS)) {
    return false;
  }
  const checks = report.checks;
  if (!checks || typeof checks !== "object" || Array.isArray(checks)
      || !hasExactKeys(checks, C2_CHECK_KEYS)
      || Object.values(checks).some((value) => ![true, false, null].includes(value))) {
    return false;
  }
  if (!validPartialObservations(report.partial_observations)) return false;
  const partialReasonClasses = {
    PARTIAL_HTTP_UNEXPECTED: "NOT_APPLICABLE",
    PARTIAL_RANGE_MALFORMED: "MALFORMED",
    PARTIAL_RANGE_MISSING: "MISSING",
    PARTIAL_RANGE_UNEXPECTED: "UNEXPECTED_START",
  };
  const partialReasonClass = partialReasonClasses[report.reason_code];
  if (partialReasonClass !== undefined
      && (!["FRESH", "STALE"].includes(report.phase)
        || report.partial_observations[report.phase.toLowerCase()].range_class !== partialReasonClass)) {
    return false;
  }
  const expectedPartial = { http_status: 202, range_class: "EXPECTED_START" };
  const expectedPartials = ["fresh", "stale"].every((role) => {
    const observation = report.partial_observations[role];
    return observation.http_status === expectedPartial.http_status
      && observation.range_class === expectedPartial.range_class;
  });
  const validHttp = (value) => value === null
    || (Number.isInteger(value) && value >= 100 && value <= 599);
  const safe = report.outcome === "OBSERVED_SAFE_STALE_REJECTION"
    && report.reason_code === "SAFE_412"
    && report.phase === "COMPLETE"
    && [200, 201].includes(report.fresh_final_http_status)
    && report.stale_final_http_status === 412
    && expectedPartials
    && C2_CHECK_KEYS.filter((key) => key !== "stale_candidate_observed")
      .every((key) => checks[key] === true)
    && checks.stale_candidate_observed === false;
  const unsafe = report.outcome === "UNSAFE_STALE_OVERWRITE"
    && report.reason_code === "STALE_BYTES_OVERWROTE_CONCURRENT"
    && checks.fresh_commit_verified === true
    && checks.concurrent_write_verified === true
    && checks.item_identity_preserved === true
    && checks.stale_candidate_observed === true
    && checks.concurrent_bytes_preserved === false
    && expectedPartials;
  if ((report.outcome === "OBSERVED_SAFE_STALE_REJECTION" && !safe)
      || (report.outcome === "UNSAFE_STALE_OVERWRITE" && !unsafe)) return false;
  const expectedPass = safe && report.cleanup === "DELETED_TO_RECYCLE_BIN"
    && report.cleanup_issue === "NONE";
  return report.schema_version === C2_SCHEMA_VERSION
    && report.candidate === expectedCandidate
    && report.runtime_gate === "BLOCKED"
    && ["PASS", "FAIL"].includes(report.status)
    && (report.status === "PASS") === expectedPass
    && typeof report.checked_at === "string"
    && report.checked_at.length <= 64
    && /(?:Z|[+-]\d{2}:\d{2})$/.test(report.checked_at)
    && !Number.isNaN(Date.parse(report.checked_at))
    && C2_OUTCOMES.has(report.outcome)
    && C2_REASON_CODES.has(report.reason_code)
    && C2_PHASES.has(report.phase)
    && validHttp(report.fresh_final_http_status)
    && validHttp(report.stale_final_http_status)
    && C2_PROVIDER_CODES.has(report.provider_error_code)
    && CLEANUP_STATES.has(report.cleanup)
    && C2_CLEANUP_ISSUES.has(report.cleanup_issue);
}

function parseArguments(argv) {
  let pythonExecutable = null;
  let selfTest = false;
  let allowLiveWrite = false;
  let cleanupTestItem = false;
  let candidate = null;

  for (let index = 0; index < argv.length; index += 1) {
    const argument = argv[index];
    if (argument === "--python-executable") {
      pythonExecutable = argv[index + 1] ?? null;
      index += 1;
    } else if (argument === "--candidate") {
      candidate = argv[index + 1] ?? null;
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
  if (candidate !== C2_CANDIDATE) {
    return { error: "C2 candidate is required." };
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
      ? ["-m", PROBE_MODULE, "--candidate", candidate, "--self-test"]
      : [
          "-m",
          PROBE_MODULE,
          "--candidate",
          candidate,
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
  if (!validateReport(report, parsed.selfTest, token, C2_CANDIDATE) || !exitMatchesReport) {
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
