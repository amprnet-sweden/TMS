<template>
  <v-container fluid>
    <v-card>
      <v-card-text>
        <v-toolbar density="comfortable" color="primary" class="mb-5">
          <v-toolbar-title>Sambandsuppdrag</v-toolbar-title>
        </v-toolbar>
        <v-sheet v-if="missions.length > 0">
          <v-card-title>Hantera uppdrag</v-card-title>
          <v-card-text>
            <v-list>
              <v-list-item
                v-for="mission in missions"
                :key="mission.id"
                :subtitle="mission.description"
                :active="mission === activeMission"
                @click="onMissionSelected(mission)"
              >
                <template v-slot:title>
                  <span :class="mission.status === 'ARCHIVED' ? 'text-decoration-line-through text-grey' : null">{{mission.name}}</span>
                </template>

                <template v-slot:append>
                  <v-icon @click.stop="editUsers = mission">
                    mdi-account-multiple-outline
                  </v-icon>
                  <v-icon class="ms-2" @click.stop="editMission = mission">
                    $edit
                  </v-icon>
                </template>
              </v-list-item>
            </v-list>
          </v-card-text>
          <v-card-actions v-if="superuser">
            <v-btn variant="elevated" @click="createMission = true">
              <v-icon>$add</v-icon>
              Skapa nytt uppdrag
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
            <v-btn variant="elevated" @click="createMission = true">
              <v-icon>$add</v-icon>
              Skapa nytt uppdrag
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
      </v-card-text>
    </v-card>

    <EditUsersDialog
      v-model="editUsers"
    ></EditUsersDialog>

    <CreateMissionDialog
      v-model="createMission"
      @create="saveMission"
    ></CreateMissionDialog>

    <EditMissionDialog
      v-model="editMission"
      @close="editMission = null"
      @update:model-value="saveMission"
      @delete="confirmDeleteMission = $event"
    ></EditMissionDialog>

    <ConfirmDialog
      v-model="confirmDeleteMission"
      title="Radera sambandsuppdrag"
      text="Är du säker på att du vill radera sambandsuppdraget? All data kommer att raderas. Operationen går inte att ångra!"
      color="error"
      @confirm="deleteMission"
      @close="confirmDeleteMission = null"
      ></ConfirmDialog>
  </v-container>
</template>

<script setup>
import api, {eventBus, getMissionId, setMissionId, toast} from "@/plugins/api"
import {computed, onBeforeUnmount, onMounted, ref} from "vue";
import {hasRole} from "@/plugins/keycloak";
import EditMissionDialog from "@/components/EditMissionDialog.vue";
import CreateMissionDialog from "@/components/CreateMissionDialog.vue";
import ConfirmDialog from "@/components/ConfirmDialog.vue";
import EditUsersDialog from "@/components/EditUsersDialog.vue";

const superuser = computed(() => hasRole('tms-superuser'))
const missions = ref([])
const activeMission = ref(null)
const createMission = ref(false)
const editMission = ref(null)
const confirmDeleteMission = ref(null)
const editUsers = ref(null)

async function fetchData() {
  return fetchMissions()
}

async function fetchMissions() {
  return api.get('/missions')
    .then(({data}) => {
      missions.value = [...data]
      const userMission = getMissionId()
      if (userMission) {
        activeMission.value = missions.value.find(p => p.id === userMission)
      } else {
        activeMission.value = null
      }
      //if(!activeMission.value) {
      //  setMissionId(null)
      //}
      return missions.value
    })
}

async function saveMission(item) {
  if (item.id) {
    return api.put(`/missions/${item.id}`, item)
      .then(({data}) => {
        //activeMission.value = data
        editMission.value = null
        return data
      })
      .then(onMissionSelected)
      .then(() => toast({message: `${item.name} uppdaterades`, color: 'success'}))
  } else {
    return api.post('/missions', item)
      .then(({data}) => {
        missions.value.push(data)
        //activeMission.value = data
        createMission.value = false
        return data
      })
      .then(onMissionSelected)
      .then(() => toast({message: `${item.name} skapades`, color: 'success'}))
  }
}

async function deleteMission(item) {
  return api.delete(`/missions/${item.id}`)
    .then(() => toast({message: `${item.name} raderades`, color: 'warning'}))
    .then(() => {
      confirmDeleteMission.value = null
      editMission.value = null
      return null
    })
    .then(onMissionSelected)
}

function onMissionSelected(item) {
  if (item?.status !== 'ACTIVE') {
    return
  }
  if (item?.id) {
    const selected = missions.value.find(p => p.id === item.id)
    activeMission.value = selected
    setMissionId(selected?.id)
    eventBus.emit({ category: 'CHANGE', domain: 'MISSION', id: selected?.id })
  } else {
    activeMission.value = null
    eventBus.emit({ category: 'CHANGE', domain: 'MISSION', id: null })
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
})

onBeforeUnmount(() => {
  shutdownListeners()
})
</script>

<style scoped lang="sass">

</style>
