<template>
  <v-app-bar location="bottom" density="compact">
    <div
      class="text-caption text-disabled"
      style="position: absolute; right: 16px;"
    >
      &copy; {{ (new Date()).getFullYear() }} <span class="d-none d-sm-inline-block">AMPRNet Sverige</span>
      —
      <a
        class="text-decoration-none text-disabled"
        href="https://amprnet.se/"
        rel="noopener noreferrer"
        target="_blank"
      >
        Användarvillkor
      </a>
      —
      <a
        class="text-decoration-none text-disabled"
        href="https://amprnet.se/"
        rel="noopener noreferrer"
        target="_blank"
      >
        Personuppgiftspolicy
      </a>
    </div>
  </v-app-bar>
</template>

<script setup>

</script>

<style scoped lang="sass">

</style>
