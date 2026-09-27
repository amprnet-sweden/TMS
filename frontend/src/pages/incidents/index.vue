<template>
  <v-container fluid>
    <v-card>
      <v-card-text>
        <v-toolbar density="comfortable" color="primary">
          <v-toolbar-title>Ärenden</v-toolbar-title>

          <v-select
            placeholder="Insatsgrupp"
            v-model="serviceFilter"
            multiple
            :items="serviceItems"
            item-value="id"
            item-title="name"
            chips
            closable-chips
            hide-details
            single-line
            density="compact"
            @update:model-value="fetchIncidents"
          ></v-select>

          <v-select
            placeholder="Status"
            v-model="statusFilter"
            multiple
            :items="statusItems"
            item-value="id"
            item-title="name"
            chips
            closable-chips
            hide-details
            single-line
            density="compact"
            @update:model-value="fetchIncidents"
          ></v-select>

          <v-select
            placeholder="Prioritet"
            v-model="priorityFilter"
            multiple
            :items="priorityItems"
            item-value="id"
            item-title="name"
            chips
            closable-chips
            hide-details
            single-line
            density="compact"
            @update:model-value="fetchIncidents"
          ></v-select>

          <v-toolbar-items>
            <v-btn
              variant="plain"
              :icon="reloadIcon"
              @click="reload"
            ></v-btn>
            <v-btn variant="elevated" rounded="0" color="warning" accesskey="n" @click="add">
              <v-icon>mdi-plus</v-icon>
              <span class="hidden-sm-and-down">Skapa nytt ärende</span>
            </v-btn>
          </v-toolbar-items>
        </v-toolbar>
        <v-data-table
          :headers="headers"
          :items="items"
          item-value="id"
          :search="search"
          @click:row="select"
        >
          <template v-slot:[`item.assigned`]="{ item }">
            <span :title="item.assignedTo?.name">{{ item.assignedTo?.initials }}</span>
          </template>
          <template v-slot:[`item.service`]="{ item }">
            <v-icon :icon="item.service?.icon" :color="item.service?.color" class="me-1"></v-icon>
            {{ item.service?.name }}
          </template>
          <template v-slot:[`item.status`]="{ item }">
            <v-icon :icon="item.status?.icon" :color="item.status?.color" class="me-1"></v-icon>
            {{ item.status?.name }}
          </template>
          <template v-slot:[`item.priority`]="{ item }">
            <v-icon :icon="item.priority?.icon" :color="item.priority?.color" class="me-1"></v-icon>
            {{ item.priority?.name }}
          </template>
          <template v-slot:[`item.created`]="{ item }">
            <span class="text-no-wrap">{{ formatDateTime(item.created) }}</span>
          </template>
          <template v-slot:[`footer.prepend`]>
            <v-text-field
              v-model="search"
              prepend-icon="mdi-magnify"
              clearable
              hide-details
              single-line
              autofocus
              variant="underlined"
              class="pb-3 me-5"
            ></v-text-field>
          </template>
        </v-data-table>
      </v-card-text>
    </v-card>
  </v-container>
</template>

<script setup>
import {computed, onBeforeUnmount, onMounted, ref} from "vue"
import {useRouter, onBeforeRouteUpdate} from "vue-router"
import {useDisplay} from 'vuetify'
import api, {eventBus, getMissionId, toast} from "@/plugins/api"
import {hasAnyRole} from "@/plugins/keycloak"
import {TMS_ADMIN, TMS_OBSERVER, TMS_OPERATOR, TMS_SUPERUSER} from "@/roles"
import dayjs from "dayjs";

