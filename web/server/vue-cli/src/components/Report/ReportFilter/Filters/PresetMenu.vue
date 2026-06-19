<template>
  <v-select
    v-model="activePresetId"
    clearable
    clear-icon="mdi-delete"
    item-title="name"
    item-value="id"
    label="Presets"
    :menu-props="{ scrim: true, scrollStrategy: 'close' }"
    :hide-details="true"
    :items="presets"
    :loading="loadingList"
    :disabled="saving || settingPreset || deletingId !== null"
    @focus="fetchPresets"
    @click:clear="handleClear"
  >
    <template #selection="{ item }">
      <span :class="{ 'preset-modified': isModified }">
        {{ item.title }}{{ isModified ? '*' : '' }}
      </span>
    </template>

    <template v-slot:item="{ props, item }">
      <v-list-item
        v-bind="props"
      >
        <template v-slot:append>
          <v-list-item-action end>
            <v-btn
              v-if="canSeeActions"
              variant="text"
              @click.stop="promptDelete(item.value)"
            >
              <v-icon
                v-if="deletingId === item.value"
                size="small"
              >
                mdi-loading
              </v-icon>
              <v-icon
                v-else
                size="large"
              >
                mdi-close-circle
              </v-icon>
            </v-btn>
          </v-list-item-action>
        </template>
      </v-list-item>
    </template>
  </v-select>

  <ConfirmDialog
    v-model="showDeleteConfirmDialog"
    max-width="400px"
    cancel-btn-color="primary"
    confirm-btn-label="Delete"
    confirm-btn-color="error"
    title="Delete Preset"
    @confirm="confirmDelete"
  >
    <template v-slot:content>
      Delete "<b>{{ pendingDeleteName }}</b>"? This action cannot be undone.
    </template>
  </ConfirmDialog>
</template>

<script setup>
import { computed, nextTick, onMounted, ref, watch } from "vue";
import isEqual from "lodash/isEqual";
import ConfirmDialog from "@/components/ConfirmDialog";
import {
  authService,
  ccService,
  handleThriftError,
  prodService } from "@cc-api";
import { Permission } from "@cc/shared-types";
import { useRoute } from "vue-router";

const emit = defineEmits([ "apply-preset", "clear-preset" ]);

const presets = ref([]);
const loadingList = ref(false);
const settingPreset = ref(false);
const deletingId = ref(null);
const saving = ref(false);
const error = ref(null);
const isSuperUser = ref(false);
const isAdminOfAnyProduct = ref(false);
const activePresetId = ref(null);
const querySnapshot = ref(null);
const isModified = ref(false);
const showDeleteConfirmDialog = ref(false);
const pendingDeleteId = ref(null);

const pendingDeleteName = computed(() => {
  const preset = presets.value.find(p => p.id === pendingDeleteId.value);
  return preset?.name || "";
});

const route = useRoute();

const canSeeActions = computed(() =>
  isSuperUser.value || isAdminOfAnyProduct.value
);

const activePresetName = computed(() => {
  const preset =
    presets.value.find(preset => preset.id === activePresetId.value);
  return preset?.name || "";
});

function checkModified(currentQuery) {
  if (!activePresetId.value || !querySnapshot.value) {
    isModified.value = false;
    return;
  }

  const normalize = query => {
    const sorted = {};
    for (const key of Object.keys(query).sort()) {
      const value = query[key];
      if (value === undefined || value === null || value === ""
        || value === "off") continue;
      if (Array.isArray(value)) {
        const filtered = value
          .filter(x => x !== undefined && x !== null && x !== ""
            && x !== "off")
          .map(String)
          .sort();
        if (filtered.length) {
          sorted[key] = filtered.length === 1 ? filtered[0] : filtered;
        }
      } else {
        sorted[key] = String(value);
      }
    }
    return sorted;
  };
  const normNew = normalize(currentQuery);
  const normSnap = normalize(querySnapshot.value);

  isModified.value = !isEqual(normNew, normSnap);
}

watch(() => route.query, newQuery => {
  checkModified(newQuery);
}, { deep: true });

watch(activePresetId, newVal => {
  if (newVal == null || settingPreset.value) return;
  settingPreset.value = true;
  emit("apply-preset", newVal);
  settingPreset.value = false;
});

onMounted(() => {
  authService.getClient().hasPermission(
    Permission.SUPERUSER,
    "",
    handleThriftError(_isSuperUser => {
      isSuperUser.value = _isSuperUser;

      if (!isSuperUser.value) {
        prodService.getClient().isAdministratorOfAnyProduct(
          handleThriftError(isAdmin => {
            isAdminOfAnyProduct.value = isAdmin;
          })
        );
      }
    })
  );
});

async function fetchPresets() {
  error.value = null;
  loadingList.value = true;

  try {
    const res = await new Promise((resolve, reject) => {
      ccService.getClient().listFilterPreset((err, presetList) => {
        if (err) return reject(err);
        resolve(presetList);
      });
    });

    if (!res) {
      presets.value = [];
      return;
    }

    presets.value = (Array.isArray(res) ? res : []).map(p => ({
      id: p.id.toNumber(),
      name: p.name,
    }));

  } catch (e) {
    error.value = (e && e.message) ? e.message : "Failed to load presets";
    presets.value = [];
  } finally {
    loadingList.value = false;
  }
}

function onPresetApplied(savedQuery) {
  querySnapshot.value = savedQuery ? { ...savedQuery } : { ...route.query };
  checkModified(route.query);
}

function clearPresetState() {
  activePresetId.value = null;
  querySnapshot.value = null;
  isModified.value = false;
}

function promptDelete(id) {
  pendingDeleteId.value = id;
  showDeleteConfirmDialog.value = true;
}

async function confirmDelete() {
  showDeleteConfirmDialog.value = false;
  if (pendingDeleteId.value !== null) {
    await deletePreset(pendingDeleteId.value);
    pendingDeleteId.value = null;
  }
}

async function deletePreset(id) {
  error.value = null;
  deletingId.value = id;

  try {
    await new Promise((resolve, reject) => {
      ccService.getClient().deleteFilterPreset(id, err => {
        if (err) return reject(err);
        resolve();
      });
    });

    presets.value = presets.value.filter(p => p.id !== id);

    if (activePresetId.value === id) {
      clearPresetState();
    }
  } catch (e) {
    error.value = (e && e.message) ? e.message : "Failed to delete preset";
  } finally {
    deletingId.value = null;
  }
}

function handleClear() {
  clearPresetState();
  emit("clear-preset");
}

async function selectPresetAfterSave(id) {
  const numId = typeof id?.toNumber === "function" ? id.toNumber() : id;
  await fetchPresets();
  activePresetId.value = numId;
  querySnapshot.value = { ...route.query };
  isModified.value = false;
}

async function selectPresetSilently(id) {
  settingPreset.value = true;
  activePresetId.value = id;
  await nextTick();
  settingPreset.value = false;
}

defineExpose({
  activePresetId,
  activePresetName,
  isModified,
  onPresetApplied,
  clearPresetState,
  selectPresetAfterSave,
  selectPresetSilently,
  fetchPresets,
});

</script>

<style scoped>
.preset-modified {
  color: orange;
  font-weight: bold;
}
</style>