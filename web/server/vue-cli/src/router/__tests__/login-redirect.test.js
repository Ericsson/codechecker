import getLoginRedirect from "@/router/login-redirect";

describe("Login redirect", () => {
  const noAuth = { requiresAuthentication: false };
  const auth = { requiresAuthentication: true };

  test("show the login page if authentication is required", () => {
    const route = { name: "login", query: {} };
    expect(getLoginRedirect(route, auth)).toBeUndefined();
  });

  test("leave other pages alone", () => {
    const route = { name: "products", query: {} };
    expect(getLoginRedirect(route, noAuth)).toBeUndefined();
  });

  test("go to the products page without authentication", () => {
    const route = { name: "login", query: {} };
    expect(getLoginRedirect(route, noAuth)).toEqual({ name: "products" });
  });

  test("go to the return_to page without authentication", () => {
    const route = {
      name: "login",
      query: { "return_to": "/Default/runs?run=foo" }
    };
    expect(getLoginRedirect(route, noAuth)).toEqual("/Default/runs?run=foo");
  });
});
