import ServiceClient from "@cc/server-info";
import { BaseService } from "./_base.service";

class ServerInfoService extends BaseService {
  constructor() {
    super("ServerInfo", ServiceClient);
  }
}

const serverInfoService = new ServerInfoService();

export default serverInfoService;
