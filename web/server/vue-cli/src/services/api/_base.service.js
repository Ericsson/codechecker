import {
  TBufferedTransport,
  TJSONProtocol,
  createXHRClient,
  createXHRConnection
} from "thrift";

import router from "@/router";
import store from "@/store";
import { ADD_ERROR, PURGE_AUTH } from "@/store/mutations.type";

import authService from "./auth.service";
import { eventHub } from "./eventHub";

const host = process.env.VITE_CC_SERVER_HOST || "localhost";
const port = parseInt(process.env.VITE_CC_SERVER_PORT, 10) || 8080;
const api = process.env.VITE_CC_API_VERSION || "6.61";

class BaseService {
  constructor(serviceName, serviceClass, version = api) {
    this._serviceName = serviceName;
    this._serviceClass = serviceClass;
    this.version = version;
    this._client = this.createClient();
    eventHub.on("update", endpoint => {
      this._client = this.createClient(endpoint);
    });
  }

  getClient() {
    return this._client;
  }

  createClient(endpoint) {
    const product = endpoint || window.__cc_endpoint || "Default";
    const path = `/${product}/${this.version}/${this._serviceName}`;
    const connection = createXHRConnection(host, port, {
      transport: TBufferedTransport,
      protocol: TJSONProtocol,
      path,
      https: window.location.protocol === "https:"
    });

    const getXmlHttpRequestObject = connection.getXmlHttpRequestObject;
    connection.getXmlHttpRequestObject = function () {
      const xreq = getXmlHttpRequestObject();
      xreq.addEventListener("readystatechange", function () {
        if (this.readyState === 1) {
          xreq.setRequestHeader("Authorization", "Bearer " + authService.getToken());
        } else if (this.readyState === 4) {
          if (this.status === 504) {
            store.commit(ADD_ERROR, `Error ${this.status}: ${this.statusText}`);
          } else if (this.status === 401) {
            store.commit(PURGE_AUTH);
          }
        }
      });
      return xreq;
    };

    return createXHRClient(this._serviceClass, connection);
  }
}

const handleThriftError = function (cb, onError) {
  return (err, ...args) => {
    if (!err) {
      if (cb) cb.apply(this, args);
      return;
    }
    if (err instanceof Error) {
      const msg = err.message;
      if (msg.includes("Error code 401:")) {
        store.commit(PURGE_AUTH);
        router.push({
          name: "login",
          query: { return_to: router.currentRoute.fullPath }
        }).catch(() => {});
        if (onError) onError(err);
        return;
      } else if (msg.match(/The product .* does not exist!/)) {
        router.replace({ name: "404" }).catch(() => {});
        return;
      }
    }
    if (onError) {
      onError(err);
    } else if (err instanceof Error) {
      store.commit(ADD_ERROR, err.message);
    }
  };
};

export {
  BaseService,
  handleThriftError,
  eventHub
};
