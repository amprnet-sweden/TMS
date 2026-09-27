<template>
  <v-app-bar density="comfortable">
    <template v-slot:prepend>
      <v-app-bar-nav-icon>
        <v-progress-circular
          v-if="loading"
          color="primary"
          indeterminate
        ></v-progress-circular>
        <v-icon v-else>mdi-radio-tower</v-icon>
      </v-app-bar-nav-icon>
    </template>

    <v-app-bar-title>TMS <sup>3.0</sup></v-app-bar-title>

    <v-spacer></v-spacer>

    <v-offline
      ping-url="https://www.technipelago.se"
      online-class="online"
      offline-class="offline"
      @detected-condition="onNetworkChange"
    >
      <template v-if="online">
        <v-icon color="green">mdi-circle-medium</v-icon>
      </template>
      <template v-else>
        <v-icon color="warning">mdi-alert</v-icon>
      </template>
    </v-offline>

    <v-btn icon="mdi-theme-light-dark" @click="toggleTheme"></v-btn>

    <v-btn icon>
      <v-menu>
        <template v-slot:activator="{ props }">
          <v-icon v-bind="props">mdi-dots-vertical</v-icon>
        </template>

        <v-list>
          <v-list-item
            title="Logga ut"
            @click="logout"
          >
            <template v-slot:prepend>
              <v-icon icon="mdi-logout"></v-icon>
            </template>
          </v-list-item>
        </v-list>
      </v-menu>
    </v-btn>
  </v-app-bar>
</template>

<script setup>
import {computed, ref} from 'vue'
import {useTheme} from 'vuetify'
import {VOffline} from 'v-offline'
import {loading} from '@/plugins/api'
import keycloak from "@/plugins/keycloak";

const theme = useTheme()

function toggleTheme() {
  theme.global.name.value = theme.global.current.value.dark ? 'light' : 'dark'
}

const online = ref(navigator.onLine)
const onNetworkChange = (status) => {
  online.value = status
}

function logout() {
  localStorage.removeItem('user')
  keycloak.logout({ redirectUri: import.meta.env.VITE_APP_URL })
}
</script>

<style scoped lang="sass">

</style>
