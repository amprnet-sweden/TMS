import * as role from '@/roles'

export default [
  {
    name: 'home',
    path: '/',
    component: () => import('@/pages/index.vue'),
    meta: {
      //menu: true,
      title: 'Hem',
      icon: 'mdi-home',
    }
  },
  {
    name: 'dashboard',
    path: '/:mission/dashboard',
    component: () => import('@/pages/dashboard.vue'),
    meta: {
      menu: true,
      title: 'Översikt',
      icon: 'mdi-helicopter',
      roles: [role.TMS_SUPERUSER, role.TMS_ADMIN, role.TMS_OPERATOR, role.TMS_OBSERVER]
    },
  },
  {
    name: 'incidents',
    path: '/:mission/incidents/',
    component: () => import('@/pages/incidents/index.vue'),
    meta: {
      menu: true,
      title: 'Ärenden',
      icon: 'mdi-alert-circle',
      roles: [role.TMS_SUPERUSER, role.TMS_ADMIN, role.TMS_OPERATOR, role.TMS_OBSERVER]
    },
  },
  {
    name: 'incident',
    path: '/:mission/incidents/:id',
    component: () => import('@/pages/incidents/[id].vue'),
    meta: {
      title: 'Ärende',
      roles: [role.TMS_SUPERUSER, role.TMS_ADMIN, role.TMS_OPERATOR, role.TMS_OBSERVER]
    },
  },
  /*
  {
    name: 'notifications',
    path: '/notifications',
    component: () => import('@/pages/notifications.vue'),
    meta: {
      menu: true,
      title: 'Logg', icon: 'mdi-bell',
      roles: [role.TMS_SUPERUSER, role.TMS_ADMIN, role.TMS_OPERATOR]
    },
  },
   */
  {
    name: 'settings',
    path: '/:mission/settings',
    component: () => import('@/pages/settings.vue'),
    meta: {
      menu: true,
      title: 'Inställningar', icon: 'mdi-cog',
      roles: [role.TMS_SUPERUSER, role.TMS_ADMIN]
    },
  },
  {
    name: 'missions',
    path: '/missions',
    component: () => import('@/pages/missions.vue'),
    meta: {
      menu: true,
      title: 'Sambandsuppdrag',
      icon: 'mdi-radio-tower',
      roles: [role.TMS_SUPERUSER]
    }
  },
]
