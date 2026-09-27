/**
 * main.js
 *
 * Bootstraps Vuetify and other plugins then mounts the App`
 */

// Plugins
import { registerPlugins } from '@/plugins'
import L from 'leaflet'

// Components
import App from './App.vue'

// Composables
import { createApp } from 'vue'

const app = createApp(App)

registerPlugins(app)

delete L.Icon.Default.prototype._getIconUrl

import iconRetinaUrl from 'leaflet/dist/images/marker-icon-2x.png'
import iconUrl from 'leaflet/dist/images/marker-icon.png'
import shadowUrl from 'leaflet/dist/images/marker-shadow.png'

L.Icon.Default.mergeOptions({iconRetinaUrl, iconUrl, shadowUrl})

function displayError(err) {
  const div = document.createElement('div');
  div.style.cssText = 'border: 5px solid #0871b8;border-radius: 3px; padding: 20px;margin: 30px;';
  div.innerHTML = '<h2>' + err + '</h2><h5>Sorry, your request could not be processed.</h5>'
  document.getElementById('app').append(div);
}

import keycloak from '@/plugins/keycloak'

keycloak.init()
  .then(() => app.mount('#app'))
  .catch(displayError)
