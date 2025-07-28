import ServiceClient from "@cc/conf";
import { BaseService } from "./_base.service";

class ConfigurationService extends BaseService {
  constructor() {
    super("Configuration", ServiceClient, "v6.61", false);
  }
}

const configService = new ConfigurationService();

export default configService;
