const { execSync } = require("child_process");
const fs = require("fs");
const path = require("path");

const CC_DIR = path.join(__dirname, "__codechecker");
const PROJ_DIR = path.join(CC_DIR, "projects");
const REPORTS_DIR = path.join(CC_DIR, "reports");
const CMP_DB_DIR = path.join(CC_DIR, "compilation_database");

// List of projects which will be logged and analyzed.
// Reports will be generated in the REPORTS_DIR for each project.
const PROJECTS = [
  "macros",
  "simple",
  "suppress"
];

function log(output, buildCommand) {
  const cmd = [
    "CodeChecker", "log",
    "-b", `"${buildCommand}"`,
    "-o", output
  ].join(" ");

  console.log("Log command: ", cmd);

  execSync(cmd, { stdio: "inherit" });
}

function analyze(output, logfile) {
  const cmd = [
    "CodeChecker", "analyze", "-c",
    "-o", `"${output}"`,
    logfile
  ].join(" ");

  console.log("Analyze command: ", cmd);

  try {
    execSync(cmd, { stdio: "inherit" });
  } catch (error) {
    if (error.status !== 0 && error.status !== 2)
      throw(error);
  }
}

if (!fs.existsSync(CMP_DB_DIR)) {
  fs.mkdirSync(CMP_DB_DIR);
}

// Log and analyze projects.
PROJECTS.forEach(name => {
  const logDir = path.join(CMP_DB_DIR, name);
  const logFile = path.join(logDir, "compilation_database.json");
  if (!fs.existsSync(logDir)) {
    fs.mkdirSync(logDir);
  }

  if (!fs.existsSync(logFile)) {
    const buildCommand = [ "make", "-C", PROJ_DIR, name ].join(" ");
    log(logFile, buildCommand);
  }

  const output = path.join(REPORTS_DIR, name);
  analyze(output, logFile);
});
