<template>
  <v-select
    clearable
    :items="presets"
    item-text="name"
    item-value="id"
    label="Presets"
    :loading="loadingList"
    :disabled="saving || applyingId !== null || deletingId !== null"
    @focus="fetchPresets"
    @click:clear="handleClear"
  >
    <template #item="{ item }">
      <v-list-item-content
        @click="applyPreset(item.id)"
      >
        <v-list-item-title>
          {{ item.name }}
        </v-list-item-title>
      </v-list-item-content>
      <v-list-item-action v-if="canSeeActions">
        <v-btn
          :disabled="saving || applyingId !== null || deletingId !== null"
          icon
          @click="deletePreset(item.id)"
        >
          <v-icon
            v-if="deletingId === item.id"
            small
          >
            mdi-loading
          </v-icon>
          <v-icon v-else small>
            mdi-delete
          </v-icon>
        </v-btn>
      </v-list-item-action>
    </template>
  </v-select>
</template>

<script>
import {
  authService,
  ccService,
  handleThriftError,
  prodService } from "@cc-api";
import { Permission } from "@cc/shared-types";

// import { is } froAEm "core-js/core/object";
// import { ccService, handleThriftError } from "@cc-api";


export default {
  name: "PresetMenu",

  props: {

  },

  data() {
    return {
      presets: [],
      loadingList: false,
      applyingId: null,
      deletingId: null,
      saving: false,
      error: null,
      isSuperUser: false,
      isAdminOfAnyProduct: false,
    };
  },

  computed: {
    canSeeActions() {
      return this.isSuperUser || this.isAdminOfAnyProduct;
    }
  },

  watch: {
  },

  created() {
    authService.getClient().hasPermission(
      Permission.SUPERUSER,
      "",
      handleThriftError(isSuperUser => {
        this.isSuperUser = isSuperUser;

        if (!isSuperUser) {
          prodService.getClient().isAdministratorOfAnyProduct(
            handleThriftError(isAdmin => {
              this.isAdminOfAnyProduct = isAdmin;
            })
          );
        }
      })
    );
  },


  methods: {
    async fetchPresets() {
      this.error = null;
      this.loadingList = true;

      try {
        const res = await new Promise((resolve, reject) => {
          ccService.getClient().listFilterPreset((err, presetList) => {
            if (err) return reject(err);
            resolve(presetList);
          });
        });

        if (!res) {
          this.presets = [];
          return;
        }

        this.presets = (Array.isArray(res) ? res : []).map(p => ({
          id: p.id.toNumber(),
          name: p.name,
        }));

      } catch (e) {
        this.error = (e && e.message) ? e.message : "Failed to load presets";
        this.presets = [];
      } finally {
        this.loadingList = false;
      }
    },

    async applyPreset(id) {
      this.error = null;
      this.applyingId = id;
      try {
        this.$emit("apply-preset", id);
      } catch (e) {
        this.error = (e && e.message) ? e.message : "Failed to apply preset";
      } finally {
        this.applyingId = null;
      }
    },

    async deletePreset(id) {
      this.error = null;
      this.deletingId = id;

      try {
        await new Promise((resolve, reject) => {
          ccService.getClient().deleteFilterPreset(id, err => {
            if (err) return reject(err);
            resolve();
          });
        });

        this.presets = this.presets.filter(p => p.id !== id);
      } catch (e) {
        this.error = (e && e.message) ? e.message : "Failed to delete preset";
      } finally {
        this.deletingId = null;
      }
    },

    handleClear() {
      this.$emit("clear-preset");
    },
  },
};
</script>