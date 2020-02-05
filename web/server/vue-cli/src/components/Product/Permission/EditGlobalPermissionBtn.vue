<template>
  <v-dialog
    v-model="dialog"
    persistent
    max-width="1000px"
    :scrollable="true"
  >
    <template v-slot:activator="{ on }">
      <v-btn
        color="primary"
        class="mr-2"
        v-on="on"
      >
        Edit global permission
      </v-btn>
    </template>

    <v-card>
      <v-card-title
        class="headline primary white--text"
        primary-title
      >
        Global permissions

        <v-spacer />

        <v-btn icon dark @click="dialog = false">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-card-title>

      <v-card-text class="pa-0">
        <edit-global-permission
          :bus="bus"
        />
      </v-card-text>

      <v-divider />

      <v-card-actions>
        <v-spacer />

        <v-btn
          color="error"
          text
          @click="dialog = false"
        >
          Cancel
        </v-btn>

        <v-btn
          color="primary"
          text
          @click="confirmPermissionChange"
        >
          Save
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script>
import Vue from "vue";

import EditGlobalPermission from "./EditGlobalPermission";

export default {
  name: "EditGlobalPermissionBtn",
  components: {
    EditGlobalPermission
  },

  data() {
    return {
      dialog: false,
      bus: new Vue()
    };
  },

  methods: {
    confirmPermissionChange() {
      this.bus.$emit("save");
    }
  }
}
</script>