const {mdAndUp} = useDisplay()
const allHeaders = [
  {key: 'name', title: 'Namn', mobile: true},
  {key: 'description', title: 'Beskrivning', cellProps: {'class': 'text-truncate'}, maxWidth: '400px', mobile: false},
  {key: 'assigned', value: 'assignedTo.initials', title: 'Tilldelad', mobile: false},
  {key: 'service', value: 'service.name', title: 'Insatsgrupp', mobile: true},
  {key: 'status', value: 'status.name', title: 'Status', mobile: true},
  {key: 'priority', value: 'priority.name', title: 'Prioritet', mobile: true},
  {key: 'created', title: 'Skapat', mobile: false},
]
const headers = computed(() => allHeaders.filter(h => h.mobile || mdAndUp.value))
const items = ref([])
const refresh = ref(false)
const serviceFilter = ref([])
const statusFilter = ref([])
const priorityFilter = ref([])
const search = ref(null)
const router = useRouter()
const serviceItems = ref([])
const userItems = ref([])
const statusItems = ref([])
const priorityItems = ref([])

async function fetchMetadata() {
  return api.get(`/missions/${getMissionId()}/members`)
    .then(({data}) => (userItems.value = data))
    .then(() => api.get('/metadata'))
    .then(({data}) => {
      serviceItems.value = data.services
      statusItems.value = data.statuses
      priorityItems.value = data.priorities
    }).catch(() => false)
}

async function fetchIncidents() {
  clearDblClickTimer()
  return api.get('/incidents' + getFilters())
    .then(({data}) => {
      items.value = data
      refresh.value = false
    }).catch(console.error)
}

function getFilters() {
  const parts = []
  if (serviceFilter.value.length) {
    parts.push('service=' + serviceFilter.value.join(','))
  }
  if (statusFilter.value.length) {
    parts.push('status=' + statusFilter.value.join(','))
  }
  if (priorityFilter.value.length) {
    parts.push('priority=' + priorityFilter.value.join(','))
  }
  return parts.length ? '?' + parts.join('&') : ''
}

function add() {
  router.push({ name: 'incident', params: { mission: getMissionId(), id: '0' } })
}

const reloadIcon = computed(() => reloadTimer.value !== undefined ? 'mdi-auto-mode' : (refresh.value ? 'mdi-reload-alert' : 'mdi-reload'))

const reloadTimer = ref(undefined)
let dblclickTimer = undefined

function reload() {
  if (dblclickTimer !== undefined) {
    clearDblClickTimer()
    autoReload()
  } else {
    dblclickTimer = setTimeout(fetchIncidents, 300)
  }
}

function clearDblClickTimer() {
  if (dblclickTimer !== undefined) {
    clearTimeout(dblclickTimer)
    dblclickTimer = undefined
  }
}

function clearReloadTimer() {
  if (reloadTimer.value !== undefined) {
    clearInterval(reloadTimer.value)
    reloadTimer.value = undefined
  }
}

function autoReload() {
  if (reloadTimer.value !== undefined) {
    clearReloadTimer()
  } else {
    reloadTimer.value = setInterval(fetchIncidents, 30000)
    fetchIncidents()
  }
}

function select(event, {item}) {
  router.push({ name: 'incident', params: { id: item.id, mission: getMissionId() } })
}

function formatDateTime(d) {
  return dayjs(d).format('YYYY-MM-DD HH:mm')
}

function onMessage(msg) {
  if (msg.domain === 'INCIDENT') {
    refresh.value = true
    if (msg.category === 'CREATED') {
      toast({message: 'Nya ärenden har registrerats', color: 'success'})
    } else if (msg.category === 'UPDATED') {
      toast({message: 'Ärenden har uppdaterats', color: 'success'})
    }
    fetchIncidents()
  }
}

function onMissionChanged(msg) {
  if(msg.category === 'CHANGE' && msg.domain === 'MISSION') {
    fetchMetadata()
      .then(fetchIncidents)
  }
}

function setupListeners() {
  eventBus.on(onMessage)
  eventBus.on(onMissionChanged)
}

function shutdownListeners() {
  eventBus.off(onMissionChanged)
  eventBus.off(onMessage)
}

onMounted(() => {
  fetchMetadata()
    .then(fetchIncidents)
  setupListeners()
})

onBeforeUnmount(() => {
  shutdownListeners()
  clearDblClickTimer()
  clearReloadTimer()
})

onBeforeRouteUpdate((from, to) => {
  return hasAnyRole([TMS_SUPERUSER, TMS_ADMIN, TMS_OPERATOR, TMS_OBSERVER])
})
</script>

<style lang="sass">
</style>
