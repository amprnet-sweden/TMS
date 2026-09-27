<template>
  <v-dialog max-width="1024" :model-value="modelValue" @keyup.esc="close">
    <v-card>
      <v-card-text>
        <div id="dialog-map" style="height:500px;"></div>
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
        <v-spacer></v-spacer>
        {{ location.join(', ') }}
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import {nextTick, ref, watch} from 'vue'
import 'leaflet/dist/leaflet.css'
import * as L from 'leaflet'

const props = defineProps({
  modelValue: {
    type: Boolean,
  },
  location: {
    type: Array,
    default: () => [59.328893326719275, 18.16224786713087]
  }
})

const emit = defineEmits(['update:modelValue', 'update:location'])

const initialMap = ref(null)
const marker = ref(null)

function close() {
  //marker.value = null
  //initialMap.value = null
  emit('update:modelValue', false)
}

function renderMap(latlng) {
  if (initialMap.value) {
    initialMap.value.setView(latlng, 12)
    marker.value.setLatLng(latlng)
  } else if (props.location) {
    nextTick(() => {
      const map = L.map('dialog-map').setView(latlng, 12)
      L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>'
      }).addTo(map)
      map.on('click', function({latlng}) {
        emit('update:location', [latlng.lat, latlng.lng])
        marker.value.setLatLng(latlng)
      });
      marker.value = L.marker(latlng).addTo(map)
      initialMap.value = map
    })
  }
}

watch(() => props.modelValue, (newState) => {
  if (newState) {
    renderMap(props.location)
  } else {
    marker.value = null
    initialMap.value = null
  }
}, {deep: true})
</script>

<style scoped lang="sass">

</style>
