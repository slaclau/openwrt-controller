// if you just want to import css
import '@controller/style/index.scss'

import 'element-plus/theme-chalk/dark/css-vars.css'

import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import App from './App.vue'
import { router } from './router'
import { client } from './sdk/client.gen'
client.setConfig({ baseUrl: window.location.origin + '/api' })

const app = createApp(App)
const pinia = createPinia()
app.use(ElementPlus)
app.use(pinia)
app.use(router)

app.config.globalProperties.window = window

app.mount('#app')
