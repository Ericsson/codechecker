<template>
  <v-container
    class="fill-height"
    fluid
  >
    <v-row
      align="center"
      justify="center"
    >
      <v-col
        cols="12"
        sm="8"
        md="3"
      >
        <v-card
          class="elevation-1 pa-8"
          variant="flat"
        >
          <v-card-title>
            <v-container
              class="text-center mt-6 mb-4"
            >
              <v-avatar
                id="avatar"
                color="primary"
                :size="120"
              >
                <v-icon
                  :size="100"
                >
                  mdi-account
                </v-icon>
              </v-avatar>
              <div
                class="text-h4 text-grey"
              >
                Login
              </div>
            </v-container>
          </v-card-title>
          <v-card-actions
            v-if="providers.length !== 0"
            id="btn-container"
            class="d-flex justify-center flex-column"
          >
            <v-btn
              block
              size="x-large"
              color="primary"
              @click="ssoButtonHandleClickEvent"
            >
              {{ ssoButtonText }}
            </v-btn>
            <a
              href="#"
              class="text-button text-no-wrap"
              @click.prevent="toggleOtherLoginOptions"
            >
              {{ optionsShow ? 'Hide other options' : 'Show other options' }}
            </a>
          </v-card-actions>
          <v-expand-transition>
            <v-responsive
              v-if="optionsShow"
            >
              <v-card-text class="px-0 pb-0">
                <alerts
                  :success="success"
                  success-msg="Successfully logged in!"
                  :error="error"
                  :error-msg="errorMsg"
                />
                <v-form v-model="isDataValid">
                  <v-text-field
                    v-model="username"
                    autocomplete="username"
                    label="Username"
                    name="username"
                    append-inner-icon="mdi-account"
                    type="text"
                    required
                    variant="outlined"
                    :rules="[() => !!username || 'This field is required']"
                    :placeholder="placeholder"
                    @keyup.enter="login"
                  />

                  <v-text-field
                    id="password"
                    v-model="password"
                    autocomplete="current-password"
                    label="Password"
                    name="password"
                    append-inner-icon="mdi-lock"
                    type="password"
                    required
                    variant="outlined"
                    :rules="[() => !!password || 'This field is required']"
                    :placeholder="placeholder"
                    @keyup.enter="login"
                  />
                </v-form>
              </v-card-text>
              <v-card-actions
                id="btn-container"
                class="d-flex justify-center flex-column"
              >
                <v-btn
                  id="login-btn"
                  block
                  size="x-large"
                  color="primary"
                  variant="flat"
                  @click="login()"
                >
                  Login
                </v-btn>
              </v-card-actions>
            </v-responsive>
          </v-expand-transition>
        </v-card>
      </v-col>
    </v-row>
    <v-dialog
      v-model="dialog"
      width="500"
      :scrollable="true"
    >
      <v-card>
        <v-card-title
          class="headline primary text-white"
        >
          Login Methods

          <v-spacer />

          <v-btn
            variant="text"
            icon="mdi-close"
            @click="dialog = false"
          />
        </v-card-title>
        <v-card-text>
          <v-btn
            v-for="provider in providers"
            :id="`login-btn-${provider}`"
            :key="provider"
            block
            size="x-large"
            color="primary"
            style="margin-top: 10px"
            @click="oauth(provider)"
          >
            Login with {{ provider }}
          </v-btn>
        </v-card-text>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { useStore } from "vuex";
import { useRoute, useRouter } from "vue-router";
import { LOGIN } from "@/store/actions.type";
import { authService, handleThriftError } from "@cc-api";
import Alerts from "@/components/Alerts";

const store = useStore();
const route = useRoute();
const router = useRouter();

const placeholder = ref("");
const username = ref("");
const password = ref("");
const success = ref(false);
const error = ref(false);
const errorMsg = ref(null);
const isDataValid = ref(false);
const providers = ref([]);
const dialog = ref(false);
const on = ref(false);
const optionsShow = ref(false);

const authParams = computed(() => store.getters.authParams);
const isAuthenticated = computed(() => store.getters.isAuthenticated);

const ssoButtonText = computed(() => {
  return providers.value.length === 1 ?
    `Login with ${providers.value[0]}` : "SSO Login";
});

watch(username, () => {
  resetPlaceholder();
});

watch(password, () => {
  resetPlaceholder();
});

onMounted(() => {
  fixAutocomplete();
  getProviders();
  if (isAuthenticated.value && authParams.value?.sessionStillActive) {
    const returnTo = route.query["return_to"];
    router.replace(returnTo || { name: "products" });
  }
});

function openModal() {
  dialog.value = true;
  on.value = true;
}

function toggleOtherLoginOptions() {
  optionsShow.value = !optionsShow.value;
}

function ssoButtonHandleClickEvent() {
  return providers.value.length === 1 ?
    oauth(providers.value[0]) : openModal();
}

function login() {
  if (!username.value || !password.value) {
    return;
  }

  store.dispatch(LOGIN,
    { username: username.value, password: password.value, type: "password" }
  ).then(() => {
    success.value = true;
    error.value = false;

    const returnTo = route.query["return_to"];
    router.replace(returnTo || { name: "products" });
  }).catch(err => {
    errorMsg.value = `Failed to log in! ${err.message}`;
    error.value = true;
  });
}

function getProviders() {
  new Promise(
    resolve => {
      authService.getClient().getOauthProviders(
        handleThriftError(providers => {
          resolve(providers);
        }));
    }
  ).then(_providers => {
    if (_providers) {
      providers.value = _providers;
    }
    optionsShow.value = providers.value.length === 0;
  }).catch(err => {
    errorMsg.value = `Providers list was passed incorrectly. ${err.message}`;
    error.value = true;
  });
}

function oauth(provider) {
  new Promise(resolve => {
    localStorage.setItem("oauth_provider", provider);
    authService.getClient().createLink(provider,
      handleThriftError(url => {
        resolve(url);
      }));
  }).then(url => {
    if (url) {
      success.value = false;
      error.value = false;

      router.push({ path: url });
    } else {
      errorMsg.value = `Server returned an invalid URL: ${url}`;
      error.value = true;
    }
  }).catch(err => {
    errorMsg.value = `Failed to access link. ${err.message}`;
    error.value = true;
  });
}

/**
 * Set placeholder when browser autocompletes username or password to raise
 * v-text-field labels.
 * See: https://github.com/vuetifyjs/vuetify/issues/3679
 */
function fixAutocomplete() {
  let times = 0;
  const interval = setInterval(() => {
    times += 1;
    if (placeholder.value || times === 20) {
      clearInterval(interval);
    }

    const username_query =
        document.querySelector("input[name=\"username\"]:-webkit-autofill");
    const password_query =
        document.querySelector("input[name=\"password\"]:-webkit-autofill");

    if (username_query || password_query) {
      placeholder.value = "`\u0020`";
    }
  }, 100);
}

/**
 * We set the placeholder back to null if the user edited this field.
 * This way the label of the text field will be moved properly.
 * See the fixAutocomplete function for more information.
 */
function resetPlaceholder() {
  placeholder.value = null;
}
</script>

<style lang="scss" scoped>
.v-card {
  overflow: visible;
}
#btn-container > button {
  margin: 0 !important;
  margin-top: 10px !important;
}

#avatar {
  position: absolute;
  margin: 0 auto;
  left: 0;
  right: 0;
  top: -70px;
  width: 95px;
  height: 95px;
  border-radius: 50%;
  z-index: 9;
  padding: 15px;
  box-shadow: 0px 2px 2px rgba(0, 0, 0, 0.1);
}

#login-btn {
  font-size: 1.2em;
}
</style>