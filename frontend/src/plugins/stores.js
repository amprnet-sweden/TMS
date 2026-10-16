import {createPinia, defineStore} from 'pinia'

const pinia = createPinia()

export const useUserStore = defineStore('user', {
  state: () => ({ user: null, settings: {} }),
})

export default pinia
