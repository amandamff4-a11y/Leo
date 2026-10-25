"""Gera meu-planner.html: a versão do planner que funciona sozinha (sem o Claude),
salvando os dados no navegador. Uso: python3 tools/build-offline.py <pasta-com-dados>"""
import json, os, sys

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(root, 'planejamento-semana.html'), encoding='utf-8').read()
args = sys.argv[1:]
pwa = '--pwa' in args
args = [a for a in args if a != '--pwa']
data_dir = args[0] if args else None

seed = {c: {} for c in ('fixed', 'weeks', 'goals', 'books', 'shows', 'days', 'habits', 'money', 'wishes', 'journal', 'inbox', 'objetivos', 'perfil', 'semestres', 'subjects', 'acad')}
if data_dir:
    for c in seed:
        d = os.path.join(data_dir, c)
        if os.path.isdir(d):
            for f in sorted(os.listdir(d)):
                if f.endswith('.json'):
                    seed[c][f[:-5]] = json.load(open(os.path.join(d, f), encoding='utf-8'))

# Aparece só quando o visualizador não roda JavaScript (ex.: pré-visualização do app Arquivos)
NOJS = '''
  <div id="nojs" style="margin:12px 0;padding:14px 16px;border-radius:14px;background:#fde8ef;color:#6d2a46;border:2px solid #e64980;font-size:18px;line-height:1.35">
    <b>Os botões não funcionam nesta pré-visualização.</b><br>
    Abra o arquivo num navegador: no iPhone, toque em Compartilhar e escolha <b>Abrir no Safari</b> (ou "Abrir com" → Chrome).
    No Android, toque nos três pontinhos e escolha <b>Abrir com Chrome</b>. No computador, clique duas vezes no arquivo.
  </div>'''

head, body = src.split('\n<div class="wrap">', 1)
head = head.replace('<meta name="claude:viewport-fit-sides" content="cover">\n', '')
main_script = body.index('\n<script>')

