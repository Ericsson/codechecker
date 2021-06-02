const fs = require("fs");
const path = require("path");

const CC_DIR = path.join(__dirname, "__codechecker");
const WORKSPACE_DIR = path.join(CC_DIR, "workspace");

const SERVER_CONFIG = {
  authentication: {
    enabled : true,
    session_lifetime : 60000,
    refresh_time : 60,
    logins_until_cleanup : 30,
    method_dictionary: {
      enabled : true,
      auths : [ "cc:admin" ],
      groups : {}
    }
  }
};

const ROOT_USER =
  "root:2691b13e4c5eadd0adad38983e611b2caa19caaa3476ccf31cbcadddf65c321c";

// Create workspace directory if it does not exists.
if (!fs.existsSync(WORKSPACE_DIR)) {
  fs.mkdirSync(WORKSPACE_DIR);
}

// Create server configuration file and enable authentication.
const serverConfigFile = path.join(WORKSPACE_DIR, "server_config.json");
const data = JSON.stringify(SERVER_CONFIG, null, "  ");
fs.writeFileSync(serverConfigFile, data);

// Generate initial root credentials.
//  - username: root
//  - password: S3cr3t
const rootUserFile = path.join(WORKSPACE_DIR, "root.user");
fs.writeFileSync(rootUserFile, ROOT_USER);
