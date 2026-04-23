/**
 * Catalog of pre-defined placeholders for contract templates.
 *
 * The admin doesn't hand-write dotted paths — they pick from this list
 * of pre-defined buttons on the template editor. Each entry knows the
 * short `key` (what ends up in `{{…}}` in the HTML body), the backend
 * `path` (resolved against `build_context` — see
 * `apps/contracts/services/snapshot.py`), and trilingual labels for
 * the picker UI.
 *
 * Mapping is derived from the legacy `clients_contracttemplatefield`
 * table (39 rows in the 2025-11 dump). Items that have no direct
 * analogue in the new snapshot (dollar rate, mortgage-specific
 * calcs, construction end date) were dropped rather than faked.
 */

export type PlaceholderCategory =
  | "contract"
  | "client"
  | "signer"
  | "apartment"
  | "project"
  | "developer"
  | "calculation"
  | "dates"

export interface CatalogEntry {
  /** What the admin writes in the HTML body: `{{key}}`. */
  key: string
  /** Dotted path resolved against the Contract context tree. */
  path: string
  /** Grouping in the picker. */
  category: PlaceholderCategory
  /** Human-readable labels. Shown on the button + in the toolbar dropdown. */
  labels: { ru: string; uz: string; oz: string }
}

/** Trilingual section headers. */
export const CATEGORY_LABELS: Record<
  PlaceholderCategory,
  { ru: string; uz: string; oz: string }
> = {
  contract: {
    ru: "Договор",
    uz: "Shartnoma",
    oz: "Шартнома",
  },
  client: {
    ru: "Клиент",
    uz: "Mijoz",
    oz: "Мижоз",
  },
  signer: {
    ru: "Подписант",
    uz: "Imzolovchi",
    oz: "Имзоловчи",
  },
  apartment: {
    ru: "Квартира",
    uz: "Kvartira",
    oz: "Квартира",
  },
  project: {
    ru: "ЖК",
    uz: "Turar-joy majmuasi",
    oz: "Турар-жой мажмуаси",
  },
  developer: {
    ru: "Застройщик",
    uz: "Quruvchi",
    oz: "Қурувчи",
  },
  calculation: {
    ru: "Расчёт оплаты",
    uz: "To'lov hisoblamasi",
    oz: "Тўлов ҳисобламаси",
  },
  dates: {
    ru: "Даты и время",
    uz: "Sana va vaqt",
    oz: "Сана ва вақт",
  },
}

