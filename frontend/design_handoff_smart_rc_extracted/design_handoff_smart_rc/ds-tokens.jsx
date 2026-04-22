/* Tokens + Components showcase — Smart RC modernized */

function Swatch({ name, value, note }) {
  return (
    <div className="flex items-center gap-3">
      <div className="w-11 h-11 rounded-[10px] shrink-0" style={{ background: value, border: '1px solid rgba(0,0,0,.06)' }} />
      <div className="min-w-0">
        <div className="text-[12.5px] font-medium leading-tight">{name}</div>
        <div className="text-[11px] mono opacity-60 truncate">{note || value}</div>
      </div>
    </div>
  );
}

function TypeRow({ label, size, weight, tracking, sample = "Smart RC · Yangi Mahalla — объекты, клиенты, продажи · 0123" }) {
  return (
    <div className="flex items-baseline gap-6 py-3 border-b last:border-b-0" style={{ borderColor: 'var(--line-soft)' }}>
      <div className="w-32 shrink-0 text-[11px] uppercase tracking-wider opacity-60 mono">{label}</div>
      <div style={{ fontSize: size, fontWeight: weight, letterSpacing: tracking, lineHeight: 1.15 }} className="flex-1 truncate">{sample}</div>
      <div className="text-[11px] mono opacity-60 shrink-0">{size} · {weight}</div>
    </div>
  );
}

