<template>
  <v-dialog :max-width="width" :model-value="visible" persistent @keydown.esc="close">
    <v-card>

      <v-card-title>{{ title }}</v-card-title>

      <v-card-text>
        <p class="body-1">{{ text }}</p>
      </v-card-text>

      <v-divider></v-divider>

      <v-card-actions>
        <v-spacer></v-spacer>

        <v-btn variant="elevated" :color="color" @click="confirm">
          <v-icon :icon="icon"></v-icon>
          {{ confirmButtonText }}
        </v-btn>
        <v-btn variant="elevated" @click="close">
          <v-icon icon="$close"></v-icon>
          {{ closeButtonText }}
        </v-btn>

      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import {computed} from "vue"
import { useLocale } from "vuetify"

const props = defineProps({
  modelValue: {
    type: Object
  },
  title: {
    type: String,
    required: true
  },
  text: {
    type: String,
    required: true
  },
  confirmLabel: {
    type: String,
  },
  closeLabel: {
    type: String,
  },
  color: {
    type: String,
    default: 'success'
  },
  icon: {
    type: String,
    default: '$ok'
  },
  width: {
    type: String,
    default: '640px'
  }
})
const emit = defineEmits(['confirm', 'update:modelValue'])
const visible = computed(() => !!props.modelValue)
const {t} = useLocale()
const confirmButtonText = computed(() => {
  return props.confirmLabel || 'Bekräfta'
})
const closeButtonText = computed(() => {
  return props.closeLabel || 'Stäng'
})
function confirm() {
  emit('confirm', props.modelValue)
}
function close() {
  emit('update:modelValue', null)
}
</script>
