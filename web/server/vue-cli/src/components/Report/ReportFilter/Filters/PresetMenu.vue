<template>
  <v-select
    v-model="activePresetId"
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
    <template #selection="{ item }">
      <span :class="{ 'preset-modified': isModified }">
        {{ item.name }}<template v-if="isModified"> *</template>
      </span>
    </template>

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
import isEqual from "lodash/isEqual";
import {
  authService,
  ccService,
  handleThriftError,
  prodService } from "@cc-api";
import { Permission } from "@cc/shared-types";


export default {
  name: "PresetMenu",

  expose : [ "onPresetApplied", "clearPresetState" ],

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
      activePresetId: null,
      querySnapshot: null,
      isModified: false,
    };
  },

  computed: {
    canSeeActions() {
      return this.isSuperUser || this.isAdminOfAnyProduct;
    },
  },

  watch: {
    "$route.query": {
      handler(newQuery) {
        if (!this.activePresetId || !this.querySnapshot) {
          this.isModified = false;
          return;
        }
        const normalize = q => {
          const sorted = {};
          for (const k of Object.keys(q).sort()) {
            const v = q[k];
            if (Array.isArray(v)) {
              sorted[ k ] = v.length === 1 ? v[ 0 ] : [ ...v ].sort();
            } else {
              sorted[k] = v;
            }
          }
          return sorted;
        };
        const normNew = normalize(newQuery);
        const normSnap = normalize(this.querySnapshot);
        this.isModified = !isEqual(normNew, normSnap);
      },
      deep: true,
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
      this.querySnapshot = null;
      try {
        this.activePresetId = id;
        this.$emit("apply-preset", id);
      } catch (e) {
        this.error = (e && e.message) ? e.message : "Failed to apply preset";
      } finally {
        this.applyingId = null;
      }
    },

    onPresetApplied(settledQuery) {
      this.querySnapshot = settledQuery
        ? { ...settledQuery }
        : { ...this.$route.query };
    },

    clearPresetState() {
      this.activePresetId = null;
      this.querySnapshot = null;
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

        if (this.activePresetId === id) {
          this.clearPresetState();
        }
      } catch (e) {
        this.error = (e && e.message) ? e.message : "Failed to delete preset";
      } finally {
        this.deletingId = null;
      }
    },

    handleClear() {
      this.clearPresetState();
      this.$emit("clear-preset");
    },
  },
};
</script>

<style scoped>
.preset-modified {
  color: orange;
  font-weight: bold;
}
</style>