<template>
  <v-container fluid>
    <v-card>
      <v-card-text>
        <v-toolbar density="comfortable" color="primary" class="mb-5">
          <v-toolbar-title>Översikt</v-toolbar-title>
        </v-toolbar>
        <v-row v-if="rawData">
          <v-col cols="12" md="6" v-for="s in Object.keys(services)" :key="s">
            <v-card>
              <v-card-title>{{ getServiceName(s) }}</v-card-title>
              <v-card-text>
                <v-row dense v-for="t in Object.keys(services[s])" :key="t">
                  <v-col cols="4">
                    {{ getStatusName(t) }}
                  </v-col>
                  <v-col cols="8">
                    <v-badge :color="getColor(services[s][t][p])" :content="services[s][t][p]"
                             v-for="p in Object.keys(services[s][t])" :key="p">
                      <v-chip class="ml-3">
                        {{ getPriorityName(p) }}
                      </v-chip>
                    </v-badge>
                  </v-col>
                </v-row>
              </v-card-text>
            </v-card>
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>
  </v-container>
</template>

<script setup>
import api, {eventBus} from "@/plugins/api"
import {computed, onBeforeUnmount, onMounted, ref} from "vue";

const serviceItems = ref([])
const statusItems = ref([])
const priorityItems = ref([])

const rawData = ref([])

const services = computed(() => rawData.value?.reduce((acc, val) => {
  const serviceId = val.serviceId
  const statusId = val.statusId
  const priorityId = val.priorityId
  const count = val.count
  const svc = acc[serviceId] || {}
  const status = svc[statusId] || {}
  const prio = (status[priorityId] || 0) + count

  status[priorityId] = prio
  svc[statusId] = status
  acc[serviceId] = svc

  return acc
}, {}))

function getServiceName(id) {
  return serviceItems.value.find(item => String(item.id) === id)?.name
}

function getStatusName(id) {
  return statusItems.value.find(item => String(item.id) === id)?.name
}

function getPriorityName(id) {
  return priorityItems.value.find(item => String(item.id) === id)?.name
}

function getColor(n) {
  if (n > 190) {
    return 'error'
  }
  if (n > 170) {
    return 'warning'
  }
  return 'primary'
}

async function fetchData() {
  return api.get('/metadata')
    .then(({data}) => {
      serviceItems.value = data.services
      statusItems.value = data.statuses
      priorityItems.value = data.priorities
    }).catch(() => false)
    .then(() => api.get('/dashboard'))
    .then(({data}) => {
      rawData.value = data
    }).catch(() => false)
}

function onMissionChanged(msg) {
  if(msg.category === 'CHANGE' && msg.domain === 'MISSION') {
    fetchData()
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
  fetchData()
})

onBeforeUnmount(() => {
  shutdownListeners()
})
</script>

<style scoped lang="sass">

</style>
