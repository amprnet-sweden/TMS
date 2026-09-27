<template>
  <v-dialog max-width="640" :model-value="modelValue" @keyup.esc="close">
    <v-form v-model="valid" @submit.prevent="save">
      <v-card>
        <v-card-title>Skapa sambandsuppdrag</v-card-title>
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
            Skapa
          </v-btn>
          <v-btn
            size="large"
            variant="elevated"
            @click="close"
          >
            <v-icon icon="$close"></v-icon>
            Avbryt
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-form>
  </v-dialog>
</template>

<script setup>
import {ref, watch} from "vue"

const props = defineProps({
  modelValue: {
    type: Boolean,
  },
})
const emit = defineEmits(['update:modelValue', 'create'])
const mission = ref({})
const valid = ref(false)
const rules = {
  required: (v) => !!v || 'Fältet är obligatoriskt',
  max(n) {
    return (v) => (!v || v.length <= n) || `Max antal tillåtna tecken är ${n}`
  }
}

function close() {
  emit('update:modelValue', false)
}

function save() {
  if (valid.value) {
    emit('create', mission.value)
  }
}

watch(() => props.modelValue, (state) => {
  if (state) {
    mission.value = {}
  }
})
</script>
