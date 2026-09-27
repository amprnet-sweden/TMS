/**
 * plugins/index.js
 *
 * Automatically included in `./src/main.js`
 */

// Plugins
import vuetify from './vuetify'
import router from '@/router'
import pinia from './stores'
import keycloak from './keycloak'
import api from './api'

export function registerPlugins (app) {
  app
    .use(pinia)
    .use(vuetify)
    .use(router)
    .use(keycloak)
    .use(api, router)
}
