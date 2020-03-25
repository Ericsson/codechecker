import VueCookie from "vue-cookie";

const ID_TOKEN_KEY = "__ccPrivilegedAccessToken";

export const getToken = () => {
  return VueCookie.get(ID_TOKEN_KEY);
};

export const saveToken = token => {
  VueCookie.set(ID_TOKEN_KEY, token);
};

export const destroyToken = () => {
  VueCookie.delete(ID_TOKEN_KEY);
};

export default { getToken, saveToken, destroyToken };
