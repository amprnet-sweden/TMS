<template>
  <v-container fluid>
    <v-form v-model="valid" @submit.prevent="save">
      <v-card>
        <v-card-text>

          <v-toolbar density="comfortable" :color="color(model)" class="mb-2">
            <v-toolbar-title v-if="model">
              {{ model.name }}
            </v-toolbar-title>

            <v-spacer></v-spacer>

            <span class="text-uppercase text-subtitle-2 mx-6">{{ model.service?.name }}</span>

            <v-toolbar-items>
              <v-btn
                variant="plain"
                :icon="refresh ? 'mdi-reload-alert' : 'mdi-reload'"
                @click="fetchIncident(model.id)"
                accesskey="r"
              ></v-btn>
              <v-btn v-if="edit" type="submit" variant="elevated" rounded="0" color="success" accesskey="s"
                     class="px-8">
                <v-icon>$save</v-icon>
                Spara
              </v-btn>
              <v-btn v-else variant="elevated" rounded="0" color="warning" accesskey="n" @click="edit = !edit">
                <v-icon>mdi-pencil</v-icon>
                <span class="hidden-sm-and-down">Redigera</span>
              </v-btn>
              <v-btn variant="elevated" rounded="0" color="primary" @click="cancel">
                <v-icon size="x-large">$close</v-icon>
              </v-btn>
            </v-toolbar-items>

          </v-toolbar>

          <IncidentEditPanel
            v-if="edit"
            v-model="model"
            :service-items="serviceItems"
            :status-items="statusItems"
            :user-items="userItems"
            :priority-items="priorityItems"
            @clear:location="clearLocation"
          ></IncidentEditPanel>

          <IncidentDetailsPanel v-else-if="model" :item="model"></IncidentDetailsPanel>

          <CommentsPanel
            v-if="model.id"
            v-model="showComments"
            :items="comments"
            @add="addComment"
            @select="selectedComment = $event"
          ></CommentsPanel>

          <v-toolbar density="compact" @click="showMap = !showMap">
            <v-icon class="ms-4" icon="mdi-map-marker-outline"></v-icon>
            <v-toolbar-title class="text-subtitle-1">{{ coords || 'Karta' }}</v-toolbar-title>
            <v-spacer></v-spacer>
            <v-toolbar-items>
              <v-btn v-if="edit" icon="mdi-map-marker-off-outline" @click.stop="clearLocation"></v-btn>
              <v-btn variant="plain" rounded="0">
                <v-icon size="x-large" :icon="showMap ? 'mdi-menu-up' : 'mdi-menu-down'"></v-icon>
              </v-btn>
            </v-toolbar-items>
          </v-toolbar>
          <div v-show="showMap" id="themap" style="height:500px;"></div>

        </v-card-text>
      </v-card>
    </v-form>
    <NoteDialog
      v-model="selectedComment"
      @update:model-value="saveComment"
      @remove="removeComment"
    ></NoteDialog>
  </v-container>
</template>

<script setup>
import {computed, nextTick, onBeforeUnmount, onMounted, ref, watch} from 'vue'
import {onBeforeRouteUpdate, useRoute, useRouter} from 'vue-router'
import 'leaflet/dist/leaflet.css'
import * as L from 'leaflet'
import api, {eventBus, getMissionId, toast} from "@/plugins/api"
import IncidentDetailsPanel from "@/components/incidents/IncidentDetailsPanel.vue";
import IncidentEditPanel from "@/components/incidents/IncidentEditPanel.vue";
import CommentsPanel from "@/components/incidents/CommentsPanel.vue";
import dayjs from "dayjs";
import {useUserStore} from "@/plugins/stores";
import NoteDialog from "@/components/incidents/NoteDialog.vue";

const router = useRouter()
const route = useRoute()
const model = ref({})
const edit = ref(false)
const refresh = ref(false)
const showMap = ref(false)
const showComments = ref(true)
const valid = ref(false)
const serviceItems = ref([])
const userItems = ref([])
const statusItems = ref([])
const priorityItems = ref([])
const comments = ref([])
const selectedComment = ref(null)
const initialMap = ref(null)
const marker = ref(null)
const defaultLocation = [59.328893326719275, 18.16224786713087]
const location = computed(() => {
  if (model.value?.latitude) {
    return [model.value.latitude, model.value.longitude]
  }
  return null
})
const coords = computed(() => {
  if (location.value) {
    return location.value.map(d => new Intl.NumberFormat(undefined, {maximumFractionDigits: 5}).format(d)).join(' ')
  }
  return null
})

const store = useUserStore()
const userId = computed(() => store.user?.id)

async function fetchMetadata() {
  return api.get(`/missions/${getMissionId()}/members`)
    .then(({data}) => {
      userItems.value = data //.map(model => ({ id: model.id, name: `${model.firstName} ${model.lastName} <${model.email}>`}))
    })
    .then(() => api.get('/metadata'))
    .then(({data}) => {
      serviceItems.value = data.services
      statusItems.value = data.statuses
      priorityItems.value = data.priorities
    }).catch(() => false)
}

function fetchIncident(id) {
  if (id === '0') {
    return Promise.resolve({data: {status: statusItems.value.find(item => item.name === 'Ny')}})
      .then(({data}) => {
        model.value = data
        edit.value = true
        refresh.value = false
      })
  }
  return api.get(`/incidents/${encodeURIComponent(id)}`)
    .then(({data}) => {
      model.value = data
      refresh.value = false
      if (showMap.value) {
        getLocation().then(renderMap)
      }
      return data
    })
    .then(() => fetchComments(id))
}

