<template>
  <ConfirmDialog
    v-model="dialog"
    max-width="1000px"
    title="Global Permissions"
    icon="mdi-shield-key"
    @confirm="confirmPermissionChange"
  >
    <template v-slot:activator="{ props: activatorProps }">
      <v-btn
        id="edit-global-permissions-btn"
        class="mr-2"
        v-bind="activatorProps"
        color="primary"
        height="40"
        variant="tonal"
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
