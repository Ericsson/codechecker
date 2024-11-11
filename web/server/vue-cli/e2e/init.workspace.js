const fs = require("fs");
const path = require("path");

const CC_DIR = path.join(__dirname, "__codechecker");
const WORKSPACE_DIR = path.join(CC_DIR, "workspace");

const SERVER_CONFIG = {
  authentication: {
    enabled : true,
    "super_user" : "root",
    session_lifetime : 60000,
    refresh_time : 60,
    logins_until_cleanup : 30,
    method_dictionary: {
      enabled : true,
      auths : [ "cc:admin",
        "root:S3cr3t" ],
      groups : {}
    }
  }
};

// Create workspace directory if it does not exists.
if (!fs.existsSync(WORKSPACE_DIR)) {
  fs.mkdirSync(WORKSPACE_DIR);
}

// Create server configuration file and enable authentication.
const serverConfigFile = path.join(WORKSPACE_DIR, "server_config.json");
const data = JSON.stringify(SERVER_CONFIG, null, "  ");
fs.writeFileSync(serverConfigFile, data);