const host = process.env.HOST || "localhost";
const port = process.env.PORT || 8002;
const chromeHeadless = process.env.CHROME_HEADLESS;

module.exports = {
  src_folders: [ "e2e/specs" ],
  page_objects_path: [ "e2e/pages" ],
  custom_commands_path: [ "e2e/commands" ],
  output_folder: "e2e/output",

  test_settings: {
    default: {
      launch_url: `http://${host}:${port}`,
      screenshots: {
        "path" : "e2e/screenshots"
      },
      webdriver: {
        start_process: true
      }
    },

    "chrome": {
      desiredCapabilities: {
        browserName: "chrome",
        chromeOptions : {
          args: [ ...[ chromeHeadless ? "--headless" : undefined ] ],
          w3c: false
        }
      }
    },

    "firefox": {
      webdriver: {
        start_process: true,
        server_path: require("geckodriver").path
      },
      desiredCapabilities: {
        browserName: "firefox",
        "moz:firefoxOptions": {
          binary: "/bin/firefox-esr",
          args: [ "--headless" ]
        }
      }
    },
  }
};
