const host = process.env.HOST || "localhost";
const port = process.env.PORT || 8001;
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
      }
    },

    selenium: {
      selenium: {
        start_process: true,
        port: 4444,
        host: "127.0.0.1",
        server_path: require("selenium-server").path,
        log_path: "e2e/output",
        check_process_delay: 5000,
        cli_args: {
          "webdriver.gecko.driver": require("geckodriver").path,
          "webdriver.chrome.driver": require("chromedriver").path
        }
      },

      webdriver: {
        start_process: false
      }
    },

    "selenium.chrome": {
      extends: "selenium",
      desiredCapabilities: {
        browserName: "chrome",
        chromeOptions : {
          args: [ ...[ chromeHeadless ? "--headless" : undefined ] ],
          w3c: false
        }
      }
    },

    "selenium.firefox": {
      extends: "selenium",
      desiredCapabilities: {
        browserName: "firefox"
      }
    },
  }
};