export const PLACEHOLDER_CATALOG: CatalogEntry[] = [
  // --- Contract ----------------------------------------------------------
  {
    key: "contract_number",
    path: "contract.contract_number",
    category: "contract",
    labels: {
      ru: "Номер договора",
      uz: "Shartnoma raqami",
      oz: "Шартнома рақами",
    },
  },
  {
    key: "contract_date",
    path: "contract.date",
    category: "contract",
    labels: {
      ru: "Дата договора",
      uz: "Shartnoma sanasi",
      oz: "Шартнома санаси",
    },
  },
  {
    key: "total_price",
    path: "contract.total_amount",
    category: "contract",
    labels: {
      ru: "Общая сумма договора",
      uz: "Shartnoma summasi",
      oz: "Шартнома суммаси",
    },
  },
  {
    key: "down_payment",
    path: "contract.down_payment",
    category: "contract",
    labels: {
      ru: "Первоначальный взнос",
      uz: "Birinchi to'lov",
      oz: "Биринчи тўлов",
    },
  },
  {
    key: "related_person",
    path: "contract.related_person",
    category: "contract",
    labels: {
      ru: "Дополнительный подписант (текст)",
      uz: "Qo'shimcha imzolovchi (matn)",
      oz: "Қўшимча имзоловчи (матн)",
    },
  },

  // --- Client (buyer entity) --------------------------------------------
  {
    key: "client_name",
    path: "client.full_name",
    category: "client",
    labels: {
      ru: "ФИО / Название клиента",
      uz: "Mijoz ismi / nomi",
      oz: "Мижоз исми / номи",
    },
  },
  {
    key: "client_inn",
    path: "client.inn",
    category: "client",
    labels: {
      ru: "ИНН клиента",
      uz: "Mijoz INN",
      oz: "Мижоз ИНН",
    },
  },
  {
    key: "client_pin",
    path: "client.pin",
    category: "client",
    labels: {
      ru: "ПИНФЛ клиента",
      uz: "Mijoz JShShIR",
      oz: "Мижоз ЖШШИР",
    },
  },
  {
    key: "client_address",
    path: "client.address",
    category: "client",
    labels: {
      ru: "Адрес клиента",
      uz: "Mijoz manzili",
      oz: "Мижоз манзили",
    },
  },
  {
    key: "client_phone",
    path: "client.phones.0",
    category: "client",
    labels: {
      ru: "Телефон клиента",
      uz: "Mijoz telefoni",
      oz: "Мижоз телефони",
    },
  },

  // --- Signer (ClientContact) -------------------------------------------
  {
    key: "signer_name",
    path: "signer.full_name",
    category: "signer",
    labels: {
      ru: "ФИО подписанта",
      uz: "Imzolovchi ismi",
      oz: "Имзоловчи исми",
    },
  },
  {
    key: "signer_role",
    path: "signer.role",
    category: "signer",
    labels: {
      ru: "Должность подписанта",
      uz: "Imzolovchi lavozimi",
      oz: "Имзоловчи лавозими",
    },
  },
  {
    key: "signer_phone",
    path: "signer.phones.0",
    category: "signer",
    labels: {
      ru: "Телефон подписанта",
      uz: "Imzolovchi telefoni",
      oz: "Имзоловчи телефони",
    },
  },
  {
    key: "passport_series",
    path: "signer.passport.series",
    category: "signer",
    labels: {
      ru: "Серия паспорта",
      uz: "Passport seriyasi",
      oz: "Паспорт серияси",
    },
  },
  {
    key: "passport_number",
    path: "signer.passport.number",
    category: "signer",
    labels: {
      ru: "Номер паспорта",
      uz: "Passport raqami",
      oz: "Паспорт рақами",
    },
  },
  {
    key: "passport_issued_by",
    path: "signer.passport.issued_by",
    category: "signer",
    labels: {
      ru: "Кем выдан паспорт",
      uz: "Passport kim tomonidan berilgan",
      oz: "Паспорт ким томонидан берилган",
    },
  },
  {
    key: "passport_issued_date",
    path: "signer.passport.issued_date",
    category: "signer",
    labels: {
      ru: "Дата выдачи паспорта",
      uz: "Passport berilgan sana",
      oz: "Паспорт берилган сана",
    },
  },
  {
    key: "passport_registration",
    path: "signer.passport.registration_address",
    category: "signer",
    labels: {
      ru: "Адрес прописки",
      uz: "Propiska manzili",
      oz: "Прописка манзили",
    },
  },

  // --- Apartment --------------------------------------------------------
  {
    key: "apt_number",
    path: "apartment.number",
    category: "apartment",
    labels: {
      ru: "Номер квартиры",
      uz: "Kvartira raqami",
      oz: "Квартира рақами",
    },
  },
  {
    key: "apt_rooms",
    path: "apartment.rooms_count",
    category: "apartment",
    labels: {
      ru: "Количество комнат",
      uz: "Xonalar soni",
      oz: "Хоналар сони",
    },
  },
  {
    key: "apt_area",
    path: "apartment.area",
    category: "apartment",
    labels: {
      ru: "Площадь, м²",
      uz: "Maydon, m²",
      oz: "Майдон, м²",
    },
  },
  {
    key: "apt_bti_area",
    path: "apartment.total_bti_area",
    category: "apartment",
    labels: {
      ru: "Площадь по БТИ, м²",
      uz: "BTI bo'yicha maydon, m²",
      oz: "БТИ бўйича майдон, м²",
    },
  },
  {
    key: "apt_total_price",
    path: "apartment.total_price",
    category: "apartment",
    labels: {
      ru: "Итоговая цена квартиры",
      uz: "Xonadonning umumiy narxi",
      oz: "Хонадоннинг умумий нархи",
    },
  },
  {
    key: "apt_floor",
    path: "apartment.floor.number",
    category: "apartment",
    labels: {
      ru: "Этаж",
      uz: "Qavat",
      oz: "Қават",
    },
  },
  {
    key: "apt_section",
    path: "apartment.floor.section.number",
    category: "apartment",
    labels: {
      ru: "Номер подъезда",
      uz: "Yo'lak raqami",
      oz: "Йўлак рақами",
    },
  },
  {
    key: "apt_building",
    path: "apartment.floor.section.building.number",
    category: "apartment",
    labels: {
      ru: "Номер корпуса",
      uz: "Korpus raqami",
      oz: "Корпус рақами",
    },
  },

  // --- Project ----------------------------------------------------------
  {
    key: "project_title",
    path: "project.title.ru",
    category: "project",
    labels: {
      ru: "Название ЖК",
      uz: "Turar-joy nomi",
      oz: "Турар-жой номи",
    },
  },
  {
    key: "project_address",
    path: "project.address",
    category: "project",
    labels: {
      ru: "Адрес ЖК",
      uz: "Turar-joy manzili",
      oz: "Турар-жой манзили",
    },
  },

  // --- Developer --------------------------------------------------------
  {
    key: "dev_name",
    path: "developer.name.ru",
    category: "developer",
    labels: {
      ru: "Название застройщика",
      uz: "Quruvchi nomi",
      oz: "Қурувчи номи",
    },
  },
  {
    key: "dev_director",
    path: "developer.director",
    category: "developer",
    labels: {
      ru: "Директор застройщика",
      uz: "Quruvchi rahbari",
      oz: "Қурувчи раҳбари",
    },
  },
  {
    key: "dev_address",
    path: "developer.address",
    category: "developer",
    labels: {
      ru: "Адрес застройщика",
      uz: "Quruvchi manzili",
      oz: "Қурувчи манзили",
    },
  },
  {
    key: "dev_phone",
    path: "developer.phone",
    category: "developer",
    labels: {
      ru: "Телефон застройщика",
      uz: "Quruvchi telefoni",
      oz: "Қурувчи телефони",
    },
  },
  {
    key: "dev_email",
    path: "developer.email",
    category: "developer",
    labels: {
      ru: "Email застройщика",
      uz: "Quruvchi email",
      oz: "Қурувчи email",
    },
  },
  {
    key: "dev_inn",
    path: "developer.inn",
    category: "developer",
    labels: {
      ru: "ИНН застройщика",
      uz: "Quruvchi INN",
      oz: "Қурувчи ИНН",
    },
  },
  {
    key: "dev_bank_name",
    path: "developer.bank_name",
    category: "developer",
    labels: {
      ru: "Банк застройщика",
      uz: "Quruvchi banki",
      oz: "Қурувчи банки",
    },
  },
  {
    key: "dev_bank_account",
    path: "developer.bank_account",
    category: "developer",
    labels: {
      ru: "Расчётный счёт застройщика",
      uz: "Quruvchi hisob raqami",
      oz: "Қурувчи ҳисоб рақами",
    },
  },

  // --- Calculation -------------------------------------------------------
  {
    key: "calc_price_per_sqm",
    path: "calculation.new_price_per_sqm",
    category: "calculation",
    labels: {
      ru: "Цена за м² (со скидкой)",
      uz: "1 m² narxi (chegirma bilan)",
      oz: "1 м² нархи (чегирма билан)",
    },
  },
  {
    key: "calc_total_price",
    path: "calculation.new_total_price",
    category: "calculation",
    labels: {
      ru: "Итоговая стоимость (со скидкой)",
      uz: "Umumiy narx (chegirma bilan)",
      oz: "Умумий нарх (чегирма билан)",
    },
  },
  {
    key: "calc_initial",
    path: "calculation.initial_fee",
    category: "calculation",
    labels: {
      ru: "Первоначальный взнос (расчёт)",
      uz: "Birinchi to'lov (hisoblama)",
      oz: "Биринчи тўлов (ҳисоблама)",
    },
  },
  {
    key: "calc_monthly",
    path: "calculation.monthly_payment",
    category: "calculation",
    labels: {
      ru: "Ежемесячный платёж",
      uz: "Oylik to'lov",
      oz: "Ойлик тўлов",
    },
  },
  {
    key: "calc_months",
    path: "calculation.installment_months",
    category: "calculation",
    labels: {
      ru: "Количество месяцев рассрочки",
      uz: "Muddatli to'lov oylari soni",
      oz: "Муддатли тўлов ойлари сони",
    },
  },
  {
    key: "calc_discount",
    path: "calculation.discount_percent",
    category: "calculation",
    labels: {
      ru: "Скидка, %",
      uz: "Chegirma, %",
      oz: "Чегирма, %",
    },
  },

  // --- Dates -------------------------------------------------------------
  {
    key: "today",
    path: "today",
    category: "dates",
    labels: {
      ru: "Сегодняшняя дата",
      uz: "Bugungi sana",
      oz: "Бугунги сана",
    },
  },
  {
    key: "now",
    path: "now",
    category: "dates",
    labels: {
      ru: "Текущее время",
      uz: "Joriy vaqt",
      oz: "Жорий вақт",
    },
  },
]

/** Ordered categories for rendering (matches the logical reading order). */
export const CATALOG_CATEGORIES: PlaceholderCategory[] = [
  "contract",
  "client",
  "signer",
  "apartment",
  "project",
  "developer",
  "calculation",
  "dates",
]

/** Group catalog entries by category for UI rendering. */
export function groupCatalog(): Record<PlaceholderCategory, CatalogEntry[]> {
  const result = {} as Record<PlaceholderCategory, CatalogEntry[]>
  for (const cat of CATALOG_CATEGORIES) result[cat] = []
  for (const entry of PLACEHOLDER_CATALOG) {
    result[entry.category].push(entry)
  }
  return result
}

/** Lookup helper for toolbar / validation. */
export function findCatalogEntry(key: string): CatalogEntry | undefined {
  return PLACEHOLDER_CATALOG.find((e) => e.key === key)
}
