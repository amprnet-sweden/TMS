<template>
  <v-app>
    <AppHeader/>

    <v-snackbar
      v-model="snackbar"
      location="top"
      :color="snackbarColor"
      :timeout="snackbarTimeout"
    >
      {{ snackbarMessage }}

      <template v-slot:actions>
        <v-btn
          color="white"
          variant="text"
          @click="snackbarMessage = null"
        >
          Stäng
        </v-btn>
      </template>
    </v-snackbar>

    <v-navigation-drawer
      v-if="username"
      v-model="drawer"
      :rail="rail"
      permanent
      @click="rail = false"
    >
      <v-list-item
        :title="username"
        :subtitle="roles.join(', ')"
        nav
      >
        <template v-slot:prepend>
          <v-avatar
            image="@/assets/profile-picture.jpg"
          ></v-avatar>
        </template>
        <template v-slot:append>
          <v-btn
            icon="mdi-chevron-left"
            variant="text"
            @click.stop="rail = !rail"
          ></v-btn>
        </template>
      </v-list-item>

      <v-divider></v-divider>

      <v-select
        label="Välj uppdrag"
        v-model="activeMission"
        :items="missions"
        item-value="id"
        item-title="name"
        single-line
        variant="solo"
        return-object
        hide-details
        class="mb-2"
        @update:model-value="onMissionSelected"
      ></v-select>

      <v-list density="compact" nav>
        <v-list-item
          v-for="item in items"
          :key="item.value"
          :prepend-icon="item.meta.icon"
          :title="item.meta.title"
          :value="item.path"
          @click.stop="select(item)"
        ></v-list-item>
      </v-list>
    </v-navigation-drawer>

    <v-main>
      <router-view/>
    </v-main>

    <AppFooter/>
  </v-app>
</template>

<script setup>
import {computed, onBeforeUnmount, onMounted, ref, watch} from "vue"
import {useRouter} from 'vue-router'
import {useDisplay} from "vuetify"
import {useUserStore} from '@/plugins/stores'
import {hasAnyRole, hasRole} from "@/plugins/keycloak"
import * as StompJs from '@stomp/stompjs'
import {Client} from '@stomp/stompjs'
import api, {
  eventBus,
  getMissionId,
  setMissionId,
  snackbarColor,
  snackbarMessage,
  snackbarTimeout,
  toast
} from '@/plugins/api'
import routes from "@/router/routes"
import AppHeader from "@/components/AppHeader.vue"
import AppFooter from "@/components/AppFooter.vue"

const store = useUserStore()

const superuser = computed(() => hasRole('tms-superuser'))
const missions = ref([])
const activeMission = ref(null)

const items = computed(() => routes.filter((item) => {
  const meta = item.meta || {}
  if (!meta.menu) {
    return false
  }
  if (meta.roles && !hasAnyRole(meta.roles)) {
    return false
  }
  if (item.path.includes(":mission") && !activeMission.value) {
    return false
  }
  return true
}))

store.$patch(null)

const router = useRouter()

function select(item) {
  const params = activeMission.value ? { mission: activeMission.value.id } : undefined
  router.push({ name: item.name, params })
}

const username = computed(() => store.user ? `${store.user.firstName} ${store.user.lastName}` : null)
const roles = computed(() => store.user?.roles || [])

async function checkLogin() {
  return fetch(`${import.meta.env.VITE_APP_API}/user`, {credentials: 'include'})
    .then(response => {
      if (response.ok) {
        return response.json().then(user => {
          store.$patch({user})
          return user
        })
      } else {
        console.warn('Not logged in', response.statusText)
        return null
      }
    })
}

function getCookie(name) {
  const value = `; ${document.cookie}`
  const parts = value.split(`; ${name}=`)
  if (parts.length === 2) return parts.pop().split(';').shift()
}

function connectWebSocket() {
  const client = new Client({
    brokerURL: `${import.meta.env.VITE_APP_WS}`,
    reconnectDelay: 10000,
    maxReconnectDelay: 60000,
    reconnectTimeMode: StompJs.ReconnectionTimeMode.EXPONENTIAL,
    connectHeaders: {
      authorization: `Bearer ${getCookie('JWT')}`,
    },
    debug: function (str) {
      //console.log(str)
    },
    beforeConnect: (client) => {
      client.connectHeaders.authorization = `Bearer ${getCookie('JWT')}`
    },
    onConnect: () => {
      console.log('connected in App')
      client.subscribe('/topic/notifications', (message, headers) => {
        console.log(`Received: ${message.body}`)
        console.log(`Headers: ${headers}`)
        const payload = JSON.parse(message.body)
        eventBus.emit(payload)
        if (payload.category === 'NOTICE' || payload.category === 'MESSAGE') {
          toast(payload)
        }
      });
      //client.publish({ destination: '/app/notification', body: JSON.stringify({ category: 'NOTICE', subject: 'First Message', message: 'Hello World!' })})
    },
    onWebSocketError: (error) => {
      console.error('WebSocket error', error)
    },
    onStompError: (frame) => {
      console.error('Broker reported error: ' + frame.headers['message'])
      console.error('Additional details: ' + frame.body)
    }
  })
  client.activate()
  return client
}

async function fetchMissions() {
  const path = superuser.value ? '/missions?status=ACTIVE' : '/user/missions'
  return api.get(path)
    .then(({data}) => {
      missions.value = data
      const userMission = getMissionId()
      if (userMission) {
        activeMission.value = missions.value.find(p => p.id === userMission)
      } else {
        activeMission.value = null
        setMissionId(null)
      }
      return missions.value
    })
}

function onMissionSelected(item) {
  const selected = missions.value.find(p => p.id === item.id)
  activeMission.value = selected
  setMissionId(selected?.id)
  eventBus.emit({category: 'CHANGE', domain: 'MISSION', id: selected?.id})
}

const {smAndDown} = useDisplay()
const drawer = ref(true)
const rail = ref(smAndDown.value)

const snackbar = ref(false)
watch(snackbarMessage, (msg) => {
  snackbar.value = !!msg
  setTimeout(() => (snackbarMessage.value = null), snackbarTimeout.value + 100)
})

function onMissionChanged(msg) {
  if (msg.category === 'CHANGE' && msg.domain === 'MISSION') {
    fetchMissions()
      .then(() => {
        //const route = router.currentRoute.value.matched[0]
        if (msg.id /*route.path.includes(':mission')*/) {
          router.replace({ name: 'dashboard', params: { mission: msg.id }})
        }
      })
  }
}

function setupListeners() {
  eventBus.on(onMissionChanged)
}

function shutdownListeners() {
  eventBus.off(onMissionChanged)
}

onMounted(() => {
  setupListeners()
  checkLogin()
    .then(connectWebSocket)
    .then(fetchMissions)
    .catch(console.error)
})

onBeforeUnmount(() => {
  shutdownListeners()
})
</script>

<style scoped>
:deep(.v-avatar.v-avatar--size-default.v-avatar--variant-flat) {
  --v-avatar-height: 36px !important;
}
</style>
