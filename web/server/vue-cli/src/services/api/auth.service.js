import ServiceClient from '@cc/auth';
import { BaseService } from './_base.service';

class AuthService extends BaseService {
  constructor() {
    super('Authentication', ServiceClient);
  }
}

const authService = new AuthService();

export default authService;
