import { createApp } from 'vue'
import { createPinia } from 'pinia'
import './styles/tokens.css'
import App from './App.vue'
import router from './router'
import VueApexCharts from 'vue3-apexcharts'
import { useThemeStore } from './stores/theme'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia).use(router).use(VueApexCharts)

// Applied before mount so the first paint is already the right theme.
useThemeStore(pinia).init()

app.mount('#app')
