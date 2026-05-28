<template>
  <ConfirmDialog
    v-model="dialog"
    content-class="select-review-status-dialog"
    persistent
    max-width="600px"
    title="Change review status"
    @confirm="confirmReviewStatusChange"
    @cancel="cancelReviewStatusChange"
  >
    <template v-slot:activator="{}">
      <v-container
        fluid
        class="px-0"
      >
        <v-row>
          <v-col
            cols="auto"
            class="pa-0 mx-4"
          >
            <v-select
              :model-value="value.status"
              :items="items"
              :hide-details="true"
              :menu-props="{ contentClass: 'select-review-status-menu' }"
              :disabled="isReviewStatusDisabled"
              label="Set review status"
              item-title="label"
              item-value="id"
              class="select-review-status small"
              height="0"
              flat
              density="compact"
              variant="solo"
              @update:model-value="onReviewStatusChange"
            >
              <template v-slot:selection="{ item }">
                <div class="d-flex align-center">
                  <review-status-icon
                    :status="item.value"
                    :size="16"
                    class="mx-2"
                  />
                  <span>{{ item.title }}</span>
                </div>
              </template>

              <template v-slot:item="{ item, props: itemProps }">
                <v-list-item
                  v-bind="itemProps"
                >
                  <template v-slot:prepend>
                    <review-status-icon
                      :status="item.raw.id"
                      :size="16"
                      class="mx-2"
                    />
                  </template>
                </v-list-item>
              </template>
            </v-select>
          </v-col>
        </v-row>
      </v-container>
    </template>
    <template v-slot:content>
      <v-container>
        <p v-if="isClosing">
          When setting review status to false positive or intentional, the
          report is considered as closed. The date of closing is the current
          time.
        </p>

        <v-alert
          v-if="reportsReviewedInSource.length"
          density="compact"
          variant="outlined"
          type="error"
        >
          <p>
            Review status of the following reports are given as source code
            comment or review status config YAML file. Their review status
            will not change. However, this option sets the review status of
            all reports without source code comment even in the future. This
            may result that a bug is assigned two different review statuses.
            We don't recommend setting review status in this interface for
            reports which already have one as a source code comment!
          </p>

          <div
            v-for="r in reportsReviewedInSource"
            :key="parseInt(r.reportId)"
          >
            <detection-status-icon
              :status="r.detectionStatus"
              :size="16"
            />
            <review-status-icon
              :status="r.reviewData.status"
              :size="16"
            />
            <router-link
              :to="{ name: 'report-detail', query: {
                ...router.currentRoute.value.query,
                'report-id': r.reportId,
                'report-hash': undefined
              }}"
              target="_blank"
            >
              {{ r.$runName }}:
              {{ r.checkedFile.replace(/^.*[\\/]/, "") }}:
              L{{ r.line }}
              <strong
                v-if="parseInt(r.reportId) === parseInt(report.reportId)"
              >
                (current report)
              </strong>
            </router-link>
          </div>
        </v-alert>
        <v-textarea
          v-model="reviewStatusMessage"
          variant="outlined"
          name="reviewStatusMessage"
          label="(Optionally) Explain the status change..."
          class="pa-0"
          :hide-details="true"
        />
      </v-container>
    </template>
  </ConfirmDialog>
</template>

<script setup>
import { DetectionStatusIcon, ReviewStatusIcon } from "@/components/Icons";
import { useReviewStatus } from "@/composables/useReviewStatus";
import { ccService } from "@cc-api";
import { ReviewStatus } from "@cc/report-server-types";
import { computed, ref } from "vue";
import { useRouter } from "vue-router";
import { useStore } from "vuex";
import ConfirmDialog from "@/components/ConfirmDialog";

const props = defineProps({
  value: { type: Object, default: () => {} },
  report: { type: Object, default: () => {} },
  onConfirm: { type: Function, default: () => {} }
});

const emit = defineEmits([ "update:value" ]);

const reviewStatus = useReviewStatus();

const items = ref([]);
const dialog = ref(false);
const oldReviewStatus = ref(0);
const newReviewStatus = ref(0);
const reviewStatusMessage = ref(null);
const sameReports = ref(null);
const store = useStore();
const router = useRouter();

items.value = Object.values(ReviewStatus).map(_id => {
  return {
    id: _id,
    label: reviewStatus.reviewStatusFromCodeToString(parseInt(_id))
  };
});

const currentProductConfig = computed(
  () => store.getters.currentProductConfig
);
const currentUser = computed(() => store.getters.currentUser);

const isReviewStatusDisabled = computed(() => {
  if (!currentProductConfig.value) return true;
  return currentProductConfig.value.isReviewStatusChangeDisabled;
});

const reportsReviewedInSource = computed(() => {
  if (!sameReports.value) return [];
  return sameReports.value.filter(report => report.reviewData.isInSource);
});

const isClosing = computed(() => {
  return props.value.status === ReviewStatus.FALSE_POSITIVE ||
    props.value.status === ReviewStatus.INTENTIONAL;
});

async function onReviewStatusChange(_value) {
  oldReviewStatus.value = props.value.status;
  emit("update:value", { ...props.value, status: _value });
  reviewStatusMessage.value = props.value.message;
  newReviewStatus.value = _value;

  dialog.value = true;

  sameReports.value = await ccService.getSameReports(props.report.bugHash);
}

function confirmReviewStatusChange() {
  const _comment = reviewStatusMessage.value || "";
  const _author = currentUser.value || "Anonymous";
  props.onConfirm(_comment, newReviewStatus.value, _author);
  dialog.value = false;
}

function cancelReviewStatusChange() {
  emit("update:value", { ...props.value, status: oldReviewStatus.value });
  dialog.value = false;
}
</script>

<style lang="scss" scoped>
:deep(.v-select__selections input) {
  display: none;
}

:deep(.v-select.v-text-field--outlined) {
  .theme--light.v-label {
    background-color: #fff;
  }
}
</style>
