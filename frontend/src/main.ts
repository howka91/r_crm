import { createPinia } from "pinia"
import PrimeVue from "primevue/config"
import ConfirmationService from "primevue/confirmationservice"
import ToastService from "primevue/toastservice"
import { createApp } from "vue"

import App from "@/App.vue"
import { abilitiesPlugin, ability } from "@/libs/acl"
import { i18n } from "@/libs/i18n"
import { primevuePreset } from "@/libs/primevue"
import { router } from "@/router"

import "primeicons/primeicons.css"
import "@/assets/styles/main.css"

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(i18n)
app.use(PrimeVue, {
  unstyled: true,
  pt: primevuePreset,
  ripple: true,
})
app.use(ToastService)
app.use(ConfirmationService)
app.use(abilitiesPlugin, ability, { useGlobalProperties: true })

app.mount("#app")
