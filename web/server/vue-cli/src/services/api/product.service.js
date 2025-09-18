import ServiceClient from "@cc/prod";
import { BaseService } from "./_base.service";

class ProductsService extends BaseService {
  constructor() {
    super("Products", ServiceClient, "v6.61", false);
  }
}

const prodService = new ProductsService();

export default prodService;
