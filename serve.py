#!/usr/bin/env python3
"""
Local server for Claude Conversations.
Run: python3 serve.py
Then open: http://localhost:8080
"""
import http.server
import json
import os
import html
import re
import threading
from datetime import datetime

_data_lock = threading.Lock()

PORT = 9000
SITE_DIR = "site"
DATA_FILE = "conversations.json"
PROJECTS_FILE = "projects.json"
DELETED_FILE = "deleted.json"


def load_deleted():
    if os.path.exists(DELETED_FILE):
        with open(DELETED_FILE, encoding='utf-8') as f:
            return set(json.load(f))
    return set()


def save_deleted(deleted_set):
    with open(DELETED_FILE, 'w', encoding='utf-8') as f:
        json.dump(sorted(deleted_set), f, indent=2)

MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']

def fmt_date(iso):
    try:
        dt = datetime.fromisoformat(iso.replace('Z', '+00:00'))
        return dt.strftime('%b %d, %Y')
    except Exception:
        return iso or ''

def iso_to_ymd(iso):
    try:
        dt = datetime.fromisoformat(iso.replace('Z', '+00:00'))
        return dt.strftime('%Y-%m-%d')
    except Exception:
        return ''

def month_label(ym):
    y, m = ym.split('-')
    return MONTHS[int(m)-1] + ' ' + y

