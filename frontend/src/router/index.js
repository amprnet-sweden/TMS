/**
 * router/index.ts
 */

import {createRouter, createWebHistory} from 'vue-router/auto'
import {hasAnyRole} from "@/plugins/keycloak"
import routes from "@/router/routes"
import {getMissionId, setMissionId} from "@/plugins/api";

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
})

// Workaround for https://github.com/vitejs/vite/issues/11804
router.onError((err, to) => {
  if (err?.message?.includes?.('Failed to fetch dynamically imported module')) {
    if (!localStorage.getItem('vuetify:dynamic-reload')) {
      console.log('Reloading page to fix dynamic import error')
      localStorage.setItem('vuetify:dynamic-reload', 'true')
      location.assign(to.fullPath)
    } else {
      console.error('Dynamic import error, reloading page did not fix it', err)
    }
  } else {
    console.error(err)
  }
})

router.isReady().then(() => {
  localStorage.removeItem('vuetify:dynamic-reload')
})

router.beforeEach((to) => {
  const userMission = getMissionId()
  const routeMission = to.params?.mission
  if (routeMission !== undefined && routeMission !== userMission) {
    // Force set current mission to the one specified in the route.
    console.warn('Changed mission to', routeMission)
    setMissionId(`${routeMission}`)
  }
  const roles = to.meta?.roles
  if (roles) {
    return hasAnyRole(roles)
  }
})

export default router
