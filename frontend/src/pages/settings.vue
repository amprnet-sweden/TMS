<template>
  <v-container fluid>
    <v-card>
      <v-card-text>
        <v-toolbar density="comfortable" color="primary" class="mb-3">
          <v-toolbar-title>Inställningar</v-toolbar-title>
        </v-toolbar>

        <v-row dense>
          <v-col cols="12" md="4">
            <MetadataList
              title="Insatsgrupp"
              url="/metadata/services"
              icon
            >
              <template v-slot:form="{ item }">
                <div class="text-caption">Roller / behörigheter</div>
                <v-combobox
                  label="Skapa"
                  v-model="item.roles.createRoles"
                  multiple
                  chips
                  closable-chips
                  autocomplete="off"
                ></v-combobox>
                <v-combobox
                  label="Läsa"
                  v-model="item.roles.readRoles"
                  multiple
                  chips
                  closable-chips
                  autocomplete="off"
                ></v-combobox>
                <v-combobox
                  label="Uppdatera"
                  v-model="item.roles.updateRoles"
                  multiple
                  chips
                  closable-chips
                  autocomplete="off"
                ></v-combobox>
                <v-combobox
                  label="Radera"
                  v-model="item.roles.deleteRoles"
                  multiple
                  chips
                  closable-chips
                  autocomplete="off"
                ></v-combobox>
              </template>
            </MetadataList>
          </v-col>
          <v-col cols="12" md="4">
            <MetadataList
              title="Status"
              url="/metadata/statuses"
              icon
              color
            ></MetadataList>
          </v-col>
          <v-col cols="12" md="4">
            <MetadataList
              title="Prioritet"
              url="/metadata/priorities"
              icon
              color
            ></MetadataList>
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>
  </v-container>
</template>

<script setup>
import MetadataList from "@/components/incidents/MetadataList.vue";
</script>

<style scoped lang="sass">

</style>
