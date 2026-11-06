/**
 * The login page is a dead end when the server does not require
 * authentication. Returns the location to go to instead of the login page in
 * that case, or undefined if the login page should be shown.
 * @param {object} to The route being navigated to.
 * @param {object} authParams Authentication parameters of the server.
 */
export default function getLoginRedirect(to, authParams) {
  if (to.name !== "login" || authParams.requiresAuthentication)
    return undefined;

  return to.query["return_to"] || { name: "products" };
}
