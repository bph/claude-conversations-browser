#!/usr/bin/env python3
import json
import os
import html
from datetime import datetime, timezone

DATA_FILE = "conversations.json"
PROJECTS_FILE = "projects.json"
OUT_DIR = "site"
CONV_DIR = os.path.join(OUT_DIR, "c")

os.makedirs(CONV_DIR, exist_ok=True)

with open(DATA_FILE, encoding="utf-8") as f:
    conversations = json.load(f)

with open(PROJECTS_FILE, encoding="utf-8") as f:
    projects = json.load(f)

# Sort newest first
conversations.sort(key=lambda c: c.get("updated_at", ""), reverse=True)

def fmt_date(iso):
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.strftime("%b %d, %Y")
    except Exception:
        return iso or ""

def fmt_datetime(iso):
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.strftime("%b %d, %Y %H:%M")
    except Exception:
        return iso or ""

SHARED_CSS = """
:root {
  --bg: #f9f9f8;
  --surface: #ffffff;
  --border: #e5e5e3;
  --text: #1a1a1a;
  --muted: #6b6b6b;
  --human-bg: #f0f4ff;
  --human-border: #c7d4f7;
  --ai-bg: #ffffff;
  --ai-border: #e5e5e3;
  --tool-bg: #f5f5f4;
  --tool-border: #d4d4d1;
  --accent: #d97706;
  --link: #2563eb;
  --code-bg: #f3f4f6;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: var(--bg); color: var(--text); font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; font-size: 15px; line-height: 1.6; }
a { color: var(--link); text-decoration: none; }
a:hover { text-decoration: underline; }
code { background: var(--code-bg); padding: 1px 5px; border-radius: 3px; font-size: 0.88em; font-family: "SF Mono", Menlo, monospace; }
pre { background: var(--code-bg); border: 1px solid var(--border); border-radius: 6px; padding: 14px 16px; overflow-x: auto; margin: 10px 0; }
pre code { background: none; padding: 0; font-size: 0.85em; }
"""

