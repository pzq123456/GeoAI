import { createApp } from 'vue'
import { createPinia } from 'pinia'

import '@/styles/theme.css'

import App from '@/layouts/app.vue'

const app = createApp(App)

app.use(createPinia())

app.mount('#app')