def build_index(conversations, projects):
    conversations = sorted(conversations, key=lambda c: c.get('updated_at', ''), reverse=True)

    from collections import Counter
    month_counts = Counter(
        iso_to_ymd(c.get('updated_at',''))[:7]
        for c in conversations if c.get('updated_at')
    )
    unique_months = sorted(month_counts.keys(), reverse=True)
    month_options = '\n'.join(
        f'<option value="{ym}">{month_label(ym)} ({month_counts[ym]})</option>'
        for ym in unique_months
    )

    items_html = []
    for conv in conversations:
        uuid = html.escape(conv['uuid'])
        name = html.escape(conv.get('name') or 'Untitled')
        summary = html.escape(conv.get('summary') or '')
        updated = fmt_date(conv.get('updated_at', ''))
        ymd = iso_to_ymd(conv.get('updated_at', ''))
        human_msgs = sum(1 for m in conv.get('chat_messages', []) if m.get('sender') == 'human')
        sum_html = f"<div class='conv-summary'>{summary}</div>" if summary else ''
        items_html.append(f"""<div class="conv-item" data-name="{name.lower()}" data-month="{ymd[:7]}" data-uuid="{uuid}">
  <div class="conv-meta">
    <div class="conv-name"><a href="/c/{uuid}.html">{name}</a></div>
    <div class="conv-info">{updated} &middot; {human_msgs} message{"s" if human_msgs != 1 else ""}</div>
    {sum_html}
  </div>
  <button class="del-btn" data-uuid="{uuid}" title="Delete conversation">&#128465;</button>
</div>""")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Claude Conversations</title>
<style>
:root{{--bg:#f9f9f8;--surface:#fff;--border:#e5e5e3;--text:#1a1a1a;--muted:#6b6b6b;--link:#2563eb;--code-bg:#f3f4f6;--danger:#dc2626;}}
*{{box-sizing:border-box;margin:0;padding:0;}}
body{{background:var(--bg);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;font-size:15px;line-height:1.6;}}
a{{color:var(--link);text-decoration:none;}}a:hover{{text-decoration:underline;}}
header{{background:var(--surface);border-bottom:1px solid var(--border);padding:20px 32px;display:flex;align-items:center;justify-content:space-between;}}
.header-left h1{{font-size:1.4rem;font-weight:700;}}
.header-left p{{color:var(--muted);font-size:.9rem;margin-top:2px;}}
.header-nav a{{font-size:.9rem;color:var(--muted);padding:6px 12px;border:1px solid var(--border);border-radius:6px;}}
.header-nav a:hover{{color:var(--link);border-color:var(--link);text-decoration:none;}}
.toolbar{{padding:12px 32px;background:var(--surface);border-bottom:1px solid var(--border);position:sticky;top:0;z-index:10;display:flex;flex-wrap:wrap;gap:10px;align-items:center;}}
.search-input{{flex:1;min-width:180px;max-width:340px;padding:7px 13px;border:1px solid var(--border);border-radius:6px;font-size:.93rem;background:var(--bg);}}
#month-select{{padding:7px 10px;border:1px solid var(--border);border-radius:6px;font-size:.9rem;background:var(--bg);color:var(--text);cursor:pointer;}}
.sort-btn{{background:none;border:1px solid var(--border);border-radius:6px;padding:7px 12px;font-size:.85rem;cursor:pointer;color:var(--muted);white-space:nowrap;}}
.sort-btn:hover{{color:var(--text);border-color:var(--text);}}
.result-count{{font-size:.83rem;color:var(--muted);white-space:nowrap;}}
.list{{max-width:860px;margin:0 auto;padding:24px 32px;}}
.conv-item{{background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:16px 20px;margin-bottom:10px;display:flex;align-items:flex-start;gap:12px;transition:box-shadow .1s;}}
.conv-item:hover{{box-shadow:0 2px 8px rgba(0,0,0,.07);}}
.conv-meta{{flex:1;min-width:0;}}
.conv-name{{font-weight:600;font-size:1rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}}
.conv-name a{{color:var(--text);}}
.conv-name a:hover{{color:var(--link);}}
.conv-info{{color:var(--muted);font-size:.83rem;margin-top:3px;}}
.conv-summary{{color:var(--muted);font-size:.88rem;margin-top:6px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;}}
.del-btn{{background:none;border:none;cursor:pointer;font-size:1rem;color:var(--muted);padding:4px 6px;border-radius:4px;flex-shrink:0;opacity:0;transition:opacity .15s,color .15s;}}
.conv-item:hover .del-btn{{opacity:1;}}
.del-btn:hover{{color:var(--danger);}}
.del-btn.confirm{{opacity:1;color:var(--danger);font-size:.8rem;font-weight:700;border:1px solid var(--danger);padding:3px 8px;border-radius:4px;}}
#no-results{{display:none;color:var(--muted);text-align:center;padding:48px 0;}}
</style>
</head>
<body>
<header>
  <div class="header-left">
    <h1>Claude Conversations</h1>
    <p>{len(conversations)} conversations</p>
  </div>
  <nav class="header-nav"><a href="/projects.html">Projects ({len(projects)})</a></nav>
</header>
<div class="toolbar">
  <input class="search-input" type="search" id="search" placeholder="Search conversations…" autofocus>
  <select id="month-select">
    <option value="">All months</option>
{month_options}
  </select>
  <button class="sort-btn" id="sort-btn" title="Toggle sort order">Newest first</button>
  <span class="result-count" id="result-count"></span>
</div>
<div class="list">
{''.join(items_html)}
  <div id="no-results">No conversations found.</div>
</div>
<script>
const list = document.querySelector('.list');
const items = Array.from(document.querySelectorAll('.conv-item'));
const noResults = document.getElementById('no-results');
const resultCount = document.getElementById('result-count');
const searchEl = document.getElementById('search');
const monthSel = document.getElementById('month-select');
const sortBtn = document.getElementById('sort-btn');
let newestFirst = true;

function applyFilters() {{
  const q = searchEl.value.toLowerCase().trim();
  const m = monthSel.value;
  let visible = 0;

  // Sort: detach all items, re-insert in desired order
  const sorted = [...items].sort((a, b) => {{
    const da = a.dataset.month, db = b.dataset.month;
    return newestFirst ? db.localeCompare(da) : da.localeCompare(db);
  }});
  sorted.forEach(el => list.appendChild(el));
  list.appendChild(noResults);

  items.forEach(el => {{
    const ms = !q || el.dataset.name.includes(q) || (el.querySelector('.conv-summary')?.textContent.toLowerCase().includes(q));
    const mm = !m || el.dataset.month === m;
    el.style.display = (ms && mm) ? '' : 'none';
    if (ms && mm) visible++;
  }});
  noResults.style.display = visible === 0 ? '' : 'none';
  resultCount.textContent = visible + ' conversation' + (visible !== 1 ? 's' : '');
}}

monthSel.addEventListener('change', applyFilters);
searchEl.addEventListener('input', applyFilters);

sortBtn.addEventListener('click', () => {{
  newestFirst = !newestFirst;
  sortBtn.textContent = newestFirst ? 'Newest first' : 'Oldest first';
  applyFilters();
}});

// Esc clears search
document.addEventListener('keydown', e => {{
  if (e.key === 'Escape' && searchEl.value) {{
    searchEl.value = '';
    applyFilters();
    searchEl.focus();
  }}
}});

applyFilters();

// Delete buttons — first click shows "Delete?" confirmation, second click deletes
document.querySelectorAll('.del-btn').forEach(btn => {{
  let confirmed = false;
  let timer = null;

  btn.addEventListener('click', async (e) => {{
    e.preventDefault();
    e.stopPropagation();

    if (!confirmed) {{
      confirmed = true;
      btn.textContent = 'Delete?';
      btn.classList.add('confirm');
      timer = setTimeout(() => {{
        confirmed = false;
        btn.textContent = '🗑';
        btn.classList.remove('confirm');
      }}, 3000);
      return;
    }}

    clearTimeout(timer);
    const uuid = btn.dataset.uuid;
    btn.textContent = '…';
    btn.disabled = true;

    try {{
      const res = await fetch('/api/conversation/' + uuid, {{ method: 'DELETE' }});
      if (!res.ok) throw new Error('Server error');
      const item = btn.closest('.conv-item');
      item.style.transition = 'opacity .2s';
      item.style.opacity = '0';
      setTimeout(() => {{
        item.remove();
        applyFilters();
      }}, 200);
    }} catch (err) {{
      btn.textContent = '🗑';
      btn.disabled = false;
      confirmed = false;
      alert('Delete failed: ' + err.message);
    }}
  }});
}});
</script>
</body>
</html>"""


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=SITE_DIR, **kwargs)

    def do_DELETE(self):
        m = re.match(r'^/api/conversation/([0-9a-f-]+)$', self.path)
        if not m:
            self._json(404, {'error': 'Not found'})
            return

        uuid = m.group(1)

        with _data_lock:
            with open(DATA_FILE, encoding='utf-8') as f:
                conversations = json.load(f)
            with open(PROJECTS_FILE, encoding='utf-8') as f:
                projects = json.load(f)

            deleted = load_deleted()
            if uuid not in {c['uuid'] for c in conversations} and uuid not in deleted:
                self._json(404, {'error': 'Conversation not found'})
                return

            # Record in deleted.json — survives fresh data imports
            deleted.add(uuid)
            save_deleted(deleted)

            # Remove from conversations.json too
            with open(DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump([c for c in conversations if c['uuid'] != uuid], f, ensure_ascii=False)

        # Remove conversation HTML page (outside lock — no data integrity risk)
        page_path = os.path.join(SITE_DIR, 'c', f'{uuid}.html')
        if os.path.exists(page_path):
            os.remove(page_path)

        remaining = [c for c in conversations if c['uuid'] not in deleted]
        index_html = build_index(remaining, projects)
        with open(os.path.join(SITE_DIR, 'index.html'), 'w', encoding='utf-8') as f:
            f.write(index_html)

        print(f'Deleted {uuid} — {len(remaining)} conversations remaining')
        self._json(200, {'ok': True, 'remaining': len(remaining)})

    def _json(self, code, data):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', len(body))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        # Suppress noisy GET logs, keep DELETE logs
        if args and args[0].startswith('DELETE'):
            super().log_message(fmt, *args)


if __name__ == '__main__':
    with open(DATA_FILE, encoding='utf-8') as f:
        conversations = json.load(f)
    with open(PROJECTS_FILE, encoding='utf-8') as f:
        projects = json.load(f)

    deleted = load_deleted()
    if deleted:
        before = len(conversations)
        conversations = [c for c in conversations if c['uuid'] not in deleted]
        print(f'Filtered {before - len(conversations)} previously deleted conversations ({len(conversations)} remaining)')

    index_html = build_index(conversations, projects)
    with open(os.path.join(SITE_DIR, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(index_html)

    with http.server.HTTPServer(('', PORT), Handler) as httpd:
        print(f'Serving at http://localhost:{PORT}')
        print('Press Ctrl+C to stop.')
        httpd.serve_forever()
