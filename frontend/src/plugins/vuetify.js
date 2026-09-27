/**
 * plugins/vuetify.js
 *
 * Framework documentation: https://vuetifyjs.com`
 */

import '@mdi/font/css/materialdesignicons.css'
import 'vuetify/styles'
import { aliases } from 'vuetify/iconsets/mdi'
import { useColorMode } from '@vueuse/core'
import { createVuetify } from 'vuetify'
import colors from 'vuetify/util/colors'

import builtinSV from 'vuetify/lib/locale/sv.mjs'
import builtinEN from 'vuetify/lib/locale/en.mjs'

import mySV from '@/locale/sv'
import myEN from '@/locale/en'

const sv = Object.assign({}, builtinSV, mySV)
const en = Object.assign({}, builtinEN, myEN)

const mode = useColorMode()

export default createVuetify({
  theme: {
    //defaultTheme: 'light',
    defaultTheme: mode.value,
    themes: {
      light: {
        dark: false,
        colors: {
          primary: colors.blue.base,
          secondary: colors.blue.lighten2,
          success: colors.green.base,
          error: colors.red.base,
        },
      },
      dark: {
        dark: true,
        colors: {
          primary: colors.blue.darken4,
          secondary: colors.blue.lighten2,
          success: colors.green.darken4,
          error: colors.red.darken4,
        },
      },
    },
  },
  locale: {
    locale: navigator.language.substring(0, 2),
    fallback: 'sv',
    messages: { sv, en },
  },
  icons: {
    aliases: {
      ...aliases,
      ok: 'mdi-check',
      add: 'mdi-plus',
      edit: 'mdi-pencil-outline',
      save: 'mdi-content-save',
      delete: 'mdi-trash-can-outline',
      map: 'mdi-map-marker-outline',
    },
  },
  defaults: {
    VBtn: {
      style: 'text-transform: none;',
    },
    VSwitch: { color: 'primary' },
  },
})
