import { createApp } from 'vue'
import { createPinia } from 'pinia'
import './styles/tokens.css'
import App from './App.vue'
import router from './router'
import VueApexCharts from 'vue3-apexcharts'
import { useThemeStore } from './stores/theme'
import { useAuthStore } from './stores/auth'
 
const app = createApp(App)
const pinia = createPinia()
 
app.use(pinia).use(router).use(VueApexCharts)
 
// Applied before mount so the first paint is already the right theme.
useThemeStore(pinia).init()
 
// The session is over: the refresh token expired, or a password reset ended
// every session on the account. A page that needs sign-in would otherwise
// sit there half-empty, so send the person to the sign-in page they use.
window.addEventListener('novus:session-ended', () => {
  const auth = useAuthStore(pinia)
  const route = router.currentRoute.value
  const staff = auth.role ? auth.role !== 'READER' : !!route.meta.roles
  auth.logout()
  if (route.meta.requiresAuth) router.replace(staff ? '/staff/login?ended=1' : '/login?ended=1')
})
 
app.mount('#app')
