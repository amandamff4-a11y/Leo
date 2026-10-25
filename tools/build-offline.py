"""Gera meu-planner.html: a versão do planner que funciona sozinha (sem o Claude),
salvando os dados no navegador. Uso: python3 tools/build-offline.py <pasta-com-dados>"""
import json, os, sys

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(root, 'planejamento-semana.html'), encoding='utf-8').read()
args = sys.argv[1:]
pwa = '--pwa' in args
args = [a for a in args if a != '--pwa']
data_dir = args[0] if args else None

seed = {c: {} for c in ('fixed', 'weeks', 'goals', 'books', 'shows')}
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
  // Primeira vez abrindo sem dados: mostra como trazer a agenda de um arquivo de cópia
  if (fresh && !Object.values(data).some(c => Object.keys(c).length)) {
    const hi = document.createElement('div');
    hi.className = 'notice';
    hi.innerHTML = '<b>Bem-vinda ao seu planner! ♡</b><br>Para trazer a sua agenda, toque em <b>Abrir cópia</b> e escolha o arquivo <b>meus-dados.json</b>. Ou comece do zero adicionando suas atividades.<br><button class="btn primary" style="margin-top:8px" id="bkLoad2">Abrir cópia</button>';
    document.querySelector('.mainnav').after(hi);
    document.getElementById('bkLoad2').onclick = () => file.click();
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
out = out.replace('<title>Planejamento da Semana</title>', '<title>Meu Planner</title>')
if pwa:
    # Versão instalável: ícone, tela cheia e funcionamento sem internet
    out = out.replace('<title>Meu Planner</title>', '''<title>Meu Planner</title>
<link rel="manifest" href="manifest.webmanifest">
<link rel="apple-touch-icon" href="apple-touch-icon.png">
<link rel="icon" href="icon-192.png">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="Meu Planner">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<meta name="theme-color" content="#fdf8f4">''')
    out = out.replace('\n</body>', "\n<script>if ('serviceWorker' in navigator && location.protocol.startsWith('http')) navigator.serviceWorker.register('sw.js');</script>\n</body>")
    target = os.path.join(root, 'docs', 'index.html')
else:
    target = os.path.join(root, 'meu-planner.html')
open(target, 'w', encoding='utf-8').write(out)
print(target, len(out), 'bytes;', {c: len(v) for c, v in seed.items()})
