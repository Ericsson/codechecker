import ServiceClient from "@cc/prod";
import { BaseService } from "./_base.service";

class ProductsService extends BaseService {
  constructor() {
    super("Products", ServiceClient);
  }
}

const prodService = new ProductsService();

export default prodService;
