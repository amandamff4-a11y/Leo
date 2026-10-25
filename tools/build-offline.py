"""Gera meu-planner.html: a versão do planner que funciona sozinha (sem o Claude),
salvando os dados no navegador. Uso: python3 tools/build-offline.py <pasta-com-dados>"""
import json, os, sys

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(root, 'planejamento-semana.html'), encoding='utf-8').read()
data_dir = sys.argv[1] if len(sys.argv) > 1 else None

seed = {c: {} for c in ('fixed', 'weeks', 'goals', 'books', 'shows')}
if data_dir:
    for c in seed:
        d = os.path.join(data_dir, c)
        if os.path.isdir(d):
            for f in sorted(os.listdir(d)):
                if f.endswith('.json'):
                    seed[c][f[:-5]] = json.load(open(os.path.join(d, f), encoding='utf-8'))

head, body = src.split('\n<div class="wrap">', 1)
head = head.replace('<meta name="claude:viewport-fit-sides" content="cover">\n', '')
main_script = body.index('\n<script>')

shim = r'''
<style>
  .backup { margin-top: 28px; padding: 14px 16px; border-radius: 16px; border: 1.5px dashed color-mix(in srgb, var(--title) 40%, transparent); display: flex; flex-wrap: wrap; gap: 10px; align-items: center; color: var(--muted); font-size: 16px; }
  .backup p { margin: 0; flex: 1 1 260px; }
</style>
<script>
// Banco de dados local: guarda tudo neste navegador (localStorage), no mesmo formato do app online
(function () {
  const KEY = 'meu-planner-dados';
  const SEED = __SEED__;
  let data = null;
  try { data = JSON.parse(localStorage.getItem(KEY)); } catch {}
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
  // Mantém abas abertas ao mesmo tempo sincronizadas
  addEventListener('storage', e => { if (e.key !== KEY) return; try { data = JSON.parse(e.newValue) || data; } catch {} Object.keys(subs).forEach(fire); });

  const box = document.createElement('div');
  box.className = 'backup';
  box.innerHTML = '<p>Seus dados ficam salvos neste navegador. Guarde uma cópia de vez em quando, ou use a cópia para levar o planner para outro aparelho.</p>' +
    '<button class="btn" id="bkSave">Baixar cópia dos dados</button><button class="btn" id="bkLoad">Abrir cópia</button><input type="file" id="bkFile" accept="application/json,.json" hidden>';
  document.querySelector('.wrap').appendChild(box);
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
       + head + '\n</head>\n<body>\n<div class="wrap">' + body[:main_script] + shim + body[main_script:] + '\n</body>\n</html>\n')
out = out.replace('<title>Planejamento da Semana</title>', '<title>Meu Planner</title>')
open(os.path.join(root, 'meu-planner.html'), 'w', encoding='utf-8').write(out)
print('meu-planner.html', len(out), 'bytes;', {c: len(v) for c, v in seed.items()})
