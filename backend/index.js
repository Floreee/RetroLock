// Retrolock Homeserver Application
// Admin Webinterface + Token Management (one_time / temporary / permanent)
// Door Open Proxy for Raspberry Pi

const express = require('express')
const sqlite3 = require('sqlite3').verbose()
const crypto = require('crypto')
const axios = require('axios')

const PORT =  process.env.PORT || 3000
const PI_GPIO_URL = 'https://192.168.178.100:5000/gpio'
const PUBLIC_HOST = 'http://127.0.0.1'

const ADMIN_TOKEN = process.env.RETROLOCK_ADMIN_TOKEN
const ADMIN_USER = process.env.RETROLOCK_ADMIN_USER || 'admin'
const ADMIN_PASS = process.env.RETROLOCK_ADMIN_PASS

if (!ADMIN_TOKEN || !ADMIN_PASS) {
  console.error('RETROLOCK_ADMIN_TOKEN or RETROLOCK_ADMIN_PASS not set')
  process.exit(1)
}

const app = express()
// ---------------- Security Headers ----------------

app.use((req, res, next) => {
  res.setHeader('X-Robots-Tag', 'noindex, nofollow')
  res.setHeader('Referrer-Policy', 'no-referrer')
  res.setHeader('Cache-Control', 'no-store')
  next()
})
app.use(express.json())
app.use(express.urlencoded({ extended: false }))

console.log(`[${new Date().toISOString()}] START: Retrolock Homeserver`)
console.log('[ENV] ADMIN_USER:', process.env.RETROLOCK_ADMIN_USER)
console.log('[ENV] ADMIN_PASS:', process.env.RETROLOCK_ADMIN_PASS ? 'SET' : 'NOT SET')
console.log('[ENV] ADMIN_TOKEN:', process.env.RETROLOCK_ADMIN_TOKEN ? 'SET' : 'NOT SET')
console.log('[ENV] PUBLIC_HOST:', process.env.RETROLOCK_PUBLIC_HOST)

process.on('exit', (code) => {
  console.log('[PROCESS EXIT]', code)
})

process.on('SIGTERM', () => {
  console.log('[SIGTERM]')
})

process.on('SIGINT', () => {
  console.log('[SIGINT]')
})

process.on('uncaughtException', err => {
  console.error('[UNCAUGHT]', err)
})

process.on('unhandledRejection', err => {
  console.error('[UNHANDLED]', err)
})

console.log('[PID]', process.pid)
setInterval(() => {
  console.log('[HEARTBEAT]', new Date().toISOString())
}, 2000)


// ---------------- DB ----------------

console.log(`[${new Date().toISOString()}] CHECKPOINT: Opening SQLite DB`)

const path = require('path')
const DB_PATH = path.join(__dirname, 'data', 'retrolock.db')
const db = new sqlite3.Database(DB_PATH, (err) => {
  if (err) {
    console.error(`[${new Date().toISOString()}] DB ERROR:`, err)
  } else {
    console.log(`[${new Date().toISOString()}] CHECKPOINT: DB opened successfully`)
  }
})


db.serialize(() => {
  db.run(`
    CREATE TABLE IF NOT EXISTS tokens (
      token TEXT PRIMARY KEY,
      type TEXT NOT NULL,              -- one_time | temporary | permanent
      note TEXT,
      created_at INTEGER NOT NULL,
      expires_at INTEGER,
      enabled INTEGER DEFAULT 1,
      last_used_at INTEGER,
      use_count INTEGER DEFAULT 0
    );
  `)
})

// ---------------- Helpers ----------------

function generateToken() {
  return crypto.randomBytes(16).toString('base64url')
}

async function openDoor() {
  await axios.post(
    PI_GPIO_URL,
    { state: 'open' },
    { headers: { Authorization: `Bearer ${ADMIN_TOKEN}` }, timeout: 3000 }
  )
}

function renderPage(title, body) {
  return `<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8" />
<title>${title}</title>
<meta name="viewport" content="width=device-width, initial-scale=1" />
<style>
body { font-family: sans-serif; background:#111; color:#eee; padding:2rem }
input, select, button { padding:.4rem; margin:.2rem }
table { border-collapse: collapse; margin-top:1rem }
th, td { border:1px solid #444; padding:.4rem }
a { color:#6cf }
.copy-btn { cursor:pointer; color:#6cf; text-decoration:underline; }
#copy-notification {
  position: fixed;
  top: 1rem;
  right: 1rem;
  background: #333;
  color: #6cf;
  padding: 0.5rem 1rem;
  border-radius: 0.5rem;
  opacity: 0;
  transition: opacity 0.3s ease;
}
</style>
</head>
<body>
<div id="copy-notification">Link kopiert</div>
${body}
<script>
function copyLink(token) {
  navigator.clipboard.writeText('https://door.domain.net/open/' + token)
    .then(() => {
      const notif = document.getElementById('copy-notification');
      notif.style.opacity = '1';
      setTimeout(() => notif.style.opacity = '0', 1200);
    })
    .catch(err => console.error('Fehler beim Kopieren', err));
}
</script>
</body>
</html>`
}

