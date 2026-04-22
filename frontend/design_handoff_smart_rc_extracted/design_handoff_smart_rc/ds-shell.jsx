/* Shared app shell — sidebar + floating navbar */

const NAV = {
  'Главное': [
    { i:'pi-th-large', l:'Дашборд', k:'dash' },
    { i:'pi-building', l:'Объекты / Шахматка', k:'shax' },
  ],
  'Продажи': [
    { i:'pi-user', l:'Клиенты', k:'clients' },
    { i:'pi-compass', l:'Канбан лидов', k:'kanban' },
    { i:'pi-box', l:'Презентация', k:'demo' },
  ],
  'Договоры': [
    { i:'pi-file', l:'Неподписанные', k:'unsigned' },
    { i:'pi-file-edit', l:'Подписанные', k:'signed' },
    { i:'pi-history', l:'Запросы правок' },
  ],
  'Финансы': [
    { i:'pi-chart-line', l:'Платежи' },
    { i:'pi-chart-bar', l:'Графики' },
  ],
  'Справочники': [
    { i:'pi-inbox', l:'Отделы продаж' },
    { i:'pi-wrench', l:'Застройщики' },
    { i:'pi-clipboard', l:'Шаблоны договоров' },
  ],
  'SMS · Отчёты · Админ.': [
    { i:'pi-envelope', l:'SMS шаблоны' },
    { i:'pi-send', l:'Отправка SMS' },
    { i:'pi-file-pdf', l:'Отчёты' },
    { i:'pi-cog', l:'Пользователи и права' },
  ],
};

function Sidebar({ active }) {
  return (
    <aside className="shrink-0 flex flex-col" style={{ width: 252, background: 'var(--surface)', borderRight: '1px solid var(--line)' }}>
      <div className="h-16 flex items-center gap-2.5 px-5" style={{ borderBottom: '1px solid var(--line)' }}>
        <div className="w-9 h-9 rounded-[10px] flex items-center justify-center text-[14px] font-bold relative overflow-hidden" style={{ background: 'var(--primary)', color: 'var(--primary-accent)', boxShadow: '0 6px 18px -4px oklch(0.38 0.10 155 / .5)', fontFamily: 'Inter Tight' }}>
          <span style={{ letterSpacing: '-0.08em' }}>YM</span>
        </div>
        <div className="leading-tight">
          <div className="text-[14.5px] font-semibold" style={{ letterSpacing: '-0.015em' }}>Yangi Mahalla</div>
          <div className="text-[10.5px] mono" style={{ color: 'var(--subtle)' }}>Smart RC · 6.4</div>
        </div>
      </div>
      <nav className="p-3 flex-1 overflow-auto art-scroll">
        {Object.entries(NAV).map(([h, items]) => (
          <div key={h} className="mb-1">
            <div className="nav-header">{h}</div>
            {items.map(it => (
              <a key={it.l} className={`nav-item ${it.k === active ? 'active' : ''}`}>
                <i className={`pi ${it.i} text-[13px]`} style={{ width: 14 }} />
                <span className="truncate">{it.l}</span>
              </a>
            ))}
          </div>
        ))}
      </nav>
      <div className="p-3 m-3 rounded-[12px] flex items-center gap-2.5" style={{ background: 'var(--sunken)', border: '1px solid var(--line-soft)' }}>
        <div className="w-9 h-9 rounded-full flex items-center justify-center text-[12px] font-semibold shrink-0" style={{ background: 'var(--primary)', color: 'var(--primary-accent)' }}>ДК</div>
        <div className="min-w-0 flex-1">
          <div className="text-[12.5px] font-medium truncate">Диана Каримова</div>
          <div className="text-[10.5px] mono truncate" style={{ color: 'var(--subtle)' }}>super_manager</div>
        </div>
        <i className="pi pi-sign-out text-[12px]" style={{ color: 'var(--subtle)' }} />
      </div>
    </aside>
  );
}

function Navbar({ crumbs = [], children }) {
  return (
    <header className="mx-6 mt-5 mb-2 h-14 flex items-center gap-4 px-5 rounded-[14px]" style={{ background: 'var(--surface)', border: '1px solid var(--line)', boxShadow: '0 6px 22px -10px rgba(20,20,50,.1)' }}>
      <nav className="flex items-center gap-2 text-[13px]" style={{ color: 'var(--muted)' }}>
        {crumbs.map((c, i) => (
          <React.Fragment key={i}>
            {i > 0 && <i className="pi pi-angle-right text-[10px]" style={{ color: 'var(--subtle)' }} />}
            <span style={i === crumbs.length - 1 ? { color: 'var(--text)', fontWeight: 500 } : {}}>{c}</span>
          </React.Fragment>
        ))}
      </nav>
      <div className="flex-1" />
      <div className="relative">
        <i className="pi pi-search absolute left-3 top-1/2 -translate-y-1/2 text-[12px]" style={{ color:'var(--subtle)' }} />
        <input className="inp inp-sm" style={{ width: 280, paddingLeft: 32 }} placeholder="Поиск клиентов, квартир, договоров…" />
        <span className="absolute right-2.5 top-1/2 -translate-y-1/2 mono text-[10px] px-1.5 py-0.5 rounded" style={{ background: 'var(--sunken)', color: 'var(--subtle)', border: '1px solid var(--line)' }}>⌘ K</span>
      </div>
      {children}
      <button className="btn btn-ghost btn-icon"><i className="pi pi-bell text-[13px]" /></button>
      <button className="btn btn-ghost btn-sm mono" style={{ padding: '5px 8px' }}>RU</button>
    </header>
  );
}

function Shell({ active, crumbs, children, navExtra }) {
  return (
    <div className="w-full h-full flex" style={{ background: 'var(--bg)' }}>
      <Sidebar active={active} />
      <div className="flex-1 flex flex-col min-w-0">
        <Navbar crumbs={crumbs}>{navExtra}</Navbar>
        <div className="flex-1 overflow-auto art-scroll px-6 pb-6 pt-2">
          {children}
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { Shell, Sidebar, Navbar });
