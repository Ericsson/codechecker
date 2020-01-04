<template>
  <h3>Run List</h3>
</template>

<script>
import { authService, ccService, confService, prodService } from '@cc-api';

export default {
  name: 'RunList',
  mounted() {
    authService.getClient().getAuthParameters((err, res) => {
      console.log("authService", res);
    });

    ccService.getClient().getPackageVersion((err, res) => {
      console.log("ccService", res);
    });

    confService.getClient().getNotificationBannerText((err, res) => {
      console.log("confService", res);
    });

    prodService.getClient().getPackageVersion((err, res) => {
      console.log("prodService", res);
    });
  }
}
</script>
