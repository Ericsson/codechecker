import Vue from "vue";
import {
  TBufferedTransport,
  TJSONProtocol,
  createXHRClient,
  createXHRConnection
} from "thrift";

import router from "@/router";
import store from "@/store";
import { ADD_ERROR, PURGE_AUTH } from "@/store/mutations.type";

// Host should be set explicitly to `hostname` because thrift will use
// the value of `window.location.host` which will contain port number by
// default on local host which cause invalid url format.
const host = process.env.CC_SERVER_HOST || window.location.hostname;
const port = parseInt(process.env.CC_SERVER_PORT, 10) ||
  parseInt(window.location.port, 10);
const api = process.env.CC_API_VERSION;

const eventHub = new Vue();

class BaseService {
  constructor(serviceName, serviceClass) {
    this._serviceName = serviceName;
    this._serviceClass = serviceClass;
    this._client = this.createClient();

    // Event which can be used to update client on route changes.
    eventHub.$on("update", endpoint => {
      this._client = this.createClient(endpoint);
    });
  }

  getClient() {
    return this._client;
  }

  createClient(endpoint) {
    const productEndpoint = endpoint ? "/" + endpoint : "";
    const connection = createXHRConnection(host, port, {
      transport: TBufferedTransport,
      protocol: TJSONProtocol,
      path: `${productEndpoint}/v${api}/${this._serviceName}`,
      https: window.location.protocol === "https:"
    });

    // Override parameters of the request object.
    const getXmlHttpRequestObject = connection.getXmlHttpRequestObject;
    connection.getXmlHttpRequestObject = function () {
      const xreq = getXmlHttpRequestObject();

      xreq.addEventListener("readystatechange", function () {
        if (this.readyState === 4) {
          if (this.status === 504) {
            store.commit(ADD_ERROR,
              `Error ${this.status}: ${this.statusText}`);
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

/**
 * This function will handle the errors of a Thrift API call. If the error
 * is a 401 error then it will redirect the user to the login page. Otherwise
 * it will add the error to the vuex store.
 * @callback [cb] - callback function which will be called on success.
 * @callback [onError] - callback function which will be called on
 * error. If it is not given the error will be added to the vuex store.
 */
const handleThriftError = function (cb, onError) {
  return (err, ...args) => {
    // Call the callback function with the rest of the arguments if it is given
    // and there are no errors.
    if (!err) {
      if (cb) cb.apply(this, args);
      return;
    }

    // Handle 401 errors.
    if (err instanceof Error) {
      const msg = err.message;
      if (msg.indexOf("Error code 401:") !== -1) {
        store.commit(PURGE_AUTH);

        router.push({
          name: "login",
          query: { "return_to": router.currentRoute.fullPath }
        }).catch(() => {});

        if (onError) onError(err);
        return;
      } else if (msg.search(/The product .* does not exist!/) > -1) {
        return router.replace({
          name: "404"
        }).catch(() => {});
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
  eventHub,
  handleThriftError,
  BaseService
};
