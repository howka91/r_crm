# Handoff: Smart RC · Yangi Mahalla — Redesign

## Overview
Визуальный и системный рестайл CRM недвижимости «Yangi Mahalla» (ЖК в Ташкенте).
Исходная система — Vuexy-шаблон (Vue 3 + Tailwind + PrimeVue). Цель рестайла:

- заменить фиолетовый Vuexy-primary на фирменный **тёмно-зелёный Yangi Mahalla** с **лаймовым акцентом** из логотипа;
- уплотнить сетку до 8 px, обновить типографику (Inter Tight + JetBrains Mono);
- модернизировать общий каркас (sidebar + floating navbar), статусы шахматки, таблицы, формы, карточки, аутентификацию.

Структура/навигация оригинального приложения сохранена — поменялся только визуальный язык.

## About the Design Files
Файлы в этом пакете — **дизайн-референсы, сделанные в HTML + React (Babel in-browser)**. Это прототипы, показывающие итоговый вид и поведение интерфейса. **Их не нужно копировать напрямую в продакшен.**

Задача — **воспроизвести эти дизайны в существующей кодовой базе Yangi Mahalla** (Vue 3 + Tailwind + PrimeVue), используя её устоявшиеся паттерны, компоненты и структуру файлов. Если какого-то компонента ещё нет — добавить по образцу, следуя имеющимся соглашениям.

## Fidelity
**High-fidelity.** Все значения (цвета в oklch, радиусы, отступы, размеры шрифта, веса, hover-состояния) финальные и готовы к пиксель-перфект реализации. Единственное, что осталось на откуп разработчику — выбор конкретных PrimeVue / Tailwind утилит и способ разбить это на Vue-компоненты.

## Design Tokens

### Цвета (oklch)

| Токен | Значение | Где используется |
|---|---|---|
| `--primary` | `oklch(0.38 0.10 155)` | Бренд, CTA, активная навигация, акценты |
| `--primary-h` | `oklch(0.32 0.10 155)` | Hover для primary |
| `--primary-soft` | `oklch(0.96 0.035 155)` | Фон soft-кнопок, chip-primary, аватары |
| `--primary-accent` | `oklch(0.72 0.18 130)` | Лаймовый акцент из логотипа (левая полоска активного пункта меню, плашка-логотип) |
| `--bg` | `oklch(0.985 0.005 285)` | Фон страницы |
| `--surface` | `#ffffff` | Карточки, sidebar, navbar |
| `--sunken` | `oklch(0.97 0.007 285)` | Hover строк таблицы, заголовки таблицы, вложенные панели |
| `--line` | `oklch(0.92 0.008 285)` | Основные разделители / border |
| `--line-soft` | `oklch(0.955 0.007 285)` | Слабые разделители (ряды таблицы) |
| `--text` | `oklch(0.24 0.02 285)` | Основной текст |
| `--muted` | `oklch(0.52 0.018 285)` | Вторичный текст |
| `--subtle` | `oklch(0.70 0.015 285)` | Третичный текст, eyebrow, mono-метки |

### Семантические

| Токен | Цвет | Soft-фон | Назначение |
|---|---|---|---|
| `--success` | `oklch(0.64 0.14 155)` | `oklch(0.96 0.04 155)` | Свободно, оплачено, действует |
| `--warning` | `oklch(0.74 0.15 75)` | `oklch(0.97 0.05 75)` | Бронь, ожидание |
| `--danger` | `oklch(0.58 0.19 22)` | `oklch(0.97 0.04 22)` | Продано, просрочка |
| `--info` | `oklch(0.68 0.13 225)` | `oklch(0.96 0.04 225)` | Акция, информационные статусы, лид |

### Типографика

Семейства: **Inter Tight** (основное), **JetBrains Mono** (ID, суммы, даты, метки).

