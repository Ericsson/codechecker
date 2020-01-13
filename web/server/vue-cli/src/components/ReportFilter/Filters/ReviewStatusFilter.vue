<template>
  <v-card>
    <v-toolbar flat>
      <v-toolbar-title>Review status</v-toolbar-title>
      <v-spacer />
      <v-toolbar-items>
        <v-btn icon>
          <v-icon>mdi-delete</v-icon>
        </v-btn>
        <v-menu
          :close-on-content-click="false"
          :nudge-width="400"
          offset-x
        >
          <template v-slot:activator="{ on }">
            <v-btn icon v-on="on">
              <v-icon>mdi-settings</v-icon>
            </v-btn>
          </template>

          <v-list class="pa-2">
            <v-list-item-group
              v-model="selected"
              active-class="light-blue--text"
              lighten-4
              multiple
            >
              <v-list-item
                v-for="option in options"
                :key="option.id"
              >
                <template v-slot:default="{ active }">
                  <v-list-item-action class="mr-5">
                    <v-checkbox :value="active" color="#28a745" />
                  </v-list-item-action>

                  <v-list-item-icon class="mr-2">
                    <review-status-icon :status="option.id" />
                  </v-list-item-icon>

                  <v-list-item-content>
                    <v-list-item-title v-text="option.value" />
                  </v-list-item-content>

                  <v-chip color="#878d96" outlined>
                    {{ option.count }}
                  </v-chip>
                </template>
              </v-list-item>
            </v-list-item-group>
          </v-list>
        </v-menu>
      </v-toolbar-items>
    </v-toolbar>

    No filter
  </v-card>
</template>

<script>
import { VCard } from "Vuetify/VCard";
import { VToolbar, VToolbarTitle, VToolbarItems } from "Vuetify/VToolbar";
import VSpacer from "Vuetify/VGrid/VSpacer";
import { VBtn } from "Vuetify/VBtn";
import VIcon from "Vuetify/VIcon/VIcon";
import VMenu from "Vuetify/VMenu/VMenu";
import {
  VList,
  VListItem,
  VListItemAction,
  VListItemContent,
  VListItemIcon,
  VListItemGroup,
  VListItemTitle
} from "Vuetify/VList";
import VCheckbox from "Vuetify/VCheckbox/VCheckbox";
import VChip from "Vuetify/VChip/VChip";

import { ReviewStatus } from "@cc/report-server-types";

import { ReviewStatusIcon } from "@/components/icons";

export default {
  name: 'ReviewStatusFilter',
  components: {
    VCard, VToolbar, VToolbarTitle, VToolbarItems, VSpacer, VBtn, VIcon, VMenu,
    VList, VListItem, VListItemAction, VListItemContent, VListItemIcon,
    VListItemGroup, VListItemTitle, VCheckbox, VChip,
    ReviewStatusIcon
  },
  data() {
    return {
      selected: [],
      options: [
        { id: ReviewStatus.UNREVIEWED, value: 'Unreviewed', count: 3 },
        { id: ReviewStatus.CONFIRMED, value: 'Confirmed', count: 7 },
        { id: ReviewStatus.FALSE_POSITIVE, value: 'False positive', count: 0 },
        { id: ReviewStatus.INTENTIONAL, value: 'Intentional', count: 10 },
      ]
    };
  }
}
</script>
