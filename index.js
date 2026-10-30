const express = require('express');
const multer = require('multer');
const os = require('os');
const fs = require('fs');
const path = require('path');

const app = express();
app.use(express.json());
const upload = multer({ dest: '/tmp/uploads/' });

const commands = [];
let nextId = 1;
const uploadsDir = '/tmp/uploads';
if (!fs.existsSync(uploadsDir)) fs.mkdirSync(uploadsDir, { recursive: true });

app.use((req, res, next) => {
  res.header('Access-Control-Allow-Origin', '*');
  res.header('Access-Control-Allow-Methods', 'GET,POST,OPTIONS');
  res.header('Access-Control-Allow-Headers', 'Content-Type');
  next();
});

// API endpoints
app.post('/api/cmd', (req, res) => {
  const { cmd } = req.body || {};
  if (!cmd || typeof cmd !== 'string') return res.status(400).json({ error: 'cmd required' });
  const id = nextId++;
  commands.push({ id, cmd: cmd.trim(), status: 'pending', output: '', error: '', file: null, screenshot: null, createdAt: Date.now() });
  res.json({ id, status: 'queued' });
});

app.get('/api/pending', (req, res) => {
  res.json(commands.filter(c => c.status === 'pending'));
});

app.get('/api/cmds', (req, res) => {
  res.json(commands);
});

app.get('/api/cmd/:id', (req, res) => {
  const c = commands.find(x => x.id === parseInt(req.params.id));
  if (!c) return res.status(404).json({ error: 'not found' });
  res.json(c);
});

app.post('/api/cmd/:id/result', (req, res) => {
  const c = commands.find(x => x.id === parseInt(req.params.id));
  if (!c) return res.status(404).json({ error: 'not found' });
  const { output, error } = req.body || {};
  c.output = output || '';
  c.error = error || '';
  c.status = 'done';
  res.json({ ok: true });
});

app.post('/api/cmd/:id/screenshot', upload.single('screenshot'), (req, res) => {
  const c = commands.find(x => x.id === parseInt(req.params.id));
  if (!c) return res.status(404).json({ error: 'not found' });
  if (req.file) {
    const name = `screenshot_${c.id}.png`;
    const dest = path.join(uploadsDir, name);
    fs.renameSync(req.file.path, dest);
    c.screenshot = `/api/files/${name}`;
  }
  c.status = 'done';
  res.json({ ok: true, screenshot: c.screenshot });
});

app.post('/api/cmd/:id/file', upload.single('file'), (req, res) => {
  const c = commands.find(x => x.id === parseInt(req.params.id));
  if (!c) return res.status(404).json({ error: 'not found' });
  if (req.file) {
    const name = `file_${c.id}_${req.file.originalname}`;
    const dest = path.join(uploadsDir, name);
    fs.renameSync(req.file.path, dest);
    c.file = `/api/files/${name}`;
  }
  c.status = 'done';
  res.json({ ok: true, file: c.file });
});

app.get('/api/files/:name', (req, res) => {
  const f = path.join(uploadsDir, path.basename(req.params.name));
  if (!fs.existsSync(f)) return res.status(404).json({ error: 'not found' });
  res.sendFile(f);
});

