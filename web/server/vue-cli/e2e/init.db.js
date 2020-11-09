const { execFile, execFileSync, execSync, spawn, spawnSync } = require("child_process");
const path = require("path");
const fs = require("fs");

const host = process.env.HOST || "localhost";
const port = process.env.PORT || 8001;
const url = `http://${host}:${port}`;

const CC_DIR = path.join(__dirname, "__codechecker");
const REPORTS_DIR = path.join(CC_DIR, "reports");
const PASSWORD_FILE = path.join(CC_DIR, "codechecker.passwords.json");
const SESSION_FILE = path.join(CC_DIR, "codechecker.session.json");

// List of products which will be added to the server.
const PRODUCTS = [
  {
    endpoint: "e2e",
    name: "e2e",
    description: "This is my product for e2e test."
  }
];

// Runs which will be stored to the server.
const RUNS = [
  {
    name: "macros",
    output: path.join(REPORTS_DIR, "macros"),
    url: `http://${host}:${port}/e2e`,
    tag: "v1.0.0",
    description: "Contains macro expansions."
  },
  {
    name: "simple",
    output: path.join(REPORTS_DIR, "simple"),
    url: `http://${host}:${port}/e2e`,
    description: "This is my simple run."
  },
  // We store this run so many times to test the run history load more feature.
  ...[ ...Array(10).keys() ].map(idx => ({
    name: "simple",
    output: path.join(REPORTS_DIR, "simple"),
    url: `http://${host}:${port}/e2e`,
    tag: `v0.0.${idx}`,
    description: "This is my updated run."
  })),
  {
    name: "duplicated",
    output: path.join(REPORTS_DIR, "simple"),
    url: `http://${host}:${port}/e2e`,
    description: "This is duplication of my simple run."
  },
  {
    name: "remove",
    output: path.join(REPORTS_DIR, "simple"),
    url: `http://${host}:${port}/e2e`,
    tag: "v0.0.1-deprecated",
    description: "This can can be removed."
  },
  {
    name: "suppress",
    output: path.join(REPORTS_DIR, "suppress"),
    url: `http://${host}:${port}/e2e`
  }
];

function runCommand(cmd) {
  execSync(cmd, {
    stdio: "inherit",
    env: {
      ...process.env,
      "CC_PASS_FILE": PASSWORD_FILE,
      "CC_SESSION_FILE": SESSION_FILE
    }
  });
}

async function login (username) {
  const cmd = [
    "CodeChecker", "cmd", "login", username,
    "--url", url
  ].join(" ");

  console.log("Login command: ", cmd);

  runCommand(cmd);
}

function logout() {
  const cmd = [
    "CodeChecker", "cmd", "login", "-d",
    "--url", url
  ].join(" ");

  console.log("Logout command: ", cmd);

  runCommand(cmd);
}

function addProduct({ endpoint, name, description }) {
  const cmd = [
    "CodeChecker", "cmd", "products", "add",
    "-n", name,
    "--description", `"${description}"`,
    "--url", url,
    endpoint
  ].join(" ");

  console.log("Add product command: ", cmd);

  runCommand(cmd);
}

function store({ name, output, tag, description, url }) {
  let cmd = [
    "CodeChecker", "store",
    "-n", `"${name}"`,
    "--url", `"${url}"`,
    output
  ];

  if (tag)
    cmd = [ ...cmd, "--tag", `"${tag}"` ];

  if (description)
    cmd = [ ...cmd, "--description", `"${description}"` ];

  cmd = cmd.join(" ");

  console.log("Store command: ", cmd);

  runCommand(cmd);
}

login("root");

// Add initial products.
PRODUCTS.forEach(args => {
  addProduct(args);
});

// Store reports.
RUNS.forEach(args => {
  store(args);
});

logout();
