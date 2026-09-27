<template>
  <div>

    <v-row dense>
      <v-col cols="12">
        <v-sheet border class="pa-3">
          <div class="text-caption text-secondary">Beskrivning</div>
          <p class="text-pre-wrap">{{ item.description }}</p>
        </v-sheet>
      </v-col>
    </v-row>

    <v-row dense>
      <v-col cols="12" md="6">
        <v-sheet border class="pa-3">
          <div class="text-caption text-secondary">Insatsgrupp</div>
          <div class="d-flex">
            {{ item.service?.name }}
            <v-spacer></v-spacer>
            <v-icon :icon="item.service?.icon" :color="item.service?.color"></v-icon>
          </div>
        </v-sheet>
      </v-col>
      <v-col cols="12" md="6">
        <v-sheet border class="pa-3">
          <div class="text-caption text-secondary">Ansvarig</div>
          <p>{{ username(item.assignedTo) }}</p>
        </v-sheet>
      </v-col>
    </v-row>

    <v-row dense>
      <v-col cols="12" md="6">
        <v-sheet border class="pa-3">
          <div class="text-caption text-secondary d-flex">
            Status
            <v-spacer></v-spacer>
            <span class="text-caption">Skapad: {{formatDateTime(item.created)}}</span>
          </div>
          <div class="d-flex">
            {{ item.status?.name }}
            <v-spacer></v-spacer>
            <v-icon :icon="item.status?.icon" :color="item.status?.color"></v-icon>
          </div>
        </v-sheet>
      </v-col>
      <v-col cols="12" md="6">
        <v-sheet border class="pa-3">
          <div class="text-caption text-secondary">Prioritet</div>
          <div class="d-flex">
            {{ item.priority?.name }}
            <v-spacer></v-spacer>
            <v-icon :icon="item.priority?.icon" :color="item.priority?.color"></v-icon>
          </div>
        </v-sheet>
      </v-col>
    </v-row>

  </div>

</template>

<script setup>
import dayjs from "dayjs";

const props = defineProps({
  item: {
    type: Object
  }
})

function username(item) {
  return item ? `${item.firstName} ${item.lastName} <${item.email}>` : null
}
function formatDateTime(d) {
  return dayjs(d).format('YYYY-MM-DD HH:mm')
}
</script>

<style scoped lang="sass">

</style>
