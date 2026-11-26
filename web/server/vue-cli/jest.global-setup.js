// Run the unit tests in a fixed timezone, so date formatting tests do not
// depend on the machine they run on. Jest workers inherit this environment.
module.exports = () => {
  process.env.TZ = "Europe/Budapest";
};
