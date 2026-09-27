<template>
  <v-dialog max-width="640" :model-value="visible" @keyup.esc="close">
    <v-form v-model="valid" @submit.prevent="save">
      <v-card>
        <v-card-title>{{ t('$vuetify.tms.mission.users.title') }}</v-card-title>
        <v-card-text>

          <v-sheet>
            <v-row dense>
              <v-col>
                <v-autocomplete
                  v-model="userModel"
                  v-model:search="search"
                  :loading="loading"
                  autofocus
                  autocomplete="off"
                  label="Sök användare"
                  variant="solo"
                  :items="searchResult"
                  item-value="id"
                  item-title="name"
                  return-object
                  hide-no-data
                ></v-autocomplete>

              </v-col>
              <v-col>
                <v-select
                  label="Roll"
                  v-model="roleModel"
                  :items="roles"
                  append-icon="$add"
                  @click:append="addUser"
                ></v-select>
              </v-col>
            </v-row>
          </v-sheet>

          <v-sheet v-for="(u, i) in users" :key="i">
            <v-row dense>
              <v-col>
                {{ u.name }}
              </v-col>
              <v-col>
                {{ t('$vuetify.tms.user.role.' + u.role)}}
              </v-col>
            </v-row>
          </v-sheet>

        </v-card-text>

        <v-card-actions class="px-4">
          <v-btn
            size="large"
            variant="elevated"
            @click="close"
          >
            <v-icon icon="$close"></v-icon>
            Stäng
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-form>
  </v-dialog>
</template>

<script setup>
import {computed, ref, watch} from "vue"
import {useLocale} from "vuetify"
import api, {loading} from "@/plugins/api"
import {refDebounced} from "@vueuse/core"
import {TMS_ADMIN, TMS_OBSERVER, TMS_OPERATOR, TMS_SUPERUSER} from "@/roles"

const props = defineProps({
  modelValue: {
    type: Object,
  },
})
const emit = defineEmits(['update:modelValue', 'delete', 'close'])
const {t} = useLocale()
const mission = ref({})
const search = ref(null)
const searchTrigger = refDebounced(search, 600)
watch(searchTrigger, (value) => {
  api.get('/keycloak/admin/users?q=' + encodeURIComponent(value))
    .then(res => (searchResult.value = res))
})

const searchResult = ref([])
const users = ref([])
const userModel = ref(null)
const roleModel = ref(null)
const roles = [
  {value: TMS_OBSERVER, title: 'Observatör'},
  {value: TMS_OPERATOR, title: 'Operatör'},
  {value: TMS_ADMIN, title: 'Administratör'},
  {value: TMS_SUPERUSER, title: 'Superuser'},
]
const valid = ref(false)
const visible = computed(() => !!props.modelValue)
const rules = {
  required: (v) => !!v || 'Fältet är obligatoriskt',
  max(n) {
    return (v) => (!v || v.length <= n) || `Max antal tillåtna tecken är ${n}`
  }
}

function addUser() {
  if (!(userModel.value && roleModel.value)) {
    return
  }
  const user = { ...userModel.value, role: roleModel.value }
  users.value.push(user)
  api.post(`/missions/${mission.value.id}/members`, user)
    .then(() => {
      userModel.value = null
      roleModel.value = null
    })
    .then(fetchData)
}

function deleteUser(index) {
  users.value.splice(index, 1)
}

function close() {
  emit('update:modelValue', null)
}

function save() {
  if (valid.value) {
    emit('update:modelValue', mission.value)
  }
}

function fetchData() {
  if (!props.modelValue.id) {
    return Promise.resolve([])
  }
  return api.get(`/missions/${props.modelValue.id}/members`)
    .then(({data}) => {
      users.value = data
    }).catch(console.error)
}

watch(() => props.modelValue, (state) => {
  if (state) {
    mission.value = {...state}
    fetchData()
  } else {
    userModel.value = null
    roleModel.value = null
    users.value = []
    mission.value = {}
  }
})
</script>
