import Vue from "vue";
import {
  createXHRClient,
  createXHRConnection,
  TBufferedTransport,
  TJSONProtocol
} from "thrift";

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
    let productEndpoint = endpoint ? "/" + endpoint : "";
    const connection = createXHRConnection(host, port, {
      transport: TBufferedTransport,
      protocol: TJSONProtocol,
      path: `${productEndpoint}/v${api}/${this._serviceName}`
    });

    return createXHRClient(this._serviceClass, connection);
  }
}

export {
  eventHub,
  BaseService
};
