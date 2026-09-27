<template>
  <v-dialog max-width="640" :model-value="!!modelValue" @keyup.esc="close">
    <v-form v-model="valid" @submit.prevent="save">
      <v-card>
        <v-card-title>
          {{note.id ? 'Ändra notering' : 'Registrera ny notering'}}
        </v-card-title>
        <v-card-text>
          <v-textarea
            label="Notering"
            v-model.trim="note.text"
            :rows="3"
            autofocus
            auto-grow
            :rules="[rules.required, rules.max(4000)]"
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
            Spara
          </v-btn>
          <v-btn
            v-if="note.id"
            size="large"
            variant="outlined"
            color="error"
            @click="remove"
          >
            <v-icon icon="$delete"></v-icon>
            Ta bort
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

import {ref, watch} from "vue";

const props = defineProps({
  modelValue: {
    type: Object,
  },
})
const emit = defineEmits(['update:modelValue', 'remove'])
const note = ref({})
const valid = ref(false)
const rules = {
  required: (v) => !!v || 'Fältet är obligatoriskt',
  max(n) {
    return (v) => (!v || v.length <= n) || `Max antal tillåtna tecken är ${n}`
  }
}

function close() {
  emit('update:modelValue', null)
}

function remove() {
  emit('remove', props.modelValue)
}

function save() {
  if (valid.value) {
    emit('update:modelValue', note.value)
  }
}

watch(() => props.modelValue, (state) => {
  if (state) {
    note.value = {...state}
  } else {
    note.value = {}
  }
})
</script>

<style scoped lang="sass">

</style>
