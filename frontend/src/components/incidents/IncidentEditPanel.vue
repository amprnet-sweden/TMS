<template>

  <v-row dense>
    <v-col cols="12">
      <v-text-field
        label="Benämning"
        autofocus
        :rules="[rules.required]"
        :model-value="modelValue.name"
        @update:model-value="update('name', $event)"
      >
      </v-text-field>
      <v-textarea
        label="Beskrivning"
        auto-grow
        :rows="1"
        :model-value="modelValue.description"
        @update:model-value="update('description', $event)"
      >
      </v-textarea>
    </v-col>
  </v-row>

  <v-row dense>
    <v-col cols="12" md="6">
      <v-select
        :model-value="modelValue.service"
        @update:model-value="update('service', $event)"
        label="Insatsgrupp"
        :items="serviceItems"
        item-value="id"
        item-title="name"
        return-object
        :rules="[rules.required]"
      >
        <template v-slot:item="{ props, item }">
          <v-list-item v-bind="props" :prepend-icon="item.raw.icon" :base-color="item.raw.color"></v-list-item>
        </template>
      </v-select>
    </v-col>
    <v-col cols="12" md="6">
      <v-select
        :model-value="modelValue.assignedTo"
        @update:model-value="update('assignedTo', $event)"
        label="Ansvarig"
        :items="userItems"
        item-value="id"
        :item-title="username"
        return-object
      ></v-select>
    </v-col>
  </v-row>

  <v-row dense>
    <v-col cols="12" md="6">
      <v-select
        :model-value="modelValue.status"
        @update:model-value="update('status', $event)"
        label="Status"
        :items="statusItems"
        item-value="id"
        item-title="name"
        return-object
        :rules="[rules.required]"
      >
        <template v-slot:item="{ props, item }">
          <v-list-item v-bind="props" :prepend-icon="item.raw.icon" :base-color="item.raw.color"></v-list-item>
        </template>
      </v-select>
    </v-col>
    <v-col cols="12" md="6">
      <v-select
        :model-value="modelValue.priority"
        @update:model-value="update('priority', $event)"
        label="Prioritet"
        :items="priorityItems"
        item-value="id"
        item-title="name"
        return-object
        :rules="[rules.required]"
      >
        <template v-slot:item="{ props, item }">
          <v-list-item v-bind="props" :prepend-icon="item.raw.icon" :base-color="item.raw.color"></v-list-item>
        </template>
      </v-select>
    </v-col>
  </v-row>

  <v-row dense v-if="false">
    <v-col cols="12" md="6">
      <v-text-field
        :model-value="modelValue.latitude"
        label="Latitud"
        clearable
        @click:clear="$emit('clear:location')"
      ></v-text-field>
    </v-col>
    <v-col cols="12" md="6">
      <v-text-field
        :model-value="modelValue.longitude"
        label="Longitud"
        clearable
        @click:clear="$emit('clear:location')"
      ></v-text-field>
    </v-col>
  </v-row>

</template>

<script setup>

const props = defineProps({
  modelValue: {type: Object},
  serviceItems: {type: Object},
  userItems: {type: Object},
  statusItems: {type: Object},
  priorityItems: {type: Object},
})
const emit = defineEmits(['update:modelValue', 'clear:location'])
const rules = {
  required: (v) => !!v || 'Du måste ange att värde'
}
function update(prop, value) {
  emit('update:modelValue', {...props.modelValue, [prop]: value})
}

function username(item) {
  return item ? `${item.firstName} ${item.lastName} <${item.email}>` : null
}
</script>

<style scoped lang="sass">

</style>
