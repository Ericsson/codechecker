import ServiceClient from "@cc/conf";
import { BaseService } from "./_base.service";

class ConfigurationService extends BaseService {
  constructor() {
    super("Configuration", ServiceClient);
  }
}

const configService = new ConfigurationService();

export default configService;
