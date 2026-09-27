<template>
  <v-card>
    <v-card-title class="d-flex">
      {{title}}
      <v-spacer></v-spacer>
      <v-btn size="small" variant="plain" icon="mdi-plus" @click="add"></v-btn>
    </v-card-title>
    <v-card-text>
      <v-list>
        <v-list-item v-for="(item, i) in items" :key="i" @click="edit = item">
          <v-list-item-title>{{ item.name }}</v-list-item-title>
          <template v-slot:prepend>
            <v-icon :color="item.color" :icon="item.icon"></v-icon>
          </template>
        </v-list-item>
      </v-list>
    </v-card-text>
  </v-card>
  <MetadataAdmin
    v-model="edit"
    :title="title"
    :url="url"
    :icon="icon"
    :color="color"
    @update:model-value="fetchItems"
  >
    <template v-slot="{item}">
      <slot name="form" :item="item"></slot>
    </template>
  </MetadataAdmin>
</template>

<script setup>
import {onBeforeUnmount, onMounted, ref} from "vue";
import api, {eventBus} from "@/plugins/api"
import MetadataAdmin from "@/components/incidents/MetadataAdmin.vue";

const props = defineProps({
  title: {
    type: String,
  },
  url: {
    type: String,
  },
  color: {
    type: Boolean,
  },
  icon: {
    type: Boolean,
  },
})

const items = ref([])
const edit = ref(null)

function sortByName() {
  return (a, b) => {
    const nameA = a.name.toUpperCase()
    const nameB = b.name.toUpperCase()
    if (nameA < nameB) {
      return -1
    }
    if (nameA > nameB) {
      return 1
    }
    return 0;
  }
}

async function fetchItems() {
  return api.get(props.url)
    .then(({data}) => {
      data.sort(sortByName());
      items.value = data
    })
}

function add() {
  edit.value = { name: '', roles: { createRoles: [], readRoles: [], updateRoles: [], deleteRoles: [] } };
}

function onMissionChanged(msg) {
  if(msg.category === 'CHANGE' && msg.domain === 'MISSION') {
    fetchItems()
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
  fetchItems()
})

onBeforeUnmount(() => {
  shutdownListeners()
})
</script>

<style scoped lang="sass">

</style>