INDEX_HTML = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Claude Conversations</title>
<style>
{SHARED_CSS}
header {{ background: var(--surface); border-bottom: 1px solid var(--border); padding: 20px 32px; display: flex; align-items: center; justify-content: space-between; }}
.header-left h1 {{ font-size: 1.4rem; font-weight: 700; }}
.header-left p {{ color: var(--muted); font-size: 0.9rem; margin-top: 2px; }}
.header-nav a {{ font-size: 0.9rem; color: var(--muted); padding: 6px 12px; border: 1px solid var(--border); border-radius: 6px; }}
.header-nav a:hover {{ color: var(--link); border-color: var(--link); text-decoration: none; }}
.toolbar {{ padding: 12px 32px; background: var(--surface); border-bottom: 1px solid var(--border); position: sticky; top: 0; z-index: 10; display: flex; flex-wrap: wrap; gap: 10px; align-items: center; }}
.search-input {{ flex: 1; min-width: 180px; max-width: 340px; padding: 7px 13px; border: 1px solid var(--border); border-radius: 6px; font-size: 0.93rem; background: var(--bg); }}
.period-toggle {{ display: flex; border: 1px solid var(--border); border-radius: 6px; overflow: hidden; }}
.period-toggle button {{ background: none; border: none; padding: 7px 14px; font-size: 0.88rem; cursor: pointer; color: var(--muted); border-right: 1px solid var(--border); }}
.period-toggle button:last-child {{ border-right: none; }}
.period-toggle button.active {{ background: var(--text); color: #fff; }}
.period-nav {{ display: flex; align-items: center; gap: 6px; }}
.period-nav button {{ background: none; border: 1px solid var(--border); border-radius: 6px; width: 30px; height: 30px; cursor: pointer; font-size: 1rem; color: var(--muted); display: flex; align-items: center; justify-content: center; }}
.period-nav button:hover {{ border-color: var(--text); color: var(--text); }}
.period-nav button:disabled {{ opacity: 0.3; cursor: default; }}
#period-label {{ font-size: 0.9rem; font-weight: 600; min-width: 150px; text-align: center; }}
.result-count {{ font-size: 0.83rem; color: var(--muted); margin-left: auto; white-space: nowrap; }}
.list {{ max-width: 860px; margin: 0 auto; padding: 24px 32px; }}
.conv-item {{ background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 16px 20px; margin-bottom: 10px; display: flex; align-items: flex-start; gap: 16px; transition: box-shadow 0.1s; }}
.conv-item:hover {{ box-shadow: 0 2px 8px rgba(0,0,0,0.07); }}
.conv-meta {{ flex: 1; min-width: 0; }}
.conv-name {{ font-weight: 600; font-size: 1rem; color: var(--text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
.conv-name a {{ color: inherit; }}
.conv-name a:hover {{ color: var(--link); }}
.conv-info {{ color: var(--muted); font-size: 0.83rem; margin-top: 3px; }}
.conv-summary {{ color: var(--muted); font-size: 0.88rem; margin-top: 6px; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }}
.badge {{ background: var(--code-bg); border: 1px solid var(--border); border-radius: 12px; padding: 2px 10px; font-size: 0.78rem; color: var(--muted); white-space: nowrap; flex-shrink: 0; }}
#no-results {{ display: none; color: var(--muted); text-align: center; padding: 48px 0; }}
</style>
</head>
<body>
<header>
  <div class="header-left">
    <h1>Claude Conversations</h1>
    <p>{len(conversations)} conversations</p>
  </div>
  <nav class="header-nav">
    <a href="projects.html">Projects ({len(projects)})</a>
  </nav>
</header>
<div class="toolbar">
  <input class="search-input" type="search" id="search" placeholder="Search conversations…" autofocus>
  <div class="period-toggle">
    <button data-mode="month" class="active">Month</button>
    <button data-mode="week">Week</button>
    <button data-mode="day">Day</button>
  </div>
  <div class="period-nav">
    <button id="prev-btn" title="Previous">&#8592;</button>
    <span id="period-label"></span>
    <button id="next-btn" title="Next">&#8594;</button>
  </div>
  <span class="result-count" id="result-count"></span>
</div>
<div class="list" id="list">
"""

def iso_to_ymd(iso):
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return ""

items = []
for conv in conversations:
    uuid = conv["uuid"]
    name = html.escape(conv.get("name") or "Untitled")
    summary = html.escape(conv.get("summary") or "")
    updated = fmt_date(conv.get("updated_at", ""))
    ymd = iso_to_ymd(conv.get("updated_at", ""))
    human_msgs = sum(1 for m in conv.get("chat_messages", []) if m.get("sender") == "human")

    item = f"""<div class="conv-item" data-name="{name.lower()}" data-date="{ymd}">
  <div class="conv-meta">
    <div class="conv-name"><a href="c/{uuid}.html">{name}</a></div>
    <div class="conv-info">{updated} &middot; {human_msgs} message{"s" if human_msgs != 1 else ""}</div>
    {"<div class='conv-summary'>" + summary + "</div>" if summary else ""}
  </div>
  <span class="badge">{updated}</span>
</div>"""
    items.append(item)

INDEX_HTML += "\n".join(items)
INDEX_HTML += """
  <div id="no-results">No conversations in this period.</div>
</div>
<script>
const items = Array.from(document.querySelectorAll('.conv-item'));
const noResults = document.getElementById('no-results');
const resultCount = document.getElementById('result-count');
const searchEl = document.getElementById('search');
const periodLabel = document.getElementById('period-label');
const prevBtn = document.getElementById('prev-btn');
const nextBtn = document.getElementById('next-btn');

// Collect all dates to know bounds
const allDates = items.map(el => el.dataset.date).filter(Boolean).sort();
const minDate = allDates[0];
const maxDate = allDates[allDates.length - 1];

let mode = 'month'; // month | week | day
let offset = 0;     // 0 = period containing most recent conv, negative = older

// Anchor: the period that contains the newest conversation
function anchorDate() {
  return maxDate; // YYYY-MM-DD
}

function parseYMD(s) {
  const [y, m, d] = s.split('-').map(Number);
  return new Date(y, m - 1, d);
}

function getMonday(date) {
  const d = new Date(date);
  const day = d.getDay() || 7;
  d.setDate(d.getDate() - day + 1);
  return d;
}

function addDays(date, n) {
  const d = new Date(date);
  d.setDate(d.getDate() + n);
  return d;
}

function periodBounds(mode, offset) {
  const anchor = parseYMD(anchorDate());
  if (mode === 'month') {
    const y = anchor.getFullYear();
    const m = anchor.getMonth() + offset;
    const start = new Date(y, m, 1);
    const end = new Date(y, m + 1, 0);
    return { start, end };
  } else if (mode === 'week') {
    const monday = getMonday(anchor);
    const start = addDays(monday, offset * 7);
    const end = addDays(start, 6);
    return { start, end };
  } else {
    const start = addDays(anchor, offset);
    return { start, end: start };
  }
}

function fmtPeriodLabel(mode, offset) {
  const { start, end } = periodBounds(mode, offset);
  const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  if (mode === 'month') {
    return months[start.getMonth()] + ' ' + start.getFullYear();
  } else if (mode === 'week') {
    const s = months[start.getMonth()] + ' ' + start.getDate();
    const e = months[end.getMonth()] + ' ' + end.getDate() + ', ' + end.getFullYear();
    return s + ' – ' + e;
  } else {
    return months[start.getMonth()] + ' ' + start.getDate() + ', ' + start.getFullYear();
  }
}

function inPeriod(dateStr, mode, offset) {
  if (!dateStr) return false;
  const d = parseYMD(dateStr);
  const { start, end } = periodBounds(mode, offset);
  return d >= start && d <= end;
}

function toYMD(d) {
  return d.getFullYear() + '-' + String(d.getMonth()+1).padStart(2,'0') + '-' + String(d.getDate()).padStart(2,'0');
}

function hasPeriod(mode, off) {
  const { start, end } = periodBounds(mode, off);
  const s = toYMD(start), e = toYMD(end);
  return allDates.some(d => d >= s && d <= e);
}

function applyFilters() {
  const q = searchEl.value.toLowerCase().trim();
  periodLabel.textContent = fmtPeriodLabel(mode, offset);

  // disable nav buttons at data bounds
  prevBtn.disabled = !hasPeriod(mode, offset - 1);
  nextBtn.disabled = offset >= 0;

  let visible = 0;
  items.forEach(el => {
    const matchSearch = !q || el.dataset.name.includes(q) || el.querySelector('.conv-summary')?.textContent.toLowerCase().includes(q);
    const matchPeriod = inPeriod(el.dataset.date, mode, offset);
    const show = matchSearch && matchPeriod;
    el.style.display = show ? '' : 'none';
    if (show) visible++;
  });

  noResults.style.display = visible === 0 ? '' : 'none';
  resultCount.textContent = visible + ' conversation' + (visible !== 1 ? 's' : '');
}

// Period toggle buttons
document.querySelectorAll('.period-toggle button').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.period-toggle button').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    mode = btn.dataset.mode;
    offset = 0;
    applyFilters();
  });
});

prevBtn.addEventListener('click', () => { offset--; applyFilters(); });
nextBtn.addEventListener('click', () => { offset++; applyFilters(); });
searchEl.addEventListener('input', applyFilters);

applyFilters();
</script>
</body>
</html>"""

with open(os.path.join(OUT_DIR, "index.html"), "w", encoding="utf-8") as f:
    f.write(INDEX_HTML)

print(f"Generated index.html with {len(conversations)} conversations")

# Generate individual conversation pages
def render_message_content(msg):
    """Render message content to safe HTML string."""
    sender = msg.get("sender", "human")
    parts = []

    content = msg.get("content", [])
    if not content:
        # Fallback to text field
        text = msg.get("text", "")
        if text:
            parts.append(("text", text))
    else:
        for item in content:
            t = item.get("type")
            if t == "text":
                parts.append(("text", item.get("text", "")))
            elif t == "tool_use":
                name = item.get("name", "tool")
                inp = item.get("input", {})
                display = item.get("display_content") or item.get("message", "")
                parts.append(("tool_use", name, inp, display))
            elif t == "tool_result":
                content_items = item.get("content", [])
                text_parts = []
                for ci in content_items:
                    if isinstance(ci, dict) and ci.get("type") == "text":
                        text_parts.append(ci.get("text", ""))
                    elif isinstance(ci, str):
                        text_parts.append(ci)
                parts.append(("tool_result", "\n".join(text_parts)))
            # skip token_budget

    out = []
    for part in parts:
        if part[0] == "text":
            out.append(render_text(part[1]))
        elif part[0] == "tool_use":
            _, name, inp, display = part
            label = html.escape(name)
            if display:
                body = f"<p>{html.escape(str(display))}</p>"
            elif inp:
                try:
                    body = f"<pre><code>{html.escape(json.dumps(inp, indent=2))}</code></pre>"
                except Exception:
                    body = f"<pre><code>{html.escape(str(inp))}</code></pre>"
            else:
                body = ""
            out.append(f'<div class="tool-block"><span class="tool-label">Tool: {label}</span>{body}</div>')
        elif part[0] == "tool_result":
            text = part[1]
            if text.strip():
                out.append(f'<div class="tool-result"><span class="tool-label">Result</span><pre><code>{html.escape(text[:4000])}{"..." if len(text) > 4000 else ""}</code></pre></div>')

    return "".join(out)


def render_text(text):
    """Convert markdown-ish text to HTML. Uses simple escaping + code block handling."""
    if not text:
        return ""

    # We'll render this with marked.js client-side - just escape and wrap
    return f'<div class="md-content" data-md="{html.escape(text, quote=True)}"></div>'


CONV_CSS = f"""
{SHARED_CSS}
header {{ background: var(--surface); border-bottom: 1px solid var(--border); padding: 14px 24px; display: flex; align-items: center; gap: 16px; position: sticky; top: 0; z-index: 10; }}
.back-link {{ color: var(--muted); font-size: 0.88rem; white-space: nowrap; }}
.back-link:hover {{ color: var(--link); }}
header h1 {{ font-size: 1.05rem; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
.conv-meta {{ padding: 12px 24px; background: var(--surface); border-bottom: 1px solid var(--border); color: var(--muted); font-size: 0.83rem; }}
.messages {{ max-width: 820px; margin: 0 auto; padding: 24px; display: flex; flex-direction: column; gap: 16px; }}
.message {{ border-radius: 8px; padding: 16px 20px; }}
.message.human {{ background: var(--human-bg); border: 1px solid var(--human-border); }}
.message.assistant {{ background: var(--ai-bg); border: 1px solid var(--ai-border); }}
.msg-header {{ font-size: 0.78rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: var(--muted); margin-bottom: 10px; }}
.message.human .msg-header {{ color: #3b5bdb; }}
.message.assistant .msg-header {{ color: #0d7761; }}
.md-content p {{ margin: 8px 0; }}
.md-content p:first-child {{ margin-top: 0; }}
.md-content p:last-child {{ margin-bottom: 0; }}
.md-content ul, .md-content ol {{ padding-left: 20px; margin: 8px 0; }}
.md-content h1,.md-content h2,.md-content h3,.md-content h4 {{ margin: 14px 0 6px; font-weight: 700; }}
.md-content h1 {{ font-size: 1.3em; }}
.md-content h2 {{ font-size: 1.15em; }}
.md-content h3 {{ font-size: 1.05em; }}
.md-content blockquote {{ border-left: 3px solid var(--border); padding-left: 12px; color: var(--muted); margin: 8px 0; }}
.tool-block {{ background: var(--tool-bg); border: 1px solid var(--tool-border); border-radius: 6px; padding: 10px 14px; margin: 8px 0; font-size: 0.88em; }}
.tool-result {{ background: var(--tool-bg); border: 1px solid var(--tool-border); border-radius: 6px; padding: 10px 14px; margin: 8px 0; font-size: 0.85em; }}
.tool-label {{ display: inline-block; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: var(--muted); margin-bottom: 6px; }}
.msg-time {{ font-size: 0.75rem; color: var(--muted); margin-top: 10px; }}
"""

for i, conv in enumerate(conversations):
    uuid = conv["uuid"]
    name = html.escape(conv.get("name") or "Untitled")
    created = fmt_datetime(conv.get("created_at", ""))
    updated = fmt_datetime(conv.get("updated_at", ""))
    messages = conv.get("chat_messages", [])

    msg_html_parts = []
    for msg in messages:
        sender = msg.get("sender", "human")
        if sender not in ("human", "assistant"):
            continue
        label = "You" if sender == "human" else "Claude"
        ts = fmt_datetime(msg.get("created_at", ""))
        body = render_message_content(msg)
        if not body.strip():
            continue
        msg_html_parts.append(f"""<div class="message {html.escape(sender)}">
  <div class="msg-header">{label}</div>
  {body}
  <div class="msg-time">{ts}</div>
</div>""")

    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{name} — Claude Conversations</title>
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<style>
{CONV_CSS}
</style>
</head>
<body>
<header>
  <a class="back-link" href="../index.html">← All conversations</a>
  <h1>{name}</h1>
</header>
<div class="conv-meta">Started {created} &middot; Last updated {updated} &middot; {len(messages)} messages</div>
<div class="messages">
{"".join(msg_html_parts)}
</div>
<script>
marked.setOptions({{ breaks: true, gfm: true }});
document.querySelectorAll('.md-content').forEach(el => {{
  const md = el.getAttribute('data-md');
  el.removeAttribute('data-md');
  el.innerHTML = marked.parse(md);
}});
</script>
</body>
</html>"""

    with open(os.path.join(CONV_DIR, f"{uuid}.html"), "w", encoding="utf-8") as f:
        f.write(page)

    if (i + 1) % 50 == 0:
        print(f"  {i+1}/{len(conversations)} conversation pages generated…")

print(f"Done! Open site/index.html in a browser.")

# Generate projects page
proj_cards = []
for proj in projects:
    name = html.escape(proj.get("name") or "Untitled")
    desc = html.escape(proj.get("description") or "")
    created = fmt_date(proj.get("created_at", ""))
    updated = fmt_date(proj.get("updated_at", ""))
    is_private = proj.get("is_private", False)
    is_starter = proj.get("is_starter_project", False)
    docs = proj.get("docs", [])
    creator = proj.get("creator", {}).get("full_name", "")

    tags = []
    if is_private:
        tags.append('<span class="tag tag-private">Private</span>')
    if is_starter:
        tags.append('<span class="tag tag-starter">Starter</span>')
    tags_html = " ".join(tags)

    docs_html = ""
    for doc in docs:
        doc_name = html.escape(doc.get("filename") or "Document")
        doc_content = doc.get("content", "")
        doc_id = doc.get("uuid", "")
        docs_html += f"""<div class="doc-block">
  <div class="doc-name">{doc_name}</div>
  <div class="md-content" data-md="{html.escape(doc_content, quote=True)}"></div>
</div>"""

    proj_cards.append(f"""<div class="proj-card">
  <div class="proj-header">
    <div>
      <div class="proj-name">{name} {tags_html}</div>
      <div class="proj-meta">Created {created} &middot; Updated {updated}{" &middot; by " + html.escape(creator) if creator else ""}</div>
    </div>
  </div>
  {"<p class='proj-desc'>" + desc + "</p>" if desc else ""}
  {docs_html}
</div>""")

projects_page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Projects — Claude Conversations</title>
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<style>
{SHARED_CSS}
header {{ background: var(--surface); border-bottom: 1px solid var(--border); padding: 14px 32px; display: flex; align-items: center; gap: 20px; }}
.back-link {{ color: var(--muted); font-size: 0.88rem; }}
.back-link:hover {{ color: var(--link); }}
header h1 {{ font-size: 1.2rem; font-weight: 700; }}
.content {{ max-width: 860px; margin: 0 auto; padding: 32px; display: flex; flex-direction: column; gap: 24px; }}
.proj-card {{ background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 24px; }}
.proj-header {{ display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 12px; }}
.proj-name {{ font-size: 1.15rem; font-weight: 700; display: flex; align-items: center; gap: 8px; }}
.proj-meta {{ color: var(--muted); font-size: 0.83rem; margin-top: 3px; }}
.proj-desc {{ color: var(--muted); font-size: 0.93rem; margin-bottom: 16px; line-height: 1.55; }}
.tag {{ display: inline-block; font-size: 0.72rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em; padding: 2px 8px; border-radius: 10px; }}
.tag-private {{ background: #fef3c7; color: #92400e; }}
.tag-starter {{ background: #d1fae5; color: #065f46; }}
.doc-block {{ background: var(--bg); border: 1px solid var(--border); border-radius: 6px; padding: 18px 20px; margin-top: 16px; }}
.doc-name {{ font-weight: 600; font-size: 0.9rem; margin-bottom: 12px; color: var(--muted); }}
.md-content p {{ margin: 8px 0; }}
.md-content p:first-child {{ margin-top: 0; }}
.md-content ul, .md-content ol {{ padding-left: 20px; margin: 8px 0; }}
.md-content h1,.md-content h2,.md-content h3 {{ margin: 14px 0 6px; font-weight: 700; }}
.md-content h1 {{ font-size: 1.2em; }}
.md-content h2 {{ font-size: 1.08em; }}
.md-content blockquote {{ border-left: 3px solid var(--border); padding-left: 12px; color: var(--muted); margin: 8px 0; }}
</style>
</head>
<body>
<header>
  <a class="back-link" href="index.html">← All conversations</a>
  <h1>Projects</h1>
</header>
<div class="content">
{"".join(proj_cards)}
</div>
<script>
marked.setOptions({{ breaks: true, gfm: true }});
document.querySelectorAll('.md-content').forEach(el => {{
  const md = el.getAttribute('data-md');
  el.removeAttribute('data-md');
  el.innerHTML = marked.parse(md);
}});
</script>
</body>
</html>"""

with open(os.path.join(OUT_DIR, "projects.html"), "w", encoding="utf-8") as f:
    f.write(projects_page)

print(f"Generated projects.html with {len(projects)} projects.")
