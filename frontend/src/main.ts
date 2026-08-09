import { createApp } from 'vue'
import { RouterView } from 'vue-router'
import { QueryClient, VueQueryPlugin } from '@tanstack/vue-query'
import { router } from './router'

createApp(RouterView)
  .use(VueQueryPlugin, { queryClient: new QueryClient() })
  .use(router)
  .mount('#app')