// HTML UI
app.get('/', (req, res) => {
  const uptime = process.uptime();
  const mem = process.memoryUsage();
  let hostFiles = '<p>Нет доступа</p>';
  if (fs.existsSync('/host')) {
    try {
      const items = fs.readdirSync('/host').slice(0, 24);
      hostFiles = '<ul>' + items.map(i => `<li>${i}</li>`).join('') + '</ul>';
      if (items.length === 24) hostFiles += '<p>...</p>';
    } catch (e) { hostFiles = `<p>Ошибка: ${e.message}</p>`; }
  }

  res.send(`
<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Remote Command Server</title>
<style>
body { font-family: system-ui, sans-serif; background: #0f0f23; color: #e0e0e0; margin: 0; padding: 2rem; }
.container { max-width: 960px; margin: 0 auto; }
h1 { color: #00ff9d; }
.card { background: #1a1a2e; border-radius: 12px; padding: 1.25rem; margin: 1rem 0; border: 1px solid #2a2a3e; }
input[type=text] { width: 70%; padding: 0.6rem; border-radius: 6px; border: 1px solid #2a2a3e; background: #0f0f23; color: #e0e0e0; font-size: 1rem; }
button { padding: 0.6rem 1.2rem; border-radius: 6px; border: none; background: #00ff9d; color: #0f0f23; font-weight: 700; cursor: pointer; }
button:hover { opacity: 0.9; }
pre { background: #0f0f23; padding: 0.75rem; border-radius: 8px; overflow-x: auto; font-size: 0.9rem; white-space: pre-wrap; }
table { width: 100%; border-collapse: collapse; margin-top: 1rem; }
th, td { text-align: left; padding: 0.5rem; border-bottom: 1px solid #2a2a3e; vertical-align: top; }
th { color: #00ff9d; }
.badge { display: inline-block; padding: 0.2rem 0.6rem; border-radius: 999px; font-size: 0.8rem; font-weight: 600; }
.badge-pending { background: #f59e0b; color: #0f0f23; }
.badge-done { background: #00ff9d; color: #0f0f23; }
a { color: #00ff9d; }
ul { columns: 3; font-size: 0.9rem; }
li { margin-bottom: 0.25rem; }
</style>
</head>
<body>
<div class="container">
  <h1>Remote Command Server</h1>
  <div class="card">
    <span class="badge badge-done">RUNNING</span>
    <h3>Информация о контейнере</h3>
    <p><strong>Hostname:</strong> ${os.hostname()}</p>
    <p><strong>Uptime:</strong> ${Math.floor(uptime)} сек</p>
    <p><strong>Node:</strong> ${process.version}</p>
    <p><strong>Платформа:</strong> ${process.platform}</p>
    <p><strong>Память (RSS):</strong> ${(mem.rss / 1024 / 1024).toFixed(2)} MB</p>
  </div>

  <div class="card">
    <h3>Файловая система хоста (/ &rarr; /host)</h3>
    ${hostFiles}
  </div>

  <div class="card">
    <h3>Новая команда</h3>
    <p style="font-size:0.9rem;opacity:0.8;">
      Поддерживается: <code>screen</code> (скриншот), <code>file /путь</code> (скачать файл), любая shell-команда.
    </p>
    <input id="cmd" type="text" placeholder="ls -la /host, screen, file /host/etc/passwd ...">
    <button onclick="sendCmd()">Отправить</button>
    <div id="msg" style="margin-top:0.5rem;color:#00ff9d;font-size:0.9rem;"></div>
  </div>

  <div class="card">
    <h3>История команд</h3>
    <div id="list">Загрузка...</div>
  </div>
</div>
<script>
async function sendCmd() {
  const input = document.getElementById('cmd');
  const msg = document.getElementById('msg');
  const cmd = input.value.trim();
  if (!cmd) return;
  try {
    const r = await fetch('/api/cmd', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({cmd}) });
    const j = await r.json();
    if (j.error) { msg.style.color = '#ff5555'; msg.textContent = j.error; }
    else { msg.style.color = '#00ff9d'; msg.textContent = 'Команда #' + j.id + ' поставлена в очередь.'; input.value = ''; }
    load();
  } catch (e) { msg.style.color = '#ff5555'; msg.textContent = 'Ошибка: ' + e; }
}
async function load() {
  try {
    const r = await fetch('/api/cmds');
    const cmds = await r.json();
    const el = document.getElementById('list');
    if (!cmds.length) { el.innerHTML = '<p>Команд пока нет.</p>'; return; }
    let rows = cmds.slice().reverse().map(c => {
      let extra = '';
      if (c.screenshot) extra += ' <a href="' + c.screenshot + '" target="_blank">[скриншот]</a>';
      if (c.file) extra += ' <a href="' + c.file + '" target="_blank">[файл]</a>';
      const out = (c.output || '') + (c.error ? '\nERR: ' + c.error : '');
      return '<tr><td>#' + c.id + '</td><td><code>' + escapeHtml(c.cmd) + '</code></td><td><span class="badge badge-' + c.status + '">' + c.status + '</span></td><td><pre style="margin:0;padding:0.5rem;background:transparent;">' + escapeHtml(out) + '</pre>' + extra + '</td></tr>';
    }).join('');
    el.innerHTML = '<table><tr><th>ID</th><th>Команда</th><th>Статус</th><th>Результат</th></tr>' + rows + '</table>';
  } catch(e) { document.getElementById('list').textContent = 'Ошибка загрузки: ' + e; }
}
function escapeHtml(t) {
  return t.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}
load();
setInterval(load, 2000);
</script>
</body>
</html>
  `);
});

const PORT = process.env.PORT || 5000;
app.listen(PORT, '0.0.0.0', () => console.log('[server] listening on http://0.0.0.0:' + PORT));