function Tokens() {
  return (
    <div className="w-full h-full overflow-auto art-scroll p-10">
      <div className="max-w-[1220px] mx-auto">
        <div className="flex items-end justify-between mb-8 pb-6 border-b" style={{ borderColor: 'var(--line)' }}>
          <div>
            <div className="text-[11px] uppercase tracking-[0.14em] mono mb-2" style={{ color: 'var(--subtle)' }}>01 · Design Tokens</div>
            <h1 className="text-[34px] font-semibold leading-none" style={{ letterSpacing: '-0.025em' }}>Основа системы</h1>
            <div className="text-[14px] mt-2" style={{ color: 'var(--muted)' }}>Основной цвет — тёмно-зелёный сайдбара Yangi Mahalla (oklch .38 / .10 / 155), с лаймовым акцентом из логотипа. 8-px сетка, Inter Tight.</div>
          </div>
          <div className="flex gap-2">
            <span className="chip chip-primary">YM deep green</span>
            <span className="chip">Inter Tight</span>
            <span className="chip">JetBrains Mono</span>
          </div>
        </div>

        {/* Colors */}
        <div className="mb-10">
          <div className="text-[13px] font-medium mb-4">Цветовая гамма</div>
          <div className="grid grid-cols-4 gap-4">
            <div className="card p-5">
              <div className="text-[11px] mono uppercase mb-3" style={{ color: 'var(--subtle)' }}>Primary · deep green</div>
              <div className="space-y-3">
                <Swatch name="primary" value="oklch(0.38 0.10 155)" note="YM brand · CTA" />
                <Swatch name="primary / hover" value="oklch(0.32 0.10 155)" />
                <Swatch name="primary / soft" value="oklch(0.96 0.035 155)" />
                <Swatch name="accent · lime" value="oklch(0.72 0.18 130)" note="logo accent" />
              </div>
            </div>
            <div className="card p-5">
              <div className="text-[11px] mono uppercase mb-3" style={{ color: 'var(--subtle)' }}>Surface</div>
              <div className="space-y-3">
                <Swatch name="bg" value="oklch(0.985 0.005 285)" />
                <Swatch name="surface" value="#ffffff" />
                <Swatch name="sunken" value="oklch(0.97 0.007 285)" />
              </div>
            </div>
            <div className="card p-5">
              <div className="text-[11px] mono uppercase mb-3" style={{ color: 'var(--subtle)' }}>Text</div>
              <div className="space-y-3">
                <Swatch name="text" value="oklch(0.24 0.02 285)" />
                <Swatch name="muted" value="oklch(0.52 0.018 285)" />
                <Swatch name="subtle" value="oklch(0.70 0.015 285)" />
              </div>
            </div>
            <div className="card p-5">
              <div className="text-[11px] mono uppercase mb-3" style={{ color: 'var(--subtle)' }}>Semantic</div>
              <div className="space-y-3">
                <Swatch name="success" value="oklch(0.64 0.14 155)" note="свободно, оплачено" />
                <Swatch name="warning" value="oklch(0.74 0.15 75)" note="бронь, ожидание" />
                <Swatch name="danger"  value="oklch(0.58 0.19 22)" note="продано, просрочка" />
                <Swatch name="info"    value="oklch(0.68 0.13 225)" note="акция, инфо" />
              </div>
            </div>
          </div>
        </div>

        {/* Type */}
        <div className="mb-10">
          <div className="text-[13px] font-medium mb-4">Типографика</div>
          <div className="card p-6">
            <TypeRow label="Display" size="34px" weight="600" tracking="-0.025em" />
            <TypeRow label="H1"      size="26px" weight="600" tracking="-0.02em" />
            <TypeRow label="H2"      size="20px" weight="600" tracking="-0.015em" />
            <TypeRow label="H3"      size="16px" weight="600" tracking="-0.01em" />
            <TypeRow label="Body"    size="14px" weight="400" tracking="0" />
            <TypeRow label="Small"   size="13px" weight="400" tracking="0" />
            <TypeRow label="Eyebrow" size="11px" weight="500" tracking="0.08em" sample="MY OBJECTS · APARTMENTS · FINANCE · REPORTS" />
          </div>
        </div>

        {/* Spacing · Radius · Elevation */}
        <div className="grid grid-cols-3 gap-5 mb-4">
          <div className="card p-5">
            <div className="text-[13px] font-medium mb-3">Шкала отступов (8-px grid)</div>
            <div className="flex items-end gap-2">
              {[4,8,12,16,24,32,48].map(n => (
                <div key={n} className="flex flex-col items-center gap-1.5">
                  <div style={{ width: 28, height: n, background: 'var(--primary)', borderRadius: 2, opacity: .85 }} />
                  <div className="text-[10px] mono" style={{ color: 'var(--subtle)' }}>{n}</div>
                </div>
              ))}
            </div>
          </div>
          <div className="card p-5">
            <div className="text-[13px] font-medium mb-3">Радиусы</div>
            <div className="flex items-center gap-3">
              {[{n:7,l:'xs'},{n:8,l:'sm'},{n:10,l:'md'},{n:14,l:'lg'},{n:999,l:'full'}].map(r => (
                <div key={r.l} className="flex flex-col items-center gap-1.5">
                  <div style={{ width: 44, height: 44, borderRadius: r.n, background: 'var(--primary-soft)', border: '1px solid var(--line)' }} />
                  <div className="text-[10px] mono" style={{ color: 'var(--subtle)' }}>{r.l}</div>
                </div>
              ))}
            </div>
          </div>
          <div className="card p-5">
            <div className="text-[13px] font-medium mb-3">Возвышенность</div>
            <div className="flex items-center gap-4">
              {[
                { l: 'flat', s: 'none' },
                { l: 'card', s: '0 1px 2px rgba(20,20,50,.04), 0 0 0 1px rgba(20,20,50,.04)' },
                { l: 'float', s: '0 6px 20px -6px rgba(20,20,50,.1), 0 1px 2px rgba(20,20,50,.04)' },
                { l: 'modal', s: '0 22px 48px -10px rgba(20,20,50,.22), 0 2px 6px rgba(20,20,50,.06)' },
              ].map(el => (
                <div key={el.l} className="flex flex-col items-center gap-2">
                  <div style={{ width: 44, height: 44, borderRadius: 10, background: '#fff', boxShadow: el.s, border: '1px solid var(--line-soft)' }} />
                  <div className="text-[10px] mono" style={{ color: 'var(--subtle)' }}>{el.l}</div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Shaxmatka cell legend — product-specific */}
        <div className="card p-6 mt-5">
          <div className="text-[13px] font-medium mb-4">Статусы квартир (шахматка)</div>
          <div className="grid grid-cols-4 gap-4">
            {[
              { k:'free',     l:'Свободно',  bg:'oklch(0.96 0.04 155)', fg:'oklch(0.38 0.12 155)', br:'oklch(0.85 0.1 155)' },
              { k:'booked',   l:'Бронь',     bg:'oklch(0.97 0.05 75)',  fg:'oklch(0.44 0.13 75)',  br:'oklch(0.85 0.1 75)'  },
              { k:'sold',     l:'Продано',   bg:'oklch(0.97 0.03 22)',  fg:'oklch(0.52 0.18 22)',  br:'oklch(0.85 0.1 22)'  },
              { k:'action',   l:'Акция',     bg:'oklch(0.96 0.04 225)', fg:'oklch(0.42 0.12 225)', br:'oklch(0.85 0.08 225)'},
            ].map(s => (
              <div key={s.k} className="flex items-center gap-3 p-3 rounded-[10px]" style={{ background: s.bg, border: '1px solid ' + s.br }}>
                <div className="w-10 h-10 rounded-lg flex items-center justify-center text-[11px] font-semibold" style={{ color: s.fg, background: 'rgba(255,255,255,.6)', border: '1px solid ' + s.br }}>{s.k[0].toUpperCase()}</div>
                <div>
                  <div className="text-[13px] font-medium" style={{ color: s.fg }}>{s.l}</div>
                  <div className="text-[10.5px] mono opacity-70" style={{ color: s.fg }}>status.{s.k}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function Components() {
  return (
    <div className="w-full h-full overflow-auto art-scroll p-10">
      <div className="max-w-[1220px] mx-auto space-y-7">
        <div className="flex items-end justify-between pb-6 border-b" style={{ borderColor: 'var(--line)' }}>
          <div>
            <div className="text-[11px] uppercase tracking-[0.14em] mono mb-2" style={{ color: 'var(--subtle)' }}>02 · Components</div>
            <h1 className="text-[30px] font-semibold leading-none" style={{ letterSpacing: '-0.025em' }}>Атомы интерфейса</h1>
          </div>
        </div>

        <section className="card p-6">
          <div className="text-[11px] uppercase tracking-wider mono mb-4" style={{ color: 'var(--subtle)' }}>Buttons</div>
          <div className="flex flex-wrap items-center gap-3 mb-4">
            <button className="btn btn-primary"><i className="pi pi-plus text-[11px]" /> Новый объект</button>
            <button className="btn btn-primary">Сохранить</button>
            <button className="btn btn-soft"><i className="pi pi-file-edit text-[11px]" /> Редактировать</button>
            <button className="btn btn-ghost">Отмена</button>
            <button className="btn btn-ghost"><i className="pi pi-download text-[11px]" /> Экспорт</button>
            <button className="btn btn-danger"><i className="pi pi-trash text-[11px]" /> Удалить</button>
            <button className="btn btn-primary" disabled style={{ opacity: .5, cursor:'not-allowed' }}>Disabled</button>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <button className="btn btn-primary btn-sm">Применить</button>
            <button className="btn btn-ghost btn-sm">Закрыть</button>
            <button className="btn btn-ghost btn-sm"><i className="pi pi-filter text-[10px]" /> Фильтр</button>
            <button className="btn btn-ghost btn-icon"><i className="pi pi-ellipsis-h text-[11px]" /></button>
            <button className="btn btn-ghost btn-icon"><i className="pi pi-refresh text-[11px]" /></button>
          </div>
        </section>

        <section className="card p-6">
          <div className="text-[11px] uppercase tracking-wider mono mb-4" style={{ color: 'var(--subtle)' }}>Inputs</div>
          <div className="grid grid-cols-3 gap-5">
            <div>
              <label className="block text-[12px] font-medium mb-1.5">ФИО клиента</label>
              <input className="inp" defaultValue="Каримов Рустам Акмалович" />
            </div>
            <div>
              <label className="block text-[12px] font-medium mb-1.5">Телефон</label>
              <input className="inp mono" defaultValue="+998 90 123 45 67" />
            </div>
            <div>
              <label className="block text-[12px] font-medium mb-1.5">Паспорт</label>
              <input className="inp mono" defaultValue="AB 1234567" />
            </div>
            <div>
              <label className="block text-[12px] font-medium mb-1.5">Объект</label>
              <select className="inp" defaultValue="yangi"><option value="yangi">ЖК «Янги Махалла»</option><option>ЖК «Мирзо»</option></select>
            </div>
            <div>
              <label className="block text-[12px] font-medium mb-1.5">Квартира</label>
              <input className="inp mono" defaultValue="Блок A · Этаж 7 · №74" />
            </div>
            <div>
              <label className="block text-[12px] font-medium mb-1.5">Сумма</label>
              <div className="relative">
                <input className="inp mono" defaultValue="845 000 000" />
                <span className="absolute right-3 top-1/2 -translate-y-1/2 text-[11px] mono" style={{ color:'var(--subtle)' }}>UZS</span>
              </div>
            </div>
            <div className="col-span-2">
              <label className="block text-[12px] font-medium mb-1.5">Комментарий</label>
              <textarea className="inp" rows="2" defaultValue="Клиент просит рассрочку на 24 месяца, первый взнос 30%."></textarea>
            </div>
            <div>
              <label className="block text-[12px] font-medium mb-1.5">Дата сделки</label>
              <input className="inp mono" defaultValue="22.04.2026" />
            </div>
          </div>
        </section>

        <section className="card p-6">
          <div className="text-[11px] uppercase tracking-wider mono mb-4" style={{ color: 'var(--subtle)' }}>Chips · Statuses</div>
          <div className="flex flex-wrap gap-2">
            <span className="chip chip-success"><span className="w-1.5 h-1.5 rounded-full" style={{ background: 'var(--success)' }} /> Свободно</span>
            <span className="chip chip-warn"><span className="w-1.5 h-1.5 rounded-full" style={{ background: 'var(--warning)' }} /> Бронь</span>
            <span className="chip chip-danger"><span className="w-1.5 h-1.5 rounded-full" style={{ background: 'var(--danger)' }} /> Продано</span>
            <span className="chip chip-info"><span className="w-1.5 h-1.5 rounded-full" style={{ background: 'var(--info)' }} /> Акция</span>
            <span className="chip chip-primary">Новый лид</span>
            <span className="chip">1-комн.</span>
            <span className="chip">2-комн.</span>
            <span className="chip">3-комн.</span>
            <span className="chip mono">64.5 м²</span>
            <span className="chip mono">14 500 000 UZS/м²</span>
            <span className="chip chip-ghost">Черновик</span>
          </div>
        </section>

        <section className="card overflow-hidden">
          <div className="p-5 pb-4 flex items-center gap-3" style={{ borderBottom: '1px solid var(--line-soft)' }}>
            <div>
              <div className="text-[11px] uppercase tracking-wider mono" style={{ color:'var(--subtle)' }}>Data table</div>
              <div className="text-[14px]" style={{ color: 'var(--muted)' }}>Плотный hover, mono для ID и сумм, chip-based статусы.</div>
            </div>
            <div className="flex-1" />
            <div className="relative">
              <i className="pi pi-search absolute left-3 top-1/2 -translate-y-1/2 text-[11px]" style={{ color:'var(--subtle)' }} />
              <input className="inp inp-sm" style={{ paddingLeft: 30, width: 220 }} placeholder="Поиск…" />
            </div>
            <button className="btn btn-ghost btn-sm"><i className="pi pi-filter text-[10px]" /> Фильтр</button>
          </div>
          <table className="tbl">
            <thead>
              <tr>
                <th style={{ width: 28 }}><input type="checkbox" /></th>
                <th>№ договора</th>
                <th>Клиент</th>
                <th>Квартира</th>
                <th>Сумма</th>
                <th>Статус</th>
                <th>Менеджер</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {[
                { id:'YM-2026-0421', c:'Каримов Р.А.', f:'A · 7 · 74', a:'845 000 000', s:'paid', m:'Султонова Л.' },
                { id:'YM-2026-0420', c:'Исламова С.К.', f:'B · 3 · 32', a:'612 500 000', s:'booked', m:'Тошматов А.' },
                { id:'YM-2026-0418', c:'Жалилов Б.У.',  f:'A · 12 · 128', a:'1 120 000 000', s:'overdue', m:'Султонова Л.' },
                { id:'YM-2026-0415', c:'Назарова Д.А.',  f:'C · 5 · 57', a:'720 000 000', s:'paid', m:'Тошматов А.' },
              ].map(r => (
                <tr key={r.id}>
                  <td><input type="checkbox" /></td>
                  <td className="mono text-[12.5px]" style={{ color: 'var(--primary)' }}>{r.id}</td>
                  <td style={{ fontWeight: 500 }}>{r.c}</td>
                  <td className="mono text-[12.5px]">{r.f}</td>
                  <td className="mono" style={{ fontWeight: 500 }}>{r.a} <span className="text-[11px] opacity-60">UZS</span></td>
                  <td>{r.s==='paid'
                    ? <span className="chip chip-success"><span className="w-1.5 h-1.5 rounded-full" style={{ background:'var(--success)' }} /> Оплачен</span>
                    : r.s==='booked'
                    ? <span className="chip chip-warn"><span className="w-1.5 h-1.5 rounded-full" style={{ background:'var(--warning)' }} /> Бронь</span>
                    : <span className="chip chip-danger"><span className="w-1.5 h-1.5 rounded-full" style={{ background:'var(--danger)' }} /> Просрочка</span>}</td>
                  <td style={{ color: 'var(--muted)' }}>{r.m}</td>
                  <td className="text-right"><button className="btn btn-ghost btn-sm"><i className="pi pi-ellipsis-h text-[10px]" /></button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      </div>
    </div>
  );
}

Object.assign(window, { Tokens, Components });
