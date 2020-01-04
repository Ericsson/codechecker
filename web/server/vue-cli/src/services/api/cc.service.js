import ServiceClient from '@cc/db-access';
import { BaseService } from './_base.service';

class CodeCheckerService extends BaseService {
  constructor() {
    super('CodeCheckerService', ServiceClient);
  }
}

const ccService = new CodeCheckerService();

export default ccService;
