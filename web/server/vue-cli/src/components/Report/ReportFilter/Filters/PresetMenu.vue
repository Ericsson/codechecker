<template>
  <div class="d-flex align-center">
    <v-menu
      v-model="menuOpen"
      offset-y
      :close-on-content-click="false"
    >
      <template v-slot:activator="{ on, attrs }">
        <v-btn
          outlined
          :loading="loadingList"
          :disabled="saving || applyingId !== null || deletingId !== null"
          v-bind="attrs"
          v-on="on"
        >
          Presets
          <v-icon right>
            mdi-menu-down
          </v-icon>
        </v-btn>
      </template>

      <v-card min-width="320">
        <v-card-title class="py-2">
          <span class="text-subtitle-2">Presets</span>
          <v-spacer />
          <v-btn
            icon
            small
            :disabled="loadingList"
            @click="fetchPresets"
          >
            <v-icon>
              mdi-refresh
            </v-icon>
          </v-btn>
        </v-card-title>

        <v-divider />

        <div v-if="loadingList" class="pa-4 d-flex justify-center">
          <v-progress-circular indeterminate />
        </div>

        <v-list v-else dense>
          <v-list-item v-if="presets.length === 0">
            <v-list-item-title class="text--secondary">
              No presets yet
            </v-list-item-title>
          </v-list-item>

          <v-list-item
            v-for="p in presets"
            :key="p.id"
            @click="applyPreset(p.id)"
          >
            <v-list-item-content>
              <v-list-item-title>
                {{ p.name }}
              </v-list-item-title>
            </v-list-item-content>

            <v-list-item-action>
              <!-- Apply spinner -->
              <v-progress-circular
                v-if="applyingId === p.id"
                indeterminate
                size="18"
              />
              <!-- Delete spinner -->
              <v-progress-circular
                v-else-if="deletingId === p.id"
                indeterminate
                size="18"
              />
              <!-- Trash -->
              <v-btn
                v-if="canSeeActions"
                icon
                small
                title="Delete"
                @click.stop="deletePreset(p.id)"
              >
                <v-icon>
                  mdi-delete
                </v-icon>
              </v-btn>
            </v-list-item-action>
          </v-list-item>
        </v-list>

        <v-divider />

        <v-alert
          v-if="error"
          type="error"
          dense
          class="ma-2"
        >
          {{ error }}
        </v-alert>
      </v-card>
    </v-menu>
  </div>
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
      menuOpen: false,
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
    },
  },

  watch: {
    menuOpen(open) {
      if (open) {
        this.fetchPresets();
      }
    },
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
        this.menuOpen = false;
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
  },
};
</script>