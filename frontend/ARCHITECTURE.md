# Frontend Architecture — Yangi Mahalla · Smart RC

Этот документ — карта для разработчиков, которые работали на **старом** проекте
(`yangi-mahalla-main/` — Vue 2 + Vuexy + Vuex + JS). Здесь описана новая
кодовая база (**Vue 3 + PrimeVue + Pinia + TypeScript**) и показано, где
что лежит в сравнении со старой.

Структура папок намеренно сохранена максимально близко к старой — чтобы не
нужно было переучивать навигацию по проекту. Под-капотные вещи, которые
поменялись из-за Vue 3 / Pinia, — собраны в разделе «Что изменилось».

---

## Структура `src/`

```
src/
├── App.vue
├── main.ts                      ← регистрация плагинов, монтаж приложения
│
├── api/                         ← HTTP-клиенты, по одному файлу на домен
│   ├── auth.ts                  ←  /auth/login, /auth/me, /auth/logout
│   ├── administration.ts        ←  staffApi + roleApi (CRUD для /staff, /roles)
│   └── permissions.ts           ←  /permissions/tree
│
├── assets/
│   └── styles/
│       └── main.css             ← токены (CSS variables) + @apply-классы
│
├── layouts/                     ← КАРКАСЫ
│   ├── components/
│   │   ├── Navbar.vue           ← плавающий верх (крошки, поиск, локаль)
│   │   └── Sidebar.vue          ← вертикальный сайдбар с меню + user-card
│   ├── vertical/
│   │   └── LayoutVertical.vue   ← основной залогиненный макет
│   └── full/
│       └── LayoutFull.vue       ← для public-экранов (Login, 404, 403)
│
├── libs/                        ← ШАРЕННЫЕ УТИЛИТЫ / ОБЁРТКИ
│   ├── axios.ts                 ← настроенный http instance + tokenStore + refresh-interceptor
│   ├── acl/
│   │   └── index.ts             ← CASL ability + useAbility()
│   ├── i18n/
│   │   ├── index.ts             ← createI18n() + setLocale()
│   │   └── locales/{ru,uz,oz}.json
│   └── primevue/
│       └── index.ts             ← PrimeVue "pt:" preset (пока пустой каркас)
│
├── navigation/                  ← КОНФИГИ МЕНЮ
│   └── vertical/
│       ├── types.ts             ← NavLink / NavGroup
│       ├── main.ts              ← группа «Главное»
│       ├── sales.ts             ← «Продажи»
│       ├── contracts.ts         ← «Договоры»
│       ├── finance.ts           ← «Финансы»
│       ├── references.ts        ← «Справочники»
│       ├── sms_reports_admin.ts ← «SMS · Отчёты · Админ.»
│       └── index.ts             ← агрегатор
│
├── router/
│   ├── index.ts                 ← сборка, public routes, guard
│   └── administration.ts        ← admin/users, admin/roles, admin/roles/:id
│                                  (новые домены — каждый в свой файл)
│
├── store/                       ← Pinia stores (по одному файлу на домен)
│   ├── auth.ts                  ← user, login/logout/fetchMe
│   └── permissions.ts           ← дерево прав, check(), CASL sync
│
├── types/
│   └── models.ts                ← Staff, Role, PermissionNode и т.д.
│
└── views/
    ├── Home.vue                 ← Дашборд
    ├── Login.vue
    ├── error/
    │   ├── Error404.vue
    │   └── Forbidden.vue
    └── modules/                 ← ДОМЕННЫЕ ЭКРАНЫ
        └── Administration/
            └── userManagement/
                ├── index.vue         ← список сотрудников
                ├── roles.vue         ← список ролей
                ├── roleView.vue      ← редактор одной роли
                └── components/
                    └── PermissionTreeEditor.vue
```

---

## Mapping: старый проект → новый

### Папки

| Vuexy (`yangi-mahalla-main/src/`)                | Новая                                              |
|--------------------------------------------------|----------------------------------------------------|
| `@core/`                                         | **(удалено)** — Vuexy-шаблон не тянем              |
| `api/{domain}.js`                                | `api/{domain}.ts`                                  |
| `auth/`                                          | `libs/acl/` + `store/auth.ts` + `libs/axios.ts`    |
| `layouts/vertical/LayoutVertical.vue`            | `layouts/vertical/LayoutVertical.vue` (то же имя)  |
| `layouts/full/LayoutFull.vue`                    | `layouts/full/LayoutFull.vue`                      |
| `layouts/components/Navbar.vue`                  | `layouts/components/Navbar.vue`                    |
| `libs/axios.js`                                  | `libs/axios.ts`                                    |
| `libs/acl/`                                      | `libs/acl/`                                        |
| `libs/i18n/`                                     | `libs/i18n/`                                       |
| `libs/toastification.js`, `libs/sweet-alerts.js` | ← будет `libs/` по мере нужды (PrimeVue Toast/ConfirmDialog) |
| `mixins/{areYouSure,checkPermission,...}.js`     | **заменено на composables + `store/permissions.ts`** |
| `navigation/vertical/*.js`                       | `navigation/vertical/*.ts` (то же имя per-domain)  |
| `router/{domain}.js` + `router/index.js`         | `router/{domain}.ts` + `router/index.ts`           |
| `store/{domain}/{actions,getters,mutations,state}.js` | `store/{domain}.ts` (**один файл**, см. ниже)  |
| `views/modules/{Domain}/index.vue + components/` | `views/modules/{Domain}/index.vue + components/`   |
| `views/error/Error404.vue`                       | `views/error/Error404.vue`                         |
| `views/Home.vue`, `views/Login.vue`              | `views/Home.vue`, `views/Login.vue`                |

### Что не перенеслось 1-в-1 (и почему)

