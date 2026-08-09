import { createApp } from 'vue'
import { QueryClient, VueQueryPlugin } from '@tanstack/vue-query'
import App from './App.vue'
createApp(App).use(VueQueryPlugin, { queryClient: new QueryClient() }).mount('#app')
