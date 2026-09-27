import {TMS_ADMIN, TMS_OBSERVER, TMS_OPERATOR, TMS_SUPERUSER} from "@/roles"

export default {
  tms: {
    mission: {
      label: 'Uppdrag',
      title: 'Sambandsuppdrag',
      status: {
        label: 'Status',
        ACTIVE: 'Aktivt',
        ARCHIVED: 'Arkiverat',
      },
      users: {
        label: 'Bemanning',
        title: 'Bemanning',
      }
    },
    user: {
      role: {
        [TMS_OBSERVER]: 'Observatör',
        [TMS_OPERATOR]: 'Operatör',
        [TMS_ADMIN]: 'Administratör',
        [TMS_SUPERUSER]: 'Superuser',
      }
    }
  }
}
