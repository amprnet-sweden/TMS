import {ref} from "vue"
import {createFetch, refDebounced, useEventBus} from "@vueuse/core"

const _loading = ref(0)
export const loading = refDebounced(() => _loading.value > 0, 600)
export const snackbarMessage = ref(null)
export const snackbarColor = ref(null)
export const snackbarTimeout = ref(null)

export function toast(ctx) {
  const message = ctx.message || ctx.subject || null

  if (message) {
    const timeout = ctx.timeout || 3000
    snackbarColor.value = ctx.color
    snackbarTimeout.value = timeout
    snackbarMessage.value = message
  }
}

export const eventBus = useEventBus('message')

function getCookie(name) {
  const value = `; ${document.cookie}`
  const parts = value.split(`; ${name}=`)
  if (parts.length === 2) return parts.pop().split(';').shift()
}

export function getMissionId() {
  return localStorage.getItem('mission')
}

export function setMissionId(missionId) {
  if (missionId) {
    localStorage.setItem('mission', missionId)
  } else {
    localStorage.removeItem('mission')
  }
}

export const useFetch = createFetch({
  baseUrl: import.meta.env.VITE_APP_API,
  options: {
    beforeFetch({options}) {
      _loading.value += 1
      options.headers['X-XSRF-TOKEN'] = getCookie('XSRF-TOKEN')
      options.headers['x-tms-mission'] = getMissionId()
      return {options}
    },
    afterFetch(ctx) {
      _loading.value -= 1
      return ctx
    },
    onFetchError(ctx) {
      _loading.value -= 1
      if (ctx.response?.status === 401 || ctx.response?.status === 403) {
        console.error('Error ' + ctx.response?.status)
      } else {
        toast({message: 'Ett fel inträffade! ' + ctx.error.message, color: 'error'})
      }
      return ctx
    }
  },
  fetchOptions: {
    mode: 'cors',
    credentials: 'include',
  },
})

function createApi() {
  const handleResponse = (data) => {
    const response = data.response.value
    if (response?.ok) {
      return response.json()
    }
    return Promise.reject(data.error.value)
  }
  const api = {
    install(app) {
      app.provide('api', api)
      app.provide('eventBus', eventBus)
      app.config.globalProperties.$api = api
      app.config.globalProperties.$eventBus = eventBus
    },
    get(url) {
      return useFetch(url).get().then(handleResponse)
    },
    post(url, data) {
      return useFetch(url).post(data).then(handleResponse)
    },
    put(url, data) {
      return useFetch(url).put(data).then(handleResponse)
    },
    delete(url) {
      return useFetch(url).delete().then(handleResponse)
    },
  }
  return api
}

export default createApi()