| Роль | Размер | Вес | Letter-spacing |
|---|---|---|---|
| Display | 34 px | 600 | -0.025em |
| H1 | 26–28 px | 600 | -0.025em |
| H2 | 20 px | 600 | -0.015em |
| H3 | 16 px | 600 | -0.01em |
| Body | 14 px | 400 | 0 |
| Small | 13 px | 400 | 0 |
| Eyebrow | 11 px | 500 | 0.12em uppercase |
| Mono-label | 10.5–11 px | 500 | 0 |

### Отступы (8-px grid)
`4 · 8 · 12 · 16 · 24 · 32 · 48`

### Радиусы
- `xs` 7 · `sm` 8 · `md` 10 · `lg` 14 · `full` 999
- Кнопки: 10 (sm — 8, xs — 7)
- Инпуты: 10 (sm — 8)
- Карточки: 14
- Chips: 7

### Возвышенность
- **flat** — без тени
- **card** — `0 1px 2px rgba(20,20,50,.04), 0 0 0 1px rgba(20,20,50,.04)`
- **float** — `0 6px 20px -6px rgba(20,20,50,.1), 0 1px 2px rgba(20,20,50,.04)` (navbar)
- **modal** — `0 22px 48px -10px rgba(20,20,50,.22), 0 2px 6px rgba(20,20,50,.06)`
- Primary-кнопка: `0 2px 10px -2px oklch(0.38 0.10 155 / .45)` + inset highlight
- Фокус инпута: `0 0 0 3px oklch(0.38 0.10 155 / .15)`

## Screens / Views

### 1. Design System reference (`ds-tokens.jsx`)
Показательные страницы токенов и атомов. **Не нужно переносить один-в-один** — использовать как единый источник правды для стилей. Содержит: палитру, типографическую шкалу, spacing / radius / elevation, легенду статусов квартир, набор кнопок, инпутов, chips и эталонную таблицу.

### 2. App Shell (`ds-shell.jsx`)
Глобальный каркас всех экранов приложения.

**Sidebar** (252 px, белый, border-right):
- Логотип: квадрат 36 × 36, radius 10, фон `--primary`, текст «YM» цветом `--primary-accent`, вес 700, letter-spacing −0.08em
- Подпись: «Yangi Mahalla» (14.5 px / 600) + «Smart RC · 6.4» (10.5 px mono, `--subtle`)
- Группы пунктов с eyebrow-заголовками (10 px uppercase, letter-spacing 0.12em, `--subtle`)
- Пункт: 9 × 14 px, radius 10, 13 px, иконка PrimeIcons слева (13 px)
- Активный: градиент `linear-gradient(100deg, var(--primary) 0%, oklch(0.44 0.11 150) 100%)`, белый текст, **левая полоска 3 px `--primary-accent`** (реализовано через `border-left` + компенсирующий `padding-left`), shadow `0 8px 20px -8px oklch(0.38 0.10 155 / .5)`
- Карточка пользователя в низу: sunken-фон, аватар-круг с инициалами (background `--primary`, текст `--primary-accent`)

**Navbar** (floating, 14 px margin, радиус 14):
- Крошки (левое), глобальный поиск с `⌘K`-подсказкой (правое), колокольчик, переключатель RU/UZ, слот для primary-CTA

### 3. Dashboard (`Dashboard`)
4 stat-карточки (Свободно / Бронь / Продано / Выручка) + 2/3 bar-chart «Динамика договоров» за 6 месяцев (primary + primary-soft) + 1/3 список «Недавние договоры» с аватарами и chip-статусами.

### 4. Шахматка (`Shaxmatka`)
Цель — вертикальная сетка этажей. **14 этажей × 8 секций**, ячейка 40 px, radius 7.
Цвета ячеек — soft семантические с контрастным текстом:
- Свободно: bg `oklch(0.96 0.04 155)`, text `oklch(0.38 0.12 155)`, border `oklch(0.88 0.08 155)`
- Бронь: 75 hue аналогично
- Продано: 22 hue
- Акция: 225 hue

Над сеткой — сегмент «Блок A/B/C» (soft-active), легенда с количеством.

