<template>
  <v-card class="mb-2" elevation="1">
    <v-card-title class="d-flex pb-1">
      <span class="text-caption">{{ formatDateTime(modelValue.timestamp) }} {{ modelValue.user.name }}</span>
      <v-spacer></v-spacer>
      <v-icon
        color="grey"
        icon="$edit"
        size="x-small"
        @click="$emit('select', modelValue)"
      ></v-icon>
    </v-card-title>
    <v-card-text class="text-pre-wrap">{{ modelValue.text }}</v-card-text>
  </v-card>
</template>

<script setup>
import dayjs from "dayjs";

defineProps({
  modelValue: {
    type: Object,
  }
})
defineEmits(["select"]);

function formatDateTime(d) {
  return dayjs(d).format('YYYY-MM-DD HH:mm');
}
</script>
