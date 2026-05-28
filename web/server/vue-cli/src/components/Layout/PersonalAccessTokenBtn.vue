<template>
  <div>
    <ConfirmDialog
      v-model="deletePersonalAccessTokenDialog"
      confirm-btn-color="error"
      confirm-btn-label="Delete access token"
      cancel-btn-color="primary"
      title="Delete Personal Access Token"
      @confirm="deleteToken(token.name)"
    >
      <template v-slot:content>
        <p>
          You have selected to delete token with name
          <strong>{{ token.name }}</strong>.
        </p>
      </template>
    </ConfirmDialog>

    <ConfirmDialog
      v-model="reviewPersonalAccessTokenDialog"
      confirm-btn-label="OK"
      title="New Personal Access Token"
      @confirm="reviewPersonalAccessTokenDialog = false"
    >
      <template v-slot:content>
        <p>
          Token: <strong>{{ token.token }}</strong>
        </p>
        <p>
          Name: <strong>{{ token.name }}</strong>
        </p>
        <p>
          Expiration: <strong>{{ dateFormat(token.expiration) }}</strong>
        </p>
        <p>
          Description: <strong>{{ token.description }}</strong>
        </p>
        <p>
          Make sure to save this token, because it won't be available anymore
          after closing this window.
        </p>
      </template>
    </ConfirmDialog>

    <ConfirmDialog
      v-model="addPersonalAccessTokenDialog"
      confirm-btn-label="Add new token"
      title="Personal Access Tokens"
      @confirm="addNewToken()"
    >
      <template v-slot:activator="{ props }">
        <v-card flat>
          <v-card-text>
            <v-btn
              v-bind="props" 
              color="primary"
              block
              @click="loadTokens()"
            >
              <v-icon left>
                mdi-shield-account
              </v-icon>
              Personal access tokens
            </v-btn>
          </v-card-text>
        </v-card>
      </template>

      <template v-slot:content>
        <v-card>
          <v-table
            density="compact"
          >
            <template v-slot:default>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Last access</th>
                  <th>Expiration</th>
                  <th>Description</th>
                  <th>Delete</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="tok in accessTokens" :key="tok.token">
                  <td>{{ tok.name }}</td>
                  <td>{{ tok.lastAccess }}</td>
                  <td>{{ dateFormat(tok.expiration) }}</td>
                  <td>{{ tok.description }}</td>
                  <td>
                    <v-btn icon @click="confirmDelete(tok)">
                      <v-icon>mdi-delete</v-icon>
                    </v-btn>
                  </td>
                </tr>
              </tbody>
            </template>
          </v-table>

          <v-card-text>
            <v-form ref="newPersonalAccessTokenForm">
              <v-text-field
                ref="tokenNameField"
                v-model="newTokenName"
                :rules="[rules.required]"
                clearable
                label="New token name"
              />
              <v-text-field
                v-model="newTokenDescription"
                clearable
                label="New token description"
              />
              <v-text-field
                v-model.number="newTokenExpiration"
                :hint="personalTokenExpirationHint"
                :rules="[
                  rules.required,
                  rules.min,
                  rules.max
                ]"
                clearable
                label="New token expiration"
              />
            </v-form>
          </v-card-text>
        </v-card>
      </template>
    </ConfirmDialog>
  </div>
</template>

<script setup>
import ConfirmDialog from "@/components/ConfirmDialog";
import { authService, handleThriftError } from "@cc-api";
import { format } from "date-fns";
import { computed, onMounted, ref, watch } from "vue";

const addPersonalAccessTokenDialog = ref(false);
const deletePersonalAccessTokenDialog = ref(false);
const reviewPersonalAccessTokenDialog = ref(false);
const accessTokens = ref([]);
const token = ref({});
const newTokenName = ref("");
const newTokenDescription = ref("");
const newTokenExpiration = ref(1);
const maxTokenExpiration = ref(365);
const rules = ref(
  {
    required: v => !!v || "This field is required",
    min: v => v >= 1 || "Minimum length is 1 day!",
    max: v => v <= maxTokenExpiration.value || "Maximum length is "
      + maxTokenExpiration.value + " days!"
  }
);

const newPersonalAccessTokenForm = ref(null);

const personalTokenExpirationHint = computed(() => {
  return `Expiration must be between 1 and ${maxTokenExpiration.value} days`;
});

watch(addPersonalAccessTokenDialog, addPersonalTokenDialogOpen => {
  if (!addPersonalTokenDialogOpen) {
    newPersonalAccessTokenForm.value?.reset();
  }
});

onMounted(() => {
  getMaxTokenExpiration();
});

function addNewToken() {
  const _isFormValid = newPersonalAccessTokenForm.value?.validate();
  if (_isFormValid) {
    authService.getClient().newPersonalAccessToken(
      newTokenName.value,
      newTokenDescription.value,
      newTokenExpiration.value,
      handleThriftError(newToken => {
        token.value = newToken;
        reviewPersonalAccessTokenDialog.value = true;
        loadTokens();
        newPersonalAccessTokenForm.value?.reset();
      })
    );
  }
}

function getMaxTokenExpiration() {
  authService.getClient().getMaxTokenExpiration(
    handleThriftError(_maxTokenExpiration => {
      maxTokenExpiration.value = _maxTokenExpiration;
    }));
}

function confirmDelete(_token) {
  token.value = _token;
  deletePersonalAccessTokenDialog.value = true;
}

function dateFormat(dateStr) {
  return format(new Date(dateStr), "yyyy-MM-dd HH:mm:ss");
}

function deleteToken(tokenName) {
  authService.getClient().removePersonalAccessToken(tokenName,
    handleThriftError(() => {
      loadTokens();
      deletePersonalAccessTokenDialog.value = false;
    }));
}

function loadTokens() {
  authService.getClient().getPersonalAccessTokens(
    handleThriftError(_accessTokens => {
      accessTokens.value = _accessTokens;
    }));
}
</script>