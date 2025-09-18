import ServiceClient from "@cc/server-info";
import { BaseService } from "./_base.service";

class ServerInfoService extends BaseService {
  constructor() {
    super("ServerInfo", ServiceClient, "v6.61", false);
  }
}

const serverInfoService = new ServerInfoService();

export default serverInfoService;
