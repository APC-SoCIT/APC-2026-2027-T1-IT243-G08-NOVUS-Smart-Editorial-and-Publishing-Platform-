import { createApp } from 'vue'
import { createPinia } from 'pinia'
import './styles/tokens.css'
import App from './App.vue'
import router from './router'
import VueApexCharts from 'vue3-apexcharts'

createApp(App)
  .use(createPinia())
  .use(router)
  .use(VueApexCharts)
  .mount('#app')
