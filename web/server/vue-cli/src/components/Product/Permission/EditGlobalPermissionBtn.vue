<template>
  <ConfirmDialog
    v-model="dialog"
    max-width="1000px"
    title="Global Permissions"
    @confirm="confirmPermissionChange"
  >
    <template v-slot:activator="{ props: activatorProps }">
      <v-btn
        v-bind="activatorProps"
        id="edit-global-permissions-btn"
        color="primary"
        class="mr-2"
        variant="outlined"
      >
        <template v-slot:prepend>
          <v-icon>mdi-shield-key</v-icon>
        </template>
        Edit global permission
      </v-btn>
    </template>

    <template v-slot:content>
      <EditGlobalPermission
        ref="editGlobalPermission"
      />
    </template>
  </ConfirmDialog>
</template>

<script setup>
import { ref } from "vue";

import ConfirmDialog from "@/components/ConfirmDialog";
import EditGlobalPermission from "./EditGlobalPermission";

const dialog = ref(false);
const editGlobalPermission = ref(null);

function confirmPermissionChange() {
  editGlobalPermission.value.saveAll();
}
</script>
