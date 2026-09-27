<template>
  <v-dialog max-width="640" :model-value="visible" @keyup.esc="close">
    <v-form v-model="valid" @submit.prevent="save">
      <v-card>
        <v-card-title>{{ t('$vuetify.tms.mission.title') }}</v-card-title>
        <v-card-text>

          <v-text-field
            autofocus
            label="Uppdragsnamn"
            v-model="mission.name"
            :rules="[rules.required]"
          >
          </v-text-field>
          <v-textarea
            label="Beskrivning av uppdraget"
            v-model.trim="mission.description"
            :rows="3"
            auto-grow
            :rules="[rules.max(4000)]"
            :counter="4000"
          ></v-textarea>

          <v-select
            label="Status"
            v-model="mission.status"
            :items="statusOptions"
          ></v-select>

        </v-card-text>
        <v-card-actions class="px-4">
          <v-btn
            type="submit"
            size="large"
            variant="elevated"
            color="success"
            accesskey="s"
          >
            <v-icon icon="$save"></v-icon>
            Spara
          </v-btn>
          <v-btn
            size="large"
            variant="outlined"
            color="error"
            @click="remove"
          >
            <v-icon icon="$delete"></v-icon>
            Radera
          </v-btn>

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

const props = defineProps({
  modelValue: {
    type: Object,
  },
})
const emit = defineEmits(['update:modelValue', 'delete', 'close'])
const {t} = useLocale()
const mission = ref({})
const statusOptions = computed(() => {
  return [
    {value: 'ACTIVE', title: t('$vuetify.tms.mission.status.ACTIVE')},
    {value: 'ARCHIVED', title: t('$vuetify.tms.mission.status.ARCHIVED')},
  ]
})
const valid = ref(false)
const visible = computed(() => !!props.modelValue)
const rules = {
  required: (v) => !!v || 'Fältet är obligatoriskt',
  max(n) {
    return (v) => (!v || v.length <= n) || `Max antal tillåtna tecken är ${n}`
  }
}

function close() {
  emit('close')
}

function remove() {
  emit('delete', props.modelValue)
}

function save() {
  if (valid.value) {
    emit('update:modelValue', mission.value)
  }
}

watch(() => props.modelValue, (state) => {
  if (state) {
    mission.value = {...state}
  } else {
    mission.value = {}
  }
})
</script>
