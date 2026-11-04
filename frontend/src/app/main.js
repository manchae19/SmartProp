import '../styles/style.css'
import { createApp } from 'vue'
import App from './App.vue'
import router from './router.js'
import {initializeAuth} from '../features/auth/api.js'

const app = createApp(App)
initializeAuth()
app.use(router)
app.mount('#app')