### 5. Канбан (`Kanban`)
5 колонок (Новые лиды / Квалификация / Презентация / Договор / Закрыт). Карточка: аватар-круг инициалов, имя, источник, chip с площадью (mono), относительное время.

### 6. Клиенты (`Clients`)
Фильтр-бар с селекторами и активными chip-фильтрами. Таблица с аватарами-инициалами, mono-телефонами, chip-статусами, пагинацией (soft-active номер страницы).

### 7. Контракт / Wizard (`Contract`)
Шаговый визард (5 шагов), 2/3 форма + 1/3 summary-карточка с градиентным верхом. Форма «Оплата»: селекты, mono-инпуты сумм, вложенная таблица-график платежей.

### 8. Login (`Login`)
Split: 2/3 брендовая панель (градиент `linear-gradient(135deg, oklch(0.28 0.08 155) 0%, oklch(0.20 0.06 155) 100%)`, радиальные акценты primary и accent), «призрачная» шахматка, плашка-логотип «YM» на лаймовом акцентном фоне. 1/3 форма логина.

## Interactions & Behavior
- **Hover карточки** (`.card-hover`): border → `oklch(0.86 0.01 285)`, тень float.
- **Hover ряда таблицы**: фон → `oklch(0.98 0.005 285)`.
- **Фокус инпута**: border → `--primary`, ring-shadow.
- **Soft-кнопка**: hover bg → `oklch(0.93 0.045 155)`.
- **Primary-кнопка disabled**: opacity 0.5, cursor not-allowed.
- Все transition: `all .15s` для кнопок, `border-color/box-shadow .15s` для инпутов.

## Component mapping (Vuexy → новая система)

| Vuexy / PrimeVue | Новая реализация |
|---|---|
| `.btn-primary` (Vuexy) | `.btn.btn-primary` с тёмно-зелёным `--primary` + кастомная тень |
| `p-button-outlined` | `.btn.btn-ghost` (transparent + 1 px border) |
| `p-badge` | `.chip` + семантические модификаторы |
| `p-datatable` заголовок | `.tbl th` с `background: --sunken`, uppercase eyebrow |
| `p-dialog` | Карточка `.card`, padding 24, тень modal |
| Vuexy sidebar active | Активный `.nav-item` — градиент + `border-left` лаймовый |

## Files in this bundle

- `Smart RC - Modernized Design.html` — корневой документ, собирающий design canvas из всех ниже.
- `design-canvas.jsx` — стартовая утилита (pan/zoom/drag) для презентации вариантов.
- `ds-tokens.jsx` — эталон токенов и атомов (палитра, типографика, кнопки, таблица).
- `ds-shell.jsx` — `<Shell>`, `<Sidebar>`, `<Navbar>` — общий каркас приложения.
- `ds-screens.jsx` — 6 экранов: Dashboard, Shaxmatka, Kanban, Clients, Contract, Login.

Открыть локально: просто открыть `Smart RC - Modernized Design.html` в браузере (все зависимости по CDN — Tailwind, PrimeIcons, React 18, Babel Standalone).

## Assets
Внешние ассеты не использовались. Иконки — **PrimeIcons 7.0.0** (CDN), шрифты — **Google Fonts**: Inter Tight (400/500/600/700) и JetBrains Mono (400/500). QR-коды и аватары на скринах оригинального приложения заменены плейсхолдерами из инициалов.

## Next steps для разработчика
1. Добавить новые CSS-переменные в корневой SCSS/CSS проекта (заменить старые Vuexy-токены primary).
2. Подключить Inter Tight + JetBrains Mono (Google Fonts или self-host).
3. Переопределить `.btn-primary`, `.badge`, `.p-datatable` темы PrimeVue через существующую систему переопределений.
4. Обновить `AppVerticalMenu.vue` — добавить лаймовую левую полоску и градиент в активный пункт.
5. Пройти по экранам в порядке: Login → Dashboard → Clients → Shaxmatka → Kanban → Contract.