function cancel() {
  if (edit.value && model.value.id) {
    fetchIncident(model.value.id).then(() => (edit.value = false))
  } else {
    router.push({ name: 'incidents', params: { mission: getMissionId() } })
  }
}

async function save() {
  if (!valid.value) {
    return
  }
  const req = model.value.id
    ? api.put(`/incidents/${encodeURIComponent(model.value.id)}`, model.value)
    : api.post('/incidents', model.value)
  return req
    .then(({data}) => {
      edit.value = false
      if (data) {
        if (model.value.id) {
          toast({message: 'Ärendet har uppdaterats', color: 'success'})
          fetchIncident(data.id)
        } else {
          toast({message: 'Ärendet har skapats', color: 'success'})
          router.push({ name: 'incident', params: { id: data.id, mission: getMissionId() } })
        }
      } else {
        fetchIncident(model.value.id)
        toast({message: 'Ärendet kunde inte sparas', color: 'error'})
      }
    })
    .catch(console.error)
}

function color(item) {
  return item?.color || 'primary'
}

function getLocation() {
  if (location.value) {
    return Promise.resolve(location.value)
  }

  if ("geolocation" in navigator) {
    return new Promise((resolve, reject) => {
      try {
        navigator.geolocation.getCurrentPosition((position) => {
          resolve([position.coords.latitude, position.coords.longitude])
        }, (err) => {
          console.warn(err.message)
          resolve(null)
        })
      } catch (err) {
        reject(err)
      }
    })
  }
  return Promise.resolve(null)
}

function setLocation(lat, lng) {
  model.value.latitude = lat
  model.value.longitude = lng
  return [lat, lng]
}

function clearLocation() {
  setLocation(null, null)
  if (initialMap.value && marker.value) {
    initialMap.value.removeLayer(marker.value)
    marker.value = null
  }
}

const markerOptions = undefined //{iconUrl: '@/assets/leaflet/marker-icon.png', shadowUrl: '@/assets/leaflet/marker-shadow.png'}

function renderMap(currentLocation) {
  const center = location.value || currentLocation || defaultLocation
  const target = location.value || (edit.value ? defaultLocation.value : null)

  if (initialMap.value) {
    initialMap.value.setView(center, 12)
    if (target) {
      if (marker.value) {
        marker.value.setLatLng(target)
      } else {
        marker.value = L.marker(target, markerOptions).addTo(initialMap.value)
      }
    }
  } else if (center) {
    nextTick(() => {
      const map = L.map('themap', {scrollWheelZoom: false}).setView(center, 12)
      L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>'
      }).addTo(map)
      map.on('click', function ({latlng}) {
        if (edit.value) {
          initialMap.value.setView(latlng, Math.max(15, initialMap.value.getZoom()))
          setLocation(latlng.lat, latlng.lng)
          if (marker.value) {
            marker.value.setLatLng(latlng)
          } else {
            marker.value = L.marker(latlng).addTo(initialMap.value)
          }
        }
      });
      if (target) {
        marker.value = L.marker(target, markerOptions).addTo(map)
      }
      initialMap.value = map
    })
  }
}

function fetchComments(id) {
  if (id === '0') {
    return Promise.resolve([])
  }
  return api.get(`/incidents/${id}/comments`)
    .then(({data}) => (comments.value = data))
    .catch(console.error)
}

function addComment(text) {
  selectedComment.value = {id: null, user: {id: userId.value}, timestamp: dayjs(), text}
}

function saveComment(data) {
  if (!data) {
    return
  }
  const {id, text} = data
  const incident = model.value.id
  const comment = { user: {id: userId.value}, timestamp: dayjs(), text, id }
  return api.post(`/incidents/${incident}/comments`, comment)
    .then(() => (selectedComment.value = null))
    .then(() => toast({message: 'Noteringen har sparats', color: 'success'}))
    .then(() => fetchComments(incident))
    .then(() => (showComments.value = true))
    .catch(console.error)
}

function removeComment(item) {
  const id = model.value.id
  return api.delete(`/incidents/${id}/comments/${item.id}`)
    .then(() => (selectedComment.value = null))
    .then(() => toast({message: 'Noteringen raderad', color: 'warning'}))
    .then(() => fetchComments(id))
    .catch(console.error)
}

function onMessage(msg) {
  if (msg.domain === 'INCIDENT' && msg.id === model.value.id) {
    refresh.value = true
    toast({message: 'Ärendet har uppdaterats av annan användare', color: 'success'})
    if (!edit.value) {
      fetchIncident(model.value.id)
    }
  }
}

function onMissionChanged(msg) {
  if(msg.category === 'CHANGE' && msg.domain === 'MISSION') {
    router.push({ name: 'incidents', params: { mission: getMissionId() } })
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
  setupListeners()
  fetchMetadata()
    .then(() => fetchIncident(route.params.id))
    .then((incident) => (showMap.value = !!incident?.latitude))
    .then(fetchComments(route.params.id))
    .catch(console.error)
})

onBeforeUnmount(() => {
  shutdownListeners()
})

onBeforeRouteUpdate((to) => {
  fetchIncident(to.params.id)
    .then((incident) => (showMap.value = !!incident?.latitude))
    .then(fetchComments(to.params.id))
    .catch(console.error)
})
watch(() => showMap.value, (state) => {
  if (state) {
    getLocation().then(renderMap)
  }
})
</script>

<style scoped lang="sass">
</style>
