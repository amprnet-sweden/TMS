import Keycloak from 'keycloak-js'
import backend from '@/plugins/api'
import * as role from "@/roles";

export function hasRole(role) {
  const user = JSON.parse(localStorage.getItem('user') || '{}')
  const myRoles = user?.roles || []
  return myRoles.includes(role)
}

export function hasAnyRole(roles) {
  const user = JSON.parse(localStorage.getItem('user') || '{}')
  const myRoles = user?.roles || []
  if(! myRoles.includes(role.TMS_SUPERUSER)) {
    myRoles.push(role.TMS_OPERATOR) // TODO Implement correct role logic
  }
  for(let i = 0; i < roles.length; i++) {
    let role = roles[i]
    if (myRoles.includes(role)) {
      return true
    }
  }
  return false
}

function createKeycloak() {
  const kcOptions = {
    url: (import.meta.env.VITE_APP_AUTH || 'https://localhost:9000/auth'),
    realm: import.meta.env.VITE_APP_REALM || 'amprnet',
    clientId: import.meta.env.VITE_APP_CLIENT_ID || 'tms-web-app'
  }
  const keycloak = new Keycloak(kcOptions)

  const JWT_COOKIE_NAME = 'JWT'

  const setCookie = (name, value, days = 1, path = '/') => {
    const expires = new Date(Date.now() + days * 864e5).toUTCString()
    document.cookie = name + '=' + encodeURIComponent(value) + '; expires=' + expires + '; path=' + path
  }

  const deleteCookie = (name) => {
    setCookie(name, '', -1)
  }

  const api = {
    install(app) {
      app.provide('keycloak', api)
      app.config.globalProperties.$keycloak = api
    },
    async init() {
      return new Promise((resolve, reject) => {
        keycloak.init({onLoad: 'login-required', promiseType: 'native'}).then(auth => {
          if (auth) {
            setCookie(JWT_COOKIE_NAME, keycloak.token)
            setInterval(() => {
              keycloak.updateToken(70).then(refreshed => {
                if (refreshed) {
                  setCookie(JWT_COOKIE_NAME, keycloak.token)
                }
              }).catch(err => {
                console.error('Failed to refresh auth token', err)
              })
            }, 60000)

            keycloak.loadUserInfo()
              .then(info => {
                const roles = info.realm_access?.roles || []
                localStorage.setItem('user', JSON.stringify({ username: info.preferred_username, email: info.email, firstName: info.given_name, lastName: info.family_name, name: info.name, sub: info.sub, roles }))
              })
              .then(() => backend.get("/user"))
              .then(() => resolve(keycloak))
              .catch(reject)
          } else {
            reject('could not authorize')
          }
        }).catch(err => {
          console.error('Initialization failed', err)
          keycloak.clearToken()
          deleteCookie(JWT_COOKIE_NAME)
          reject(err)
        })
      })
    },
    logout(props = {}) {
      keycloak.logout(props)
    },
  }
  return api
}

export default createKeycloak()
