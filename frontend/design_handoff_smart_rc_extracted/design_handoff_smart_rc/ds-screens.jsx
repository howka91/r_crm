/* Screens: Dashboard, Shaxmatka, Kanban, Clients, Contract, Login */
const { Shell } = window;

// ——— Dashboard ———
function Dashboard() {
  const stats = [
    { l:'Свободно',  v:'127', d:'42% фонда',  c:'var(--success)', ic:'pi-check-circle' },
    { l:'Бронь',     v:'38',  d:'12% · +4 сегодня', c:'var(--warning)', ic:'pi-clock' },
    { l:'Продано',   v:'136', d:'46% фонда', c:'var(--danger)', ic:'pi-ban' },
    { l:'Выручка мес.', v:'₽ 18.4 млрд', d:'+7.2% к марту', c:'var(--primary)', ic:'pi-chart-line' },
  ];
  return (
    <Shell active="dash" crumbs={['Главное','Дашборд']} navExtra={<button className="btn btn-primary btn-sm"><i className="pi pi-plus text-[11px]" /> Новый лид</button>}>
      <div className="flex items-end justify-between mb-5 mt-1 px-1">
        <div>
          <div className="text-[11px] uppercase tracking-[0.12em] mono mb-1.5" style={{ color:'var(--subtle)' }}>Обзор / Апрель 2026</div>
          <h1 className="text-[28px] font-semibold leading-none" style={{ letterSpacing:'-0.025em' }}>ЖК «Янги Махалла»</h1>
          <div className="text-[13px] mt-2" style={{ color:'var(--muted)' }}>3 блока · 14 этажей · 301 квартира · 4 отдела продаж</div>
        </div>
        <div className="flex items-center gap-2">
          <button className="btn btn-ghost btn-sm"><i className="pi pi-calendar text-[11px]" /> Апрель 2026</button>
          <button className="btn btn-ghost btn-sm"><i className="pi pi-download text-[11px]" /> Экспорт</button>
        </div>
      </div>

      <div className="grid grid-cols-4 gap-4 mb-5">
        {stats.map(s => (
          <div key={s.l} className="card p-5">
            <div className="flex items-start justify-between">
              <div className="text-[11px] uppercase tracking-wider mono" style={{ color:'var(--subtle)' }}>{s.l}</div>
              <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: 'oklch(from '+s.c+' 0.96 0.03 h)', color: s.c }}><i className={`pi ${s.ic} text-[13px]`} /></div>
            </div>
            <div className="text-[26px] font-semibold mt-2" style={{ letterSpacing:'-0.025em' }}>{s.v}</div>
            <div className="text-[11.5px] mono mt-1" style={{ color:'var(--muted)' }}>{s.d}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-3 gap-4">
        <div className="card p-5 col-span-2">
          <div className="flex items-center justify-between mb-4">
            <div>
              <div className="text-[11px] uppercase tracking-wider mono" style={{ color:'var(--subtle)' }}>Продажи · последние 6 мес.</div>
              <div className="text-[16px] font-semibold mt-1">Динамика договоров</div>
            </div>
            <div className="flex items-center gap-2">
              <span className="chip chip-primary">Договоры</span>
              <span className="chip chip-ghost">Бронь</span>
            </div>
          </div>
          {/* faux chart */}
          <div className="relative h-[200px] flex items-end gap-3">
            {[
              {a:60,b:30},{a:72,b:36},{a:54,b:40},{a:88,b:48},{a:96,b:38},{a:120,b:52}
            ].map((b,i) => (
              <div key={i} className="flex-1 flex flex-col items-center gap-1.5">
                <div className="w-full flex items-end gap-1 h-[180px]">
                  <div className="flex-1 rounded-t-[6px]" style={{ background: 'linear-gradient(180deg, var(--primary) 0%, oklch(0.62 0.20 295) 100%)', height: b.a * 1.4 }} />
                  <div className="flex-1 rounded-t-[6px]" style={{ background: 'var(--primary-soft)', height: b.b * 1.4 }} />
                </div>
                <div className="text-[10.5px] mono" style={{ color:'var(--subtle)' }}>{['Нояб','Дек','Янв','Фев','Март','Апр'][i]}</div>
              </div>
            ))}
          </div>
        </div>
        <div className="card p-5">
          <div className="text-[11px] uppercase tracking-wider mono mb-1" style={{ color:'var(--subtle)' }}>Недавние договоры</div>
          <div className="text-[16px] font-semibold mb-4">Последние 5</div>
          <div className="space-y-3">
            {[
              { id:'YM-2026-0421', n:'Каримов Р.А.', s:'paid', t:'7 мин' },
              { id:'YM-2026-0420', n:'Исламова С.К.', s:'booked', t:'52 мин' },
              { id:'YM-2026-0418', n:'Жалилов Б.У.', s:'overdue', t:'3 ч' },
              { id:'YM-2026-0415', n:'Назарова Д.А.', s:'paid', t:'вчера' },
              { id:'YM-2026-0412', n:'Ахмедов Т.И.', s:'booked', t:'вчера' },
            ].map(c => (
              <div key={c.id} className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-full flex items-center justify-center text-[11px] font-semibold" style={{ background: 'var(--primary-soft)', color: 'var(--primary)' }}>{c.n.split(' ')[0][0]}{c.n.split(' ')[1]?.[0]}</div>
                <div className="min-w-0 flex-1">
                  <div className="text-[13px] font-medium truncate">{c.n}</div>
                  <div className="text-[11px] mono truncate" style={{ color:'var(--subtle)' }}>{c.id}</div>
                </div>
                {c.s==='paid' && <span className="chip chip-success">Оплачен</span>}
                {c.s==='booked' && <span className="chip chip-warn">Бронь</span>}
                {c.s==='overdue' && <span className="chip chip-danger">Просрочка</span>}
                <span className="text-[11px] mono" style={{ color:'var(--subtle)' }}>{c.t}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </Shell>
  );
}

// ——— Shaxmatka ———
function Shaxmatka() {
  const floors = 14;
  const aptsPerFloor = 8;
  const statusDist = ['free','free','sold','booked','free','sold','free','action','free','booked','sold','free','sold','free','free','action'];
  const cell = (i) => {
    const s = statusDist[i % statusDist.length];
    const map = {
      free:   { bg:'oklch(0.96 0.04 155)', fg:'oklch(0.38 0.12 155)', br:'oklch(0.88 0.08 155)' },
      booked: { bg:'oklch(0.97 0.05 75)',  fg:'oklch(0.44 0.13 75)',  br:'oklch(0.88 0.08 75)'  },
      sold:   { bg:'oklch(0.97 0.03 22)',  fg:'oklch(0.52 0.18 22)',  br:'oklch(0.88 0.08 22)'  },
      action: { bg:'oklch(0.96 0.05 225)', fg:'oklch(0.42 0.12 225)', br:'oklch(0.86 0.08 225)' },
    }[s];
    return map;
  };
  return (
    <Shell active="shax" crumbs={['Объекты','Шахматка','Блок A']} navExtra={<button className="btn btn-primary btn-sm"><i className="pi pi-file-plus text-[11px]" /> Оформить договор</button>}>
      <div className="flex items-end justify-between mb-4 mt-1 px-1">
        <div>
          <div className="text-[11px] uppercase tracking-[0.12em] mono mb-1.5" style={{ color:'var(--subtle)' }}>ЖК Янги Махалла / Блок A</div>
          <h1 className="text-[28px] font-semibold leading-none" style={{ letterSpacing:'-0.025em' }}>Шахматка</h1>
        </div>
        <div className="flex items-center gap-2">
          <div className="card flex items-center gap-1 p-1">
            <button className="btn btn-soft btn-xs">Блок A</button>
            <button className="btn btn-ghost btn-xs">Блок B</button>
            <button className="btn btn-ghost btn-xs">Блок C</button>
          </div>
          <button className="btn btn-ghost btn-sm"><i className="pi pi-filter text-[10px]" /> Фильтр</button>
          <button className="btn btn-ghost btn-sm"><i className="pi pi-download text-[10px]" /> PDF</button>
        </div>
      </div>

      {/* Legend */}
      <div className="card p-3 mb-4 flex items-center gap-5">
        {[
          { l:'Свободно', c:'oklch(0.64 0.14 155)', n:127 },
          { l:'Бронь',    c:'oklch(0.74 0.15 75)',  n:38 },
          { l:'Продано',  c:'oklch(0.58 0.19 22)',  n:136 },
          { l:'Акция',    c:'oklch(0.68 0.13 225)', n:12 },
        ].map(x => (
          <div key={x.l} className="flex items-center gap-2 text-[12.5px]">
            <span className="w-3 h-3 rounded" style={{ background: x.c }} />
            <span className="font-medium">{x.l}</span>
            <span className="mono" style={{ color: 'var(--subtle)' }}>{x.n}</span>
          </div>
        ))}
        <div className="flex-1" />
        <span className="text-[11.5px] mono" style={{ color: 'var(--subtle)' }}>↕ Этажи · ↔ Секции</span>
      </div>

      {/* Grid */}
      <div className="card p-5 overflow-auto art-scroll">
        <div className="flex">
          {/* Floor labels */}
          <div className="flex flex-col-reverse gap-1.5 mr-3 pt-[2px]">
            {Array.from({length:floors}).map((_,i) => (
              <div key={i} className="h-[40px] flex items-center justify-end w-10 mono text-[11px]" style={{ color: 'var(--subtle)' }}>эт. {i+1}</div>
            ))}
          </div>
          {/* Cells */}
          <div className="flex-1 flex flex-col-reverse gap-1.5">
            {Array.from({length:floors}).map((_,fi) => (
              <div key={fi} className="flex gap-1.5">
                {Array.from({length:aptsPerFloor}).map((_,ai) => {
                  const c = cell(fi*aptsPerFloor + ai);
                  const rooms = [1,2,3,2,3,1,2,3][ai];
                  return (
                    <div key={ai} className="flex-1 h-[40px] rounded-[7px] px-2 py-1 flex items-center justify-between cursor-pointer hover:scale-[1.03] transition-transform" style={{ background: c.bg, border: '1px solid ' + c.br, color: c.fg }}>
                      <div className="text-[10.5px] font-semibold mono">{fi+1}{String(ai+1).padStart(2,'0')}</div>
                      <div className="text-[9.5px] mono opacity-80">{rooms}к</div>
                    </div>
                  );
                })}
              </div>
            ))}
            <div className="flex gap-1.5 pt-2">
              {Array.from({length:aptsPerFloor}).map((_,i) => (
                <div key={i} className="flex-1 text-center text-[10.5px] mono" style={{ color: 'var(--subtle)' }}>секц. {i+1}</div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </Shell>
  );
}

// ——— Kanban ———
function Kanban() {
  const cols = [
    { t:'Новые лиды', n:18, c:'var(--info)', cards: [
      { n:'Абдуллаев М.', s:'Сайт · форма', p:'2к · 65 м²', t:'5 мин' },
      { n:'Исломова Д.',  s:'Instagram',    p:'3к · 90 м²', t:'18 мин' },
      { n:'Якубов Т.',    s:'Входящий звонок', p:'1к · 42 м²', t:'1 ч' },
    ]},
    { t:'Квалификация', n:12, c:'var(--primary)', cards: [
      { n:'Каримов Р.',   s:'WhatsApp',     p:'2к · 64 м²', t:'2 ч' },
      { n:'Султанова Л.', s:'Реферал',      p:'3к · 94 м²', t:'вчера' },
    ]},
    { t:'Презентация', n:9, c:'var(--warning)', cards: [
      { n:'Жалилов Б.',   s:'Офис',         p:'4к · 118 м²', t:'2 дня' },
      { n:'Назарова Д.',  s:'Офис',         p:'2к · 72 м²', t:'3 дня' },
    ]},
    { t:'Договор', n:7, c:'var(--success)', cards: [
      { n:'Ахмедов Т.',   s:'Бронь',        p:'3к · 94 м²', t:'сегодня' },
      { n:'Исмаилов А.',  s:'Готов подписать', p:'2к · 64 м²', t:'сегодня' },
    ]},
    { t:'Закрыт', n:4, c:'var(--subtle)', cards: [
      { n:'Тошматов А.',  s:'Не подошло',   p:'—', t:'вчера' },
    ]},
  ];
  return (
    <Shell active="kanban" crumbs={['Продажи','Канбан лидов']} navExtra={<button className="btn btn-primary btn-sm"><i className="pi pi-plus text-[11px]" /> Новый лид</button>}>
      <div className="flex items-end justify-between mb-4 mt-1 px-1">
        <div>
          <div className="text-[11px] uppercase tracking-[0.12em] mono mb-1.5" style={{ color:'var(--subtle)' }}>Продажи / воронка</div>
          <h1 className="text-[28px] font-semibold leading-none" style={{ letterSpacing:'-0.025em' }}>Канбан лидов</h1>
        </div>
        <div className="flex items-center gap-2">
          <button className="btn btn-ghost btn-sm"><i className="pi pi-users text-[10px]" /> Все менеджеры</button>
          <button className="btn btn-ghost btn-sm"><i className="pi pi-filter text-[10px]" /> Фильтр</button>
        </div>
      </div>

      <div className="flex gap-4 pb-2" style={{ minWidth: 0 }}>
        {cols.map(col => (
          <div key={col.t} className="flex-1 min-w-[220px]">
            <div className="flex items-center gap-2 mb-3 px-1">
              <span className="w-2 h-2 rounded-full" style={{ background: col.c }} />
              <div className="text-[13px] font-semibold">{col.t}</div>
              <div className="text-[11px] mono" style={{ color: 'var(--subtle)' }}>{col.n}</div>
              <div className="flex-1" />
              <button className="btn btn-ghost btn-xs" style={{padding:'3px 5px'}}><i className="pi pi-plus text-[9px]" /></button>
            </div>
            <div className="space-y-2.5">
              {col.cards.map((c,i) => (
                <div key={i} className="card card-hover p-3.5 cursor-pointer">
                  <div className="flex items-center gap-2 mb-1.5">
                    <div className="w-7 h-7 rounded-full flex items-center justify-center text-[10.5px] font-semibold" style={{ background: 'var(--primary-soft)', color:'var(--primary)' }}>{c.n.split(' ').map(x=>x[0]).join('')}</div>
                    <div className="text-[13px] font-medium truncate">{c.n}</div>
                  </div>
                  <div className="text-[11.5px] mb-2" style={{ color:'var(--muted)' }}>{c.s}</div>
                  <div className="flex items-center justify-between">
                    <span className="chip mono" style={{ padding: '2px 7px', fontSize: 10.5 }}>{c.p}</span>
                    <span className="text-[10.5px] mono" style={{ color:'var(--subtle)' }}>{c.t}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </Shell>
  );
}

// ——— Clients ———
function Clients() {
  const rows = [
    { n:'Каримов Рустам А.', p:'+998 90 123 45 67', obj:'A · 7 · 74', s:'active',  m:'Султонова Л.', last:'7 мин' },
    { n:'Исламова Севара К.', p:'+998 91 224 10 22', obj:'B · 3 · 32', s:'booked',  m:'Тошматов А.',  last:'1 ч' },
    { n:'Жалилов Бекзод У.', p:'+998 93 551 98 04', obj:'A · 12 · 128', s:'overdue', m:'Султонова Л.', last:'3 ч' },
    { n:'Назарова Диана А.', p:'+998 97 800 10 10', obj:'C · 5 · 57', s:'active',  m:'Тошматов А.',  last:'вчера' },
    { n:'Ахмедов Тимур И.',  p:'+998 99 776 00 11', obj:'—',          s:'lead',    m:'Султонова Л.', last:'сегодня' },
    { n:'Тошматова Мунира С.',p:'+998 90 445 12 12', obj:'B · 8 · 81', s:'active',  m:'Тошматов А.',  last:'2 ч' },
    { n:'Рахимов Анвар К.',  p:'+998 93 020 30 40', obj:'—',          s:'lead',    m:'Султонова Л.', last:'вчера' },
  ];
  const pill = (s) => {
    if (s==='active') return <span className="chip chip-success">Действует</span>;
    if (s==='booked') return <span className="chip chip-warn">Бронь</span>;
    if (s==='overdue') return <span className="chip chip-danger">Просрочка</span>;
    return <span className="chip chip-info">Лид</span>;
  };
  return (
    <Shell active="clients" crumbs={['Продажи','Клиенты']} navExtra={<button className="btn btn-primary btn-sm"><i className="pi pi-user-plus text-[11px]" /> Новый клиент</button>}>
      <div className="flex items-end justify-between mb-5 mt-1 px-1">
        <div>
          <div className="text-[11px] uppercase tracking-[0.12em] mono mb-1.5" style={{ color:'var(--subtle)' }}>Продажи / База клиентов</div>
          <h1 className="text-[28px] font-semibold leading-none" style={{ letterSpacing:'-0.025em' }}>Клиенты</h1>
          <div className="text-[13px] mt-2" style={{ color:'var(--muted)' }}>284 записи · 46 лидов · 218 активных договоров</div>
        </div>
        <div className="flex items-center gap-2">
          <button className="btn btn-ghost btn-sm"><i className="pi pi-download text-[11px]" /> Экспорт</button>
        </div>
      </div>

      {/* Filters */}
      <div className="card p-4 mb-4 flex items-center gap-3 flex-wrap">
        <div className="relative flex-1 min-w-[260px]">
          <i className="pi pi-search absolute left-3 top-1/2 -translate-y-1/2 text-[12px]" style={{ color:'var(--subtle)' }} />
          <input className="inp" style={{ paddingLeft: 34 }} placeholder="Имя, телефон, паспорт, № договора…" />
        </div>
        <select className="inp inp-sm" style={{ width: 160 }}><option>Все менеджеры</option></select>
        <select className="inp inp-sm" style={{ width: 160 }}><option>Все блоки</option></select>
        <span className="chip chip-primary">Статус: Действует ×</span>
        <span className="chip">1-3 комн. ×</span>
        <button className="btn btn-ghost btn-sm">Сбросить</button>
      </div>

      <div className="card overflow-hidden">
        <table className="tbl">
          <thead>
            <tr>
              <th style={{width:28}}><input type="checkbox" /></th>
              <th>Клиент</th>
              <th>Телефон</th>
              <th>Квартира</th>
              <th>Статус</th>
              <th>Менеджер</th>
              <th>Активность</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {rows.map(r => (
              <tr key={r.n}>
                <td><input type="checkbox" /></td>
                <td>
                  <div className="flex items-center gap-2.5">
                    <div className="w-8 h-8 rounded-full flex items-center justify-center text-[11px] font-semibold shrink-0" style={{ background: 'var(--primary-soft)', color: 'var(--primary)' }}>{r.n.split(' ').slice(0,2).map(x=>x[0]).join('')}</div>
                    <div style={{ fontWeight: 500 }}>{r.n}</div>
                  </div>
                </td>
                <td className="mono text-[12.5px]" style={{ color:'var(--muted)' }}>{r.p}</td>
                <td className="mono text-[12.5px]">{r.obj}</td>
                <td>{pill(r.s)}</td>
                <td style={{ color: 'var(--muted)' }}>{r.m}</td>
                <td style={{ color: 'var(--muted)' }}>{r.last}</td>
                <td className="text-right"><button className="btn btn-ghost btn-sm"><i className="pi pi-ellipsis-h text-[10px]" /></button></td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="flex items-center justify-between px-5 py-3" style={{ borderTop: '1px solid var(--line-soft)' }}>
          <span className="text-[12px] mono" style={{ color:'var(--subtle)' }}>Показаны 1–7 из 284</span>
          <div className="flex items-center gap-1">
            <button className="btn btn-ghost btn-xs"><i className="pi pi-angle-left text-[10px]" /></button>
            <button className="btn btn-soft btn-xs mono">1</button>
            <button className="btn btn-ghost btn-xs mono">2</button>
            <button className="btn btn-ghost btn-xs mono">3</button>
            <button className="btn btn-ghost btn-xs mono">…</button>
            <button className="btn btn-ghost btn-xs mono">41</button>
            <button className="btn btn-ghost btn-xs"><i className="pi pi-angle-right text-[10px]" /></button>
          </div>
        </div>
      </div>
    </Shell>
  );
}

// ——— Contract (form wizard) ———
function Contract() {
  const steps = ['Клиент','Квартира','Оплата','Документы','Подписание'];
  const active = 2;
  return (
    <Shell active="unsigned" crumbs={['Договоры','Неподписанные','Новый договор']} navExtra={<><button className="btn btn-ghost btn-sm">Сохранить черновик</button><button className="btn btn-primary btn-sm"><i className="pi pi-check text-[11px]" /> К подписанию</button></>}>
      <div className="flex items-end justify-between mb-5 mt-1 px-1">
        <div>
          <div className="text-[11px] uppercase tracking-[0.12em] mono mb-1.5" style={{ color:'var(--subtle)' }}>Новый договор · черновик · YM-2026-0422</div>
          <h1 className="text-[28px] font-semibold leading-none" style={{ letterSpacing:'-0.025em' }}>Каримов Рустам · Блок A · 7 · 74</h1>
        </div>
      </div>

      {/* Wizard */}
      <div className="card p-4 mb-4 flex items-center gap-2">
        {steps.map((s,i) => (
          <React.Fragment key={s}>
            <div className="flex items-center gap-2">
              <div className={`w-7 h-7 rounded-full flex items-center justify-center text-[11px] font-semibold ${i<=active?'text-white':''}`} style={{ background: i<active ? 'var(--success)' : i===active ? 'var(--primary)' : 'var(--sunken)', color: i>active ? 'var(--subtle)' : undefined, border: i>active ? '1px solid var(--line)' : 'none' }}>
                {i<active ? <i className="pi pi-check text-[10px]" /> : i+1}
              </div>
              <div className={`text-[13px] ${i===active ? 'font-semibold' : ''}`} style={{ color: i<=active ? 'var(--text)' : 'var(--subtle)' }}>{s}</div>
            </div>
            {i<steps.length-1 && <div className="flex-1 h-px" style={{ background: i<active ? 'var(--success)' : 'var(--line)' }} />}
          </React.Fragment>
        ))}
      </div>

      <div className="grid grid-cols-3 gap-4">
        {/* Form */}
        <div className="card p-6 col-span-2">
          <div className="text-[11px] uppercase tracking-wider mono mb-4" style={{ color:'var(--subtle)' }}>Оплата · шаг 3 из 5</div>

          <div className="grid grid-cols-2 gap-4 mb-5">
            <div>
              <label className="block text-[12px] font-medium mb-1.5">Тип оплаты</label>
              <select className="inp" defaultValue="inst"><option value="inst">Рассрочка</option><option>100% предоплата</option><option>Ипотека</option></select>
            </div>
            <div>
              <label className="block text-[12px] font-medium mb-1.5">Валюта</label>
              <select className="inp" defaultValue="uzs"><option value="uzs">UZS</option><option>USD</option></select>
            </div>
            <div>
              <label className="block text-[12px] font-medium mb-1.5">Цена квартиры</label>
              <input className="inp mono" defaultValue="845 000 000" />
            </div>
            <div>
              <label className="block text-[12px] font-medium mb-1.5">Скидка</label>
              <input className="inp mono" defaultValue="15 000 000" />
            </div>
            <div>
              <label className="block text-[12px] font-medium mb-1.5">Первый взнос</label>
              <div className="relative">
                <input className="inp mono" defaultValue="250 000 000" />
                <span className="absolute right-3 top-1/2 -translate-y-1/2 text-[11px] mono" style={{ color:'var(--subtle)' }}>30%</span>
              </div>
            </div>
            <div>
              <label className="block text-[12px] font-medium mb-1.5">Срок, мес.</label>
              <input className="inp mono" defaultValue="24" />
            </div>
          </div>

          <div className="text-[11px] uppercase tracking-wider mono mb-3" style={{ color:'var(--subtle)' }}>График платежей</div>
          <div className="rounded-[10px] overflow-hidden" style={{ border: '1px solid var(--line)' }}>
            <table className="tbl" style={{ fontSize: 12.5 }}>
              <thead><tr><th>№</th><th>Дата</th><th>Сумма</th><th>Статус</th></tr></thead>
              <tbody>
                {[
                  { n:1, d:'25.04.2026', s:'250 000 000', st:'first' },
                  { n:2, d:'25.05.2026', s:' 24 166 667', st:'pending' },
                  { n:3, d:'25.06.2026', s:' 24 166 667', st:'pending' },
                  { n:4, d:'25.07.2026', s:' 24 166 667', st:'pending' },
                  { n:5, d:'…',          s:'…',            st:'dots' },
                ].map(x => (
                  <tr key={x.n}>
                    <td className="mono" style={{ color: 'var(--subtle)' }}>{String(x.n).padStart(2,'0')}</td>
                    <td className="mono">{x.d}</td>
                    <td className="mono" style={{ fontWeight: 500 }}>{x.s}</td>
                    <td>{x.st==='first' ? <span className="chip chip-primary">Первый взнос</span> : x.st==='pending' ? <span className="chip">Ожидает</span> : ''}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Summary */}
        <div className="card p-6 h-fit" style={{ background: 'linear-gradient(180deg, oklch(0.98 0.015 285) 0%, var(--surface) 60%)' }}>
          <div className="text-[11px] uppercase tracking-wider mono mb-1" style={{ color:'var(--subtle)' }}>Итого по договору</div>
          <div className="text-[28px] font-semibold mono" style={{ letterSpacing:'-0.02em' }}>830 000 000 <span className="text-[12px] opacity-60">UZS</span></div>
          <div className="text-[12.5px] mt-1" style={{ color:'var(--muted)' }}>после скидки 15 000 000</div>

          <div className="my-5 h-px" style={{ background: 'var(--line)' }} />

          <div className="space-y-2.5 text-[13px]">
            {[
              ['Квартира', 'A · 7 · 74 · 64.5 м²'],
              ['Цена / м²', '13 100 000 UZS'],
              ['Первый взнос', '30% · 250 000 000'],
              ['Срок', '24 мес.'],
              ['Месячный платёж', '24 166 667 UZS'],
              ['Менеджер', 'Султонова Л.'],
            ].map(([k,v]) => (
              <div key={k} className="flex justify-between gap-4">
                <span style={{ color: 'var(--muted)' }}>{k}</span>
                <span className="mono" style={{ fontWeight: 500 }}>{v}</span>
              </div>
            ))}
          </div>

          <div className="my-5 h-px" style={{ background: 'var(--line)' }} />

          <div className="flex gap-2">
            <button className="btn btn-ghost btn-sm flex-1 justify-center">Назад</button>
            <button className="btn btn-primary btn-sm flex-1 justify-center">Далее →</button>
          </div>
        </div>
      </div>
    </Shell>
  );
}

// ——— Login ———
function Login() {
  return (
    <div className="w-full h-full flex" style={{ background: 'var(--bg)' }}>
      {/* Left brand */}
      <div className="hidden lg:block flex-[2] relative overflow-hidden" style={{ background: 'linear-gradient(135deg, oklch(0.28 0.08 155) 0%, oklch(0.20 0.06 155) 100%)' }}>
        <div className="absolute inset-0" style={{
          backgroundImage: 'radial-gradient(circle at 20% 20%, oklch(0.45 0.12 155 / .55), transparent 50%), radial-gradient(circle at 85% 75%, oklch(0.72 0.18 130 / .18), transparent 55%)'
        }} />
        {/* Ghost shaxmatka */}
        <div className="absolute inset-0 flex items-center justify-center opacity-30">
          <div className="grid grid-cols-8 gap-2 rotate-[-10deg]" style={{ width: '90%' }}>
            {Array.from({ length: 96 }).map((_,i) => {
              const s = ['free','booked','sold','free','action','free','sold','booked'][i%8];
              const c = { free:'oklch(0.64 0.14 155 / .5)', booked:'oklch(0.74 0.15 75 / .5)', sold:'oklch(0.58 0.19 22 / .5)', action:'oklch(0.68 0.13 225 / .5)' }[s];
              return <div key={i} className="h-6 rounded-[4px]" style={{ background: c }} />;
            })}
          </div>
        </div>

        <div className="relative h-full flex flex-col justify-between p-12 text-white">
          <div className="flex items-center gap-2.5">
            <div className="w-10 h-10 rounded-[11px] flex items-center justify-center text-[14px] font-bold" style={{ background: 'var(--primary-accent)', color: 'oklch(0.22 0.08 155)', letterSpacing: '-0.06em' }}>YM</div>
            <div>
              <div className="text-[16px] font-semibold" style={{ letterSpacing: '-0.015em' }}>Yangi Mahalla</div>
              <div className="text-[11px] mono opacity-70">Smart RC · 6.4</div>
            </div>
          </div>

          <div>
            <div className="text-[11px] uppercase tracking-[0.2em] mono opacity-70 mb-4">CRM · Real estate</div>
            <div className="text-[40px] font-semibold leading-[1.05] mb-4" style={{ letterSpacing:'-0.03em' }}>
              Управляйте продажами<br/>ЖК в одном окне.
            </div>
            <div className="text-[14px] opacity-75 max-w-md">Шахматка, клиенты, договоры, финансы, отчёты — от первого лида до подписанного ДДУ без переключений.</div>
          </div>

          <div className="flex items-center gap-5 text-[12px] mono opacity-60">
            <span>© 2026 Yangi Mahalla</span>
            <span className="ml-auto">v 6.4</span>
          </div>
        </div>
      </div>

      {/* Right form */}
      <div className="flex-1 flex items-center justify-center p-10">
        <div className="w-full max-w-[380px]">
          <div className="flex items-center gap-2.5 mb-10 lg:hidden">
            <div className="w-9 h-9 rounded-[10px] flex items-center justify-center text-[14px] font-bold" style={{ background: 'var(--primary)', color: 'var(--primary-accent)', letterSpacing: '-0.06em' }}>YM</div>
            <div className="text-[15px] font-semibold">Yangi Mahalla</div>
          </div>

          <div className="text-[11px] uppercase tracking-[0.14em] mono mb-2" style={{ color: 'var(--subtle)' }}>Авторизация</div>
          <h1 className="text-[30px] font-semibold leading-tight mb-2" style={{ letterSpacing:'-0.025em' }}>С возвращением</h1>
          <div className="text-[14px] mb-8" style={{ color: 'var(--muted)' }}>Введите корпоративные логин и пароль.</div>

          <form className="space-y-4">
            <div>
              <label className="block text-[12px] font-medium mb-1.5">Логин</label>
              <input className="inp" defaultValue="d.karimova" />
            </div>
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="block text-[12px] font-medium">Пароль</label>
                <a className="text-[12px]" style={{ color:'var(--primary)' }}>Забыли?</a>
              </div>
              <div className="relative">
                <input className="inp" type="password" defaultValue="••••••••••" />
                <i className="pi pi-eye absolute right-3 top-1/2 -translate-y-1/2 text-[12px]" style={{ color:'var(--subtle)' }} />
              </div>
            </div>
            <label className="flex items-center gap-2 text-[13px]" style={{ color: 'var(--muted)' }}>
              <input type="checkbox" /> Запомнить меня
            </label>
            <button className="btn btn-primary w-full justify-center" style={{ padding: '11px 14px' }}>Войти →</button>
          </form>

          <div className="mt-10 flex items-center gap-2 text-[12px] mono" style={{ color:'var(--subtle)' }}>
            <span>Язык:</span>
            <span className="chip chip-primary">RU</span>
            <span className="chip chip-ghost">UZ</span>
          </div>
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { Dashboard, Shaxmatka, Kanban, Clients, Contract, Login });