// ---------------- Auth ----------------

function basicAuth(req, res, next) {
  const auth = req.headers.authorization || ''
  const [type, encoded] = auth.split(' ')
  if (type !== 'Basic' || !encoded) {
    res.setHeader('WWW-Authenticate', 'Basic realm="Retrolock Admin"')
    return res.status(401).end()
  }
  const [user, pass] = Buffer.from(encoded, 'base64').toString().split(':')
  if (user !== ADMIN_USER || pass !== ADMIN_PASS) {
    return res.status(403).end()
  }
  next()
}

// ---------------- Admin UI ----------------

app.get('/admin', basicAuth, (req, res) => {
  const now = Date.now()
  db.all('SELECT * FROM tokens ORDER BY created_at DESC', (err, rows) => {
    const list = rows.map(t => {
      const active = t.enabled && (!t.expires_at || t.expires_at > now) ? '✔️' : '❌'
      return `<tr>
        <td>${t.type}</td>
        <td>${t.note || ''}</td>
        <td>${t.expires_at ? new Date(t.expires_at).toLocaleString() : '—'}</td>
        <td>${active}</td>
        <td>${t.token}</td>
        <td><span class="copy-btn" onclick="copyLink('${t.token}')">Copy</span></td>
        <td>${t.use_count}</td>
        <td>${t.last_used_at ? new Date(t.last_used_at).toLocaleString() : '—'}</td>
        <td><form method="POST"
        action="/admin/delete/${t.token}"
        onsubmit="return confirm('Token wirklich löschen? Diese Aktion kann nicht rückgängig gemacht werden.')">
    <button type="submit">löschen</button>
  </form></td>
      </tr>`
    }).join('')

    res.send(renderPage('Admin', `
      <h1>🔐 Retrolock Admin</h1>

      <form method="POST" action="/admin/create">
        <select name="type" required>
          <option value="one_time">One-Time</option>
          <option value="temporary">Temporär</option>
          <option value="permanent">Permanent</option>
        </select>
        <input name="note" placeholder="Notiz" />
        <input name="minutes" placeholder="Ablauf (Min)" />
        <button>Token erstellen</button>
      </form>

      <table>
        <tr>
          <th>Typ</th><th>Notiz</th><th>Ablauf</th><th>Aktiv</th>
          <th>Token</th><th>Copy</th><th>Uses</th><th>Letzte Nutzung</th><th></th>
        </tr>
        ${list}
      </table>
    `))
  })
})

// ---------------- Admin Actions ----------------

app.post('/admin/create', basicAuth, (req, res) => {
  const token = generateToken()
  const now = Date.now()
  const minutes = parseInt(req.body.minutes)
  const expires = minutes ? now + minutes * 60000 : null

  if (req.body.type === 'temporary' && !expires) {
    return res.status(400).send('Temporary tokens require expiration')
  }
  
  if (req.body.type === 'permanent') {
    expires = null
  }

  db.run(
    'INSERT INTO tokens (token,type,note,created_at,expires_at) VALUES (?,?,?,?,?)',
    token,
    req.body.type,
    req.body.note,
    now,
    expires,
    () => res.redirect('/admin')
  )
})

app.post('/admin/delete/:token', basicAuth, (req, res) => {
  db.run(
    'DELETE FROM tokens WHERE token = ?',
    req.params.token,
    () => res.redirect('/admin')
  )
})

// ---------------- Door Open ----------------

app.get('/open/:token', async (req, res) => {
  const token = req.params.token
  const now = Date.now()

  db.get('SELECT * FROM tokens WHERE token = ? AND enabled = 1', token, async (err, row) => {
    if (!row) return res.send(renderPage('Ungültig', '<h1>❌ Link ungültig</h1>'))

    if (row.expires_at && row.expires_at < now)
      return res.send(renderPage('Abgelaufen', '<h1>❌ Link abgelaufen</h1>'))

    if (row.type === 'permanent')
      return res.send(renderPage('Fehler', '<h1>⚠️ Permanente Tokens sind nicht per Link erlaubt</h1>'))

    db.run(
      'UPDATE tokens SET last_used_at=?, use_count=use_count+1 WHERE token=?',
      now,
      token
    )

    if (row.type === 'one_time') {
      db.run('UPDATE tokens SET enabled=0 WHERE token=?', token)
    }

    try {
      await openDoor()
      res.send(renderPage('Erfolg', '<h1>🚪 Tür geöffnet</h1>'))
    } catch {
      res.send(renderPage('Fehler', '<h1>⚠️ Tür konnte nicht geöffnet werden</h1>'))
    }
  })
})

console.log(`[${new Date().toISOString()}] CHECKPOINT: Before app.listen`)

app.listen(PORT, '0.0.0.0', () => {
  console.log(`Retrolock Homeserver running on port ${PORT}`)
})
