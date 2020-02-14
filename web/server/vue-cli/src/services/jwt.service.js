const ID_TOKEN_KEY = "__ccPrivilegedAccessToken";

function setCookie(name, value, expires) {
  const props = { path: "/" };

  if (expires) {
    const d = new Date();
    d.setTime(d.getTime() + (expires * 24 * 60 * 60 * 1000));
    props["expires"] = d.toUTCString();
  }

  const properties = Object.keys(props).map((k, v) => `${k}=${v}`).join(";");
  document.cookie = `${name}=${value};${properties}`;
}

export const getToken = () => {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${ID_TOKEN_KEY}=`);
  if (parts.length == 2) return parts.pop().split(";").shift();

  return null;
};

export const saveToken = token => {
  setCookie(ID_TOKEN_KEY, token);
};

export const destroyToken = () => {
  setCookie(ID_TOKEN_KEY, "", -1);
};

export default { getToken, saveToken, destroyToken };
