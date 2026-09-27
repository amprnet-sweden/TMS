<template>
  <v-container fluid>
    <v-card>
      <v-card-text>
        <v-toolbar density="comfortable" color="primary" class="mb-5">
          <v-toolbar-title>Sambandsuppdrag</v-toolbar-title>
        </v-toolbar>

        <div v-if="initialized">
          <v-sheet v-if="missions.length > 0">
            <v-card-title>Välj uppdrag</v-card-title>
            <v-card-text>
              <v-list>
                <v-list-item
                  v-for="mission in missions"
                  :key="mission.id"
                  :title="mission.name"
                  :subtitle="mission.description"
                  :active="mission === activeMission"
                  @click="onMissionSelected(mission)"
                >
                </v-list-item>
              </v-list>
            </v-card-text>
            <v-card-actions v-if="superuser">
              <v-btn variant="elevated" to="/missions">
                <v-icon>mdi-radio-tower</v-icon>
                Hantera uppdrag
              </v-btn>
            </v-card-actions>
          </v-sheet>

          <v-sheet v-else-if="superuser">
            <v-card-title>Kom igång</v-card-title>
            <v-card-text>
              Databasen innehåller för närvarande inga sambandsuppdrag.<br/>
              För att kunna jobba med TMS krävs att du först skapar ett sambandsuppdrag.
            </v-card-text>
            <v-card-actions>
              <v-btn variant="elevated" to="/missions">
                <v-icon>mdi-radio-tower</v-icon>
                Hantera uppdrag
              </v-btn>
            </v-card-actions>
          </v-sheet>

          <v-sheet v-else>
            <v-card-title>TMS är inte initierat</v-card-title>
            <v-card-text>
              Databasen innehåller för närvarande inga sambandsuppdrag.<br/>
              Be din systemadministratör att skapa ett sambandsuppdrag.
            </v-card-text>
          </v-sheet>
        </div>

        <v-skeleton-loader type="list-item-two-line@3" v-else>
        </v-skeleton-loader>

      </v-card-text>
    </v-card>

  </v-container>
</template>

<script setup>
import api, {eventBus, getMissionId, setMissionId} from "@/plugins/api"
import {computed, onBeforeUnmount, onMounted, ref} from "vue"
import {hasRole} from "@/plugins/keycloak"

const superuser = computed(() => hasRole('tms-superuser'))
const missions = ref([])
const activeMission = ref(null)
const initialized = ref(false)

async function fetchData() {
  return fetchMissions()
}

async function fetchMissions() {
  const path = superuser.value ? '/missions?status=ACTIVE' : '/user/missions'
  return api.get(path)
    .then(({data}) => {
      const list = [...data]
      missions.value = list
      const userMission = getMissionId()
      if (userMission) {
        activeMission.value = missions.value.find(p => p.id === userMission)
      } else {
        activeMission.value = null
      }
      return missions.value
    })
}

function onMissionSelected(item) {
  if (item?.id) {
    const selected = missions.value.find(p => p.id === item.id)
    activeMission.value = selected
    setMissionId(selected?.id)
    eventBus.emit({category: 'CHANGE', domain: 'MISSION', id: selected?.id})

  } else {
    activeMission.value = null
    eventBus.emit({category: 'CHANGE', domain: 'MISSION', id: null})
  }
}

function onMissionChanged(msg) {
  if (msg.category === 'CHANGE' && msg.domain === 'MISSION') {
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
    .then(() => (initialized.value = true))
})

onBeforeUnmount(() => {
  shutdownListeners()
})
</script>

<style scoped lang="sass">

</style>