1. **`@core/`** (Vuexy-ядро): удалён целиком. Это чужой шаблон.
2. **`mixins/`**: в Vue 3 mixins считаются анти-паттерном, заменяются на composables.
   `mixins/checkPermission.js` переехал в `store/permissions.ts#check()` —
   вызывается из компонентов через `usePermissionStore().check("clients.view")`.
3. **`store/{domain}/{actions,getters,mutations,state}.js`** (Vuex, 4 файла на домен):
   в Pinia (`setup`-синтаксис) сжимается в **один файл** на домен. См. `store/auth.ts` —
   `ref/computed` как state/getters, обычные функции как actions. Это не стиль «я полдела
   сделал» — это идиома Pinia из её официальной документации.

---

## Что изменилось в стеке

| Старое              | Новое                    | Зачем            |
|---------------------|--------------------------|------------------|
| Vue 2 Options API   | Vue 3 `<script setup>`   | Текущая LTS      |
| Vuex 3              | Pinia (setup-syntax)     | Официальный стор для Vue 3, без мутаций |
| JavaScript          | TypeScript 5             | Типобезопасность в CRUD; `src/types/models.ts` — источник правды |
| BootstrapVue / Vuexy | PrimeVue 4 (unstyled + pt: preset) | Более современная, TS-native |
| ACL v4              | CASL `@casl/ability` v6 + `@casl/vue` v2 | Vue 3 plugin API |
| Feather Icons       | PrimeIcons 7             | Из коробки с PrimeVue |
| `vue-i18n` v8       | `vue-i18n` v10           | Vue 3 native (`legacy: false`) |
| SCSS (Vuexy темы)   | Tailwind 3 + CSS-переменные | Мы не наследуем тему Vuexy — новый дизайн-код |

---

## Как читать Pinia store (для тех, кто писал Vuex)

### Старый Vuex модуль:

```js
// store/auth/state.js
export default () => ({ user: null, loading: false })

// store/auth/mutations.js
export default {
  SET_USER(state, user) { state.user = user },
  SET_LOADING(state, loading) { state.loading = loading },
}

// store/auth/actions.js
export default {
  async login({ commit }, { email, password }) {
    commit("SET_LOADING", true)
    const { user } = await authApi.login({ email, password })
    commit("SET_USER", user)
    commit("SET_LOADING", false)
  },
}

// store/auth/getters.js
export default {
  isAuthenticated: (state) => state.user !== null,
}

// использование
this.$store.dispatch("auth/login", { email, password })
this.$store.getters["auth/isAuthenticated"]
```

### Новый Pinia store:

```ts
// store/auth.ts
import { defineStore } from "pinia"
import { computed, ref } from "vue"

export const useAuthStore = defineStore("auth", () => {
  const user = ref<Staff | null>(null)        // ← state
  const loading = ref(false)
  const isAuthenticated = computed(            // ← getter
    () => user.value !== null,
  )

  async function login(email: string, password: string) {  // ← action
    loading.value = true
    const { user: signedIn } = await authApi.login({ email, password })
    user.value = signedIn
    loading.value = false
  }

  return { user, loading, isAuthenticated, login }
})

// использование
const auth = useAuthStore()
await auth.login(email, password)
auth.isAuthenticated
```

**Правила соответствия:**
- `state.value.X` → `X.value` (внутри стора) или `store.X` (снаружи).
- `commit("SET_X", v)` → `X.value = v`. Никаких мутаций отдельно.
- `dispatch("auth/login", ...)` → `useAuthStore().login(...)`.
- `getters.isAuthenticated` → `computed(() => ...)`.
- `mapState / mapActions / mapGetters` не нужны — прямой доступ к стору.

---

## Как читать компонент (`<script setup>` vs Options API)

### Старый:
```vue
<script>
export default {
  data() { return { count: 0 } },
  computed: { double() { return this.count * 2 } },
  methods: { inc() { this.count++ } },
  mounted() { this.inc() },
}
</script>
<template><button @click="inc">{{ double }}</button></template>
```

### Новый:
```vue
<script setup lang="ts">
import { computed, onMounted, ref } from "vue"

const count = ref(0)
const double = computed(() => count.value * 2)
function inc() { count.value++ }
onMounted(inc)
</script>
<template><button @click="inc">{{ double }}</button></template>
```

**Правила:**
- `data()` → `ref()` / `reactive()`.
- `computed: { x }` → `const x = computed(...)`.
- `methods: { foo }` → обычная функция `function foo() {}`.
- `mounted` → `onMounted(() => {})`.
- `this.$store` → `const store = useXxxStore()`.
- `this.$route / this.$router` → `const route = useRoute() / useRouter()`.
- `this.$t` → `const { t } = useI18n()`.
- Внутри `<script setup>` `this` нет. Всё, что объявлено на верхнем уровне, доступно в шаблоне.

---

## Дизайн-токены (Yangi Mahalla)

Цвета, типографика, радиусы, тени — единый источник правды:
`src/assets/styles/main.css` (CSS-переменные `--primary`, `--surface`, и т.д.) +
`tailwind.config.ts` (мапит их на `bg-ym-primary`, `text-ym-muted`, `shadow-ym-float`).

Два одинаково валидных способа применять токены:

```vue
<!-- через Tailwind-утилиту: -->
<div class="bg-ym-primary text-ym-primary-accent shadow-ym-primary-lg">...</div>

<!-- напрямую через CSS-переменную (редко — для нестандартных значений): -->
<div style="background: var(--primary)">...</div>
```

**Правило:** предпочитайте Tailwind-утилиты. `style=""` — только если нужно
значение, которое не положено утилитой (например, градиент в нестандартном угле).

Полный справочник токенов — в `frontend/design_handoff_smart_rc_extracted/design_handoff_smart_rc/README.md`.
