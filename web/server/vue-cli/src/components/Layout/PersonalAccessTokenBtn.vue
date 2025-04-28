<template>
  <div>
    <confirm-dialog
      v-model="deleteDialog"
      confirm-btn-color="error"
      confirm-btn-label="Delete access token"
      cancel-btn-color="primary"
      @confirm="deleteToken(token.name)"
    >
      <template v-slot:title>
        Delete Personal Access Token
      </template>

      <template v-slot:content>
        <p>
          You have selected to delete token with name
          <strong>{{ token.name }}</strong>.
        </p>
      </template>
    </confirm-dialog>

    <confirm-dialog
      v-model="newDialog"
      confirm-btn-label="OK"
      @confirm="newDialog = false"
    >
      <template v-slot:title>
        New Personal Access Token
      </template>

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
    </confirm-dialog>

    <confirm-dialog
      v-model="dialog"
      confirm-btn-label="Add new token"
      @confirm="addNewToken()"
    >
      <template v-slot:activator="{ on }">
        <v-card flat>
          <v-card-text>
            <v-btn color="primary" block v-on="on" @click="loadTokens()">
              <v-icon left>
                mdi-shield-account
              </v-icon>
              Personal access tokens
            </v-btn>
          </v-card-text>
        </v-card>
      </template>

      <template v-slot:title>
        Personal Access Tokens
      </template>

      <template v-slot:content>
        <v-card>
          <v-simple-table dense>
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
          </v-simple-table>

          <v-card-text>
            <v-text-field
              ref="tokenNameField"
              v-model="newTokenName"
              label="New token name"
            />
            <v-text-field
              v-model="newTokenDescription"
              label="New token description"
            />
          </v-card-text>
        </v-card>
      </template>
    </confirm-dialog>
  </div>
</template>

<script>
import { format } from "date-fns";
import { authService, handleThriftError } from "@cc-api";
import ConfirmDialog from "@/components/ConfirmDialog";

export default {
  components: {
    ConfirmDialog
  },

  data() {
    return {
      dialog: false,
      deleteDialog: false,
      newDialog: false,
      accessTokens: [],
      token: {},
      newTokenName: "",
      newTokenDescription: ""
    };
  },

  methods: {
    addNewToken() {
      if (!this.newTokenName) {
        this.$refs.tokenNameField.focus();
        this.$refs.tokenNameField.error = true;
        return;
      }

      authService.getClient().newPersonalAccessToken(
        this.newTokenName,
        this.newTokenDescription,
        handleThriftError(newToken => {
          this.token = newToken;
          this.newDialog = true;
          this.loadTokens();
          this.newTokenName = "";
          this.newTokenDescription = "";
        })
      );
    },

    confirmDelete(token) {
      this.token = token;
      this.deleteDialog = true;
    },

    dateFormat(str) {
      return format(new Date(str), "yyyy-MM-dd HH:mm:ss");
    },

    deleteToken(name) {
      authService.getClient().removePersonalAccessToken(name,
        handleThriftError(() => {
          this.loadTokens();
          this.deleteDialog = false;
        }));
    },

    loadTokens() {
      authService.getClient().getPersonalAccessTokens(
        handleThriftError(accessTokens => {
          this.accessTokens = accessTokens;
        }));
    }
  }
};
</script>