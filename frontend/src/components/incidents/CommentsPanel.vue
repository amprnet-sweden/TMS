<template>
  <v-toolbar density="comfortable" class="my-2" @click="$emit('update:modelValue', !modelValue)">
    <v-icon class="ms-4" icon="mdi-comment-text-outline"></v-icon>
    <v-toolbar-title class="text-subtitle-1">Noteringar<sup v-if="items.length">({{ items.length }})</sup>
    </v-toolbar-title>

    <v-toolbar-items>
      <v-btn variant="plain" rounded="0" @click.stop="$emit('add')">
        <v-icon size="x-large" icon="$add"></v-icon>
      </v-btn>
      <v-btn variant="plain" rounded="0">
        <v-icon size="x-large" :icon="modelValue ? 'mdi-menu-up' : 'mdi-menu-down'"></v-icon>
      </v-btn>
    </v-toolbar-items>
  </v-toolbar>

  <v-list v-if="modelValue">
    <CommentItem
      v-for="(item, i) in items"
      :key="i"
      :model-value="item"
      @select="$emit('select', $event)"
    ></CommentItem>
  </v-list>
</template>

<script setup>
import CommentItem from "@/components/incidents/CommentItem.vue";

defineProps({
  modelValue: {
    type: Boolean,
  },
  items: {
    type: Array,
    default: () => []
  }
})
defineEmits(['update:modelValue', 'add', 'select'])
</script>

<style scoped lang="sass">

</style>
