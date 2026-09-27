<template>
  <v-dialog max-width="512" :modelValue="!!modelValue" @keyup.esc="close">
    <v-form v-if="modelValue" @submit.prevent="save">
      <v-card>
        <v-card-title>{{ title }}</v-card-title>

        <v-card-text>

          <v-text-field
            label="Benämning"
            v-model="item.name"
            autofocus
          ></v-text-field>

          <v-select
            v-if="icon"
            label="Ikon"
            v-model="item.icon"
            :items="icons"
            :prepend-inner-icon="item.icon"
          >
            <template v-slot:item="{ props, item }">
              <v-list-item v-bind="props" :prepend-icon="item.raw"></v-list-item>
            </template>
          </v-select>

          <v-color-picker
            v-if="color"
            v-model="item.color"
            :swatches="colors"
            hide-canvas
            hide-inputs
            hide-sliders
            show-swatches
            elevation="0"
            width="100%"
          ></v-color-picker>

          <slot :item="item"></slot>

        </v-card-text>

        <v-card-actions>
          <v-btn type="submit" variant="elevated" color="success">
            <v-icon icon="$save"></v-icon>
            Spara
          </v-btn>
          <v-btn v-if="item.id" variant="outlined" color="error" @click="remove">
            <v-icon icon="$delete"></v-icon>
            Radera
          </v-btn>
          <v-btn variant="elevated" @click="close">
            <v-icon icon="$close"></v-icon>
            Stäng
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-form>
  </v-dialog>
</template>

<script setup>
import {ref, watch} from "vue";
import api from "@/plugins/api";

const props = defineProps({
  modelValue: {
    type: Object,
  },
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
  }
})
const emit = defineEmits(['update:modelValue'])

const colors = [
  ['#FF0000', '#AA0000', '#660000'],
  ['#FFCC80', '#FB8C00', '#E65100'],
  ['#BCAAA4', '#6D4C41', '#3E2723'],
  ['#FFEB3B', '#AAAA00', '#555500'],
  ['#00FF00', '#00AA00', '#005500'],
  ['#00FFFF', '#00AAAA', '#005555'],
  ['#0000FF', '#0000AA', '#000066'],
  ['#CCCCCC', '#999999', '#666666'],
]

const icons = [
  'mdi-check-bold',
  'mdi-alert',
  'mdi-alert-circle',
  'mdi-arrow-up-bold-box',
  'mdi-arrow-right-bold-box',
  'mdi-arrow-down-bold-box',
  'mdi-arrow-left-bold-box',
  'mdi-lock',
  'mdi-account',
  'mdi-account-multiple',
  'mdi-gas-station',
  'mdi-car',
  'mdi-bus',
  'mdi-tractor',
  'mdi-ferry',
  'mdi-airplane',
  'mdi-bike',
  'mdi-water',
  'mdi-waves',
  'mdi-fire',
  'mdi-ambulance',
  'mdi-silverware-fork-knife',
  'mdi-transmission-tower',
  'mdi-flash',
  'mdi-cog',
  'mdi-bell',
  'mdi-battery',
  'mdi-battery-20',
  'mdi-battery-60',
  'mdi-cellphone',
  'mdi-phone-classic',
  'mdi-binoculars',
  'mdi-weather-sunny',
  'mdi-cloud',
  'mdi-weather-pouring',
  'mdi-snowflake',
  'mdi-currency-eur',
  'mdi-horse',
  'mdi-dog-side',
  'mdi-cat',
  'mdi-bird',
  'mdi-fish',
  'mdi-alarm',
  'mdi-clock',
  'mdi-calendar',
  'mdi-text-box',
  'mdi-coffee',
  'mdi-cup',
]

const item = ref(null)

function save() {
  api.post(props.url, item.value)
    .then(close)
    .catch(console.error)
}

function remove() {
  api.delete(`${props.url}/${item.value.id}`)
    .then(close)
    .catch(console.error)
}

function close() {
  emit('update:modelValue', null)
}

watch(() => !!props.modelValue, (state) => {
  if(state) {
    item.value = { ...props.modelValue }
  } else {
    item.value = null
  }
})
</script>

<style scoped lang="sass">

</style>