shim = r'''
<style>
  .backup { margin-top: 28px; padding: 14px 16px; border-radius: 16px; border: 1.5px dashed color-mix(in srgb, var(--title) 40%, transparent); display: flex; flex-wrap: wrap; gap: 10px; align-items: center; color: var(--muted); font-size: 16px; }
  .backup p { margin: 0; flex: 1 1 260px; }
  .paste-bar { display: flex; justify-content: flex-end; margin: -6px 0 12px; }
  .paste-bar .btn { border-color: color-mix(in srgb, var(--title) 45%, transparent); color: var(--title); }
  #pasteText { width: 100%; font: inherit; font-size: 16px; border: 1px solid var(--line); border-radius: 10px; padding: 10px; background: var(--bg); color: var(--ink); resize: vertical; }
</style>
<script>
// Banco de dados local: guarda tudo neste navegador (localStorage), no mesmo formato do app online
(function () {
  const KEY = 'meu-planner-dados';
  const SEED = __SEED__;
  let data = null;
  try { data = JSON.parse(localStorage.getItem(KEY)); } catch {}
  const fresh = !data;
  if (!data) data = JSON.parse(JSON.stringify(SEED));
  const save = () => { try { localStorage.setItem(KEY, JSON.stringify(data)); } catch {} };
  save();
  const subs = {};
  const snap = c => ({ docs: Object.entries(data[c] || {}).map(([id, d]) => ({ id, exists: true, data: () => d })) });
  const fire = c => (subs[c] || []).forEach(f => f(snap(c)));
  const merge = (a, b) => { for (const k in b) a[k] = (b[k] && typeof b[k] === 'object' && !Array.isArray(b[k]) && a[k] && typeof a[k] === 'object') ? merge({ ...a[k] }, b[k]) : b[k]; return a; };
  const copy = o => JSON.parse(JSON.stringify(o));
  const db = {
    collection: c => ({ onSnapshot(f) { (subs[c] = subs[c] || []).push(f); setTimeout(() => f(snap(c))); return () => {}; } }),
    doc(path) {
      const [c, id] = path.split('/');
      return {
        async set(d) { (data[c] = data[c] || {})[id] = copy(d); save(); fire(c); },
        async update(d) { const cur = (data[c] || {})[id]; if (!cur) throw { code: 'invalid_argument' }; data[c][id] = merge({ ...cur }, copy(d)); save(); fire(c); },
        async delete() { if (data[c]) delete data[c][id]; save(); fire(c); }
      };
    }
  };
  window.claude = { use: async name => name === 'db' ? db : null };
  document.getElementById('nojs')?.remove();
  // Mantém abas abertas ao mesmo tempo sincronizadas
  addEventListener('storage', e => { if (e.key !== KEY) return; try { data = JSON.parse(e.newValue) || data; } catch {} Object.keys(subs).forEach(fire); });

  const box = document.createElement('div');
  box.className = 'backup';
  box.innerHTML = '<p>Seus dados ficam salvos neste navegador. Guarde uma cópia de vez em quando, ou use a cópia para levar o planner para outro aparelho.</p>' +
    '<button class="btn" id="bkSave">Baixar cópia dos dados</button><button class="btn" id="bkLoad">Abrir cópia</button><input type="file" id="bkFile" accept="application/json,.json" hidden>';
  document.querySelector('.wrap').appendChild(box);

  // "Colar do Claude": aplica um código que o Claude manda no chat (agenda completa ou alterações)
  const bar = document.createElement('div');
  bar.className = 'paste-bar';
  bar.innerHTML = '<button class="btn" id="pasteOpen">📋 Colar do Claude</button>';
  document.querySelector('.mainnav').after(bar);
  const dlg = document.createElement('dialog');
  dlg.innerHTML = '<form id="pasteForm"><h3>Colar do Claude</h3><p class="form-note">Cole aqui o código que o Claude te mandou no chat e toque em Aplicar.</p>' +
    '<textarea id="pasteText" rows="7" placeholder="Toque e segure aqui, depois escolha Colar"></textarea>' +
    '<div class="actions"><span></span><span><button type="button" class="btn" id="pasteCancel">Cancelar</button><button type="submit" class="btn primary">Aplicar</button></span></div></form>';
  document.body.appendChild(dlg);
  const openPaste = () => { dlg.querySelector('#pasteText').value = ''; dlg.showModal(); };
  document.getElementById('pasteOpen').onclick = openPaste;
  dlg.querySelector('#pasteCancel').onclick = () => dlg.close();
  dlg.querySelector('#pasteForm').onsubmit = e => {
    e.preventDefault();
    try {
      const msg = applyPaste(dlg.querySelector('#pasteText').value);
      save(); Object.keys(subs).forEach(fire); dlg.close();
      document.querySelectorAll('.welcome').forEach(el => el.remove());
      window.celebrate ? celebrate(msg) : alert(msg);
    } catch { alert('Não entendi esse código. Copie de novo a mensagem inteira do Claude e cole aqui.'); }
  };
  const P = iso => { const [y, m, d] = iso.split('-').map(Number); return new Date(y, m - 1, d, 12); };
  const F = d => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
  const weekOf = iso => { const d = P(iso); d.setDate(d.getDate() - d.getDay()); return F(d); };
  const uid = p => p + Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
  const isDate = v => /^\d{4}-\d{2}-\d{2}$/.test(v || '');
  const week = iso => { const w = weekOf(iso); return data.weeks[w] = data.weeks[w] || { start: w, items: [], done: {}, skip: [], notes: {}, lists: { prioridades: [], academicas: [], pessoais: [] } }; };
  const same = (a, b) => String(a || '').trim().toLowerCase() === String(b || '').trim().toLowerCase();
  const pick = (o, keys) => Object.fromEntries(keys.filter(k => o[k] !== undefined).map(k => [k, o[k]]));
  function applyPaste(txt) {
    const a = txt.indexOf('{'), b = txt.lastIndexOf('}');
    if (a < 0 || b < a) throw 0;
    const obj = JSON.parse(txt.slice(a, b + 1));
    ['fixed', 'weeks', 'goals', 'books', 'shows', 'days', 'habits', 'money', 'wishes', 'journal', 'inbox', 'objetivos', 'perfil', 'semestres', 'subjects', 'acad'].forEach(c => data[c] = data[c] || {});
    if (obj.weeks && obj.fixed) {
      data = obj; ['fixed', 'weeks', 'goals', 'books', 'shows', 'days', 'habits', 'money', 'wishes', 'journal', 'inbox', 'objetivos', 'perfil', 'semestres', 'subjects', 'acad'].forEach(c => data[c] = data[c] || {});
      return 'Sua agenda chegou! ♡';
    }
    if (obj.merge && typeof obj.merge === 'object') {
      let m = 0;
      for (const [c, docs] of Object.entries(obj.merge)) { data[c] = data[c] || {}; for (const [id, d] of Object.entries(docs || {})) { data[c][id] = d; m++; } }
      if (!m) throw 0;
      return `Pronto, ${m} itens adicionados! ♡`;
    }
    if (!Array.isArray(obj.planner)) throw 0;
    let n = 0;
    for (const o of obj.planner) {
      const item = { time: o.time || '', text: o.text || 'Atividade', sub: o.sub || '', icon: o.icon || 'coracao', hl: !!o.hl };
      if (o.add === 'atividade' && isDate(o.date)) week(o.date).items.push({ id: uid('w'), date: o.date, ...item });
      else if (o.add === 'fixa' && o.weekday >= 0 && o.weekday <= 6) data.fixed[uid('f')] = { ...item, weekday: +o.weekday };
      else if (o.add === 'livro') data.books[uid('b')] = { status: 'lendo', ...pick(o, ['title', 'author', 'status', 'page', 'pages', 'note']), updated: Date.now() };
      else if (o.add === 'serie' || o.add === 'filme') data.shows[uid('s')] = { kind: o.add, status: 'vendo', ...pick(o, ['title', 'status', 'season', 'episode', 'where', 'rating', 'note']), updated: Date.now() };
      else if (o.add === 'meta' && isDate(o.semana)) {
        const g = data.goals[o.semana] = data.goals[o.semana] || { lists: { prioridades: [], academicas: [], pessoais: [] } };
        (g.lists[o.lista || 'prioridades'] = g.lists[o.lista || 'prioridades'] || []).push({ text: o.text, done: false });
      }
      else if (o.remove === 'atividade' && isDate(o.date)) {
        const w = week(o.date), wd = P(o.date).getDay();
        w.items = w.items.filter(it => !(it.date === o.date && same(it.text, o.text)));
        Object.entries(data.fixed).forEach(([id, f]) => { if (f.weekday === wd && same(f.text, o.text)) w.skip.push(id + '_' + o.date); });
      }
      else if (o.remove === 'fixa') Object.entries(data.fixed).forEach(([id, f]) => { if (f.weekday === +o.weekday && same(f.text, o.text)) delete data.fixed[id]; });
      else if (o.nota && isDate(o.nota)) week(o.nota).notes[o.nota] = o.text || '';
      else continue;
      n++;
    }
    if (!n) throw 0;
    return n === 1 ? 'Pronto, atualizei! ♡' : `Pronto, ${n} atualizações feitas! ♡`;
  }
  // Primeira vez abrindo sem dados: mostra como trazer a agenda de um arquivo de cópia
  if (fresh && !Object.values(data).some(c => Object.keys(c).length)) {
    const hi = document.createElement('div');
    hi.className = 'notice welcome';
    hi.innerHTML = '<b>Bem-vinda ao seu planner! ♡</b><br>Para trazer a sua agenda, copie o código que o Claude te mandou e toque em <b>Colar do Claude</b>. Ou comece do zero adicionando suas atividades.<br><button class="btn primary" style="margin-top:8px" id="pasteOpen2">📋 Colar do Claude</button>';
    bar.after(hi);
    document.getElementById('pasteOpen2').onclick = openPaste;
  }
  document.getElementById('bkSave').onclick = () => {
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' }));
    a.download = 'meu-planner-copia-' + new Date().toISOString().slice(0, 10) + '.json';
    document.body.appendChild(a); a.click(); a.remove();
  };
  const file = document.getElementById('bkFile');
  document.getElementById('bkLoad').onclick = () => file.click();
  file.onchange = async () => {
    try {
      const d = JSON.parse(await file.files[0].text());
      if (!d || typeof d.weeks !== 'object' || typeof d.fixed !== 'object') throw 0;
      data = d; save(); location.reload();
    } catch { alert('Não consegui abrir esse arquivo. Escolha uma cópia baixada pelo próprio planner.'); }
    file.value = '';
  };
})();
</script>'''.replace('__SEED__', json.dumps(seed, ensure_ascii=False))

out = ('<!doctype html>\n<html lang="pt-BR">\n<head>\n<meta charset="utf-8">\n'
       '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
       + head + '\n</head>\n<body>\n<div class="wrap">' + NOJS + body[:main_script] + shim + body[main_script:] + '\n</body>\n</html>\n')
if pwa:
    # Versão instalável: ícone, tela cheia e funcionamento sem internet
    out = out.replace('<title>Vida da Amandinha</title>', '''<title>Vida da Amandinha</title>
<link rel="manifest" href="manifest.webmanifest">
<link rel="apple-touch-icon" href="apple-touch-icon.png">
<link rel="icon" href="icon-192.png">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="Amandinha">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<meta name="theme-color" content="#fff6f3">''')
    out = out.replace('\n</body>', "\n<script>if ('serviceWorker' in navigator && location.protocol.startsWith('http')) navigator.serviceWorker.register('sw.js');</script>\n</body>")
    target = os.path.join(root, 'docs', 'index.html')
else:
    target = os.path.join(root, 'meu-planner.html')
open(target, 'w', encoding='utf-8').write(out)
print(target, len(out), 'bytes;', {c: len(v) for c, v in seed.items()})
