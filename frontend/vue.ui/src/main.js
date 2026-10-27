import './style.css'
import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import {initializeAuth} from './services/api.js'

const app = createApp(App)
initializeAuth()
app.use(router)
app.mount('#app')