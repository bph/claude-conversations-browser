#!/usr/bin/env python3
import json
import os
import sys
import html
from datetime import datetime

# Use the canonical build_index from serve.py so both scripts produce identical index HTML
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from serve import build_index

TOOL_RESULT_MAX_CHARS = 4000

DATA_FILE = "conversations.json"
PROJECTS_FILE = "projects.json"
DELETED_FILE = "deleted.json"
OUT_DIR = "site"
CONV_DIR = os.path.join(OUT_DIR, "c")

os.makedirs(CONV_DIR, exist_ok=True)

try:
    with open(DATA_FILE, encoding="utf-8") as f:
        conversations = json.load(f)
except FileNotFoundError:
    sys.exit(f"Error: {DATA_FILE} not found.\nExport your Claude data at claude.ai/settings and place the file here.")
except json.JSONDecodeError as e:
    sys.exit(f"Error: {DATA_FILE} is not valid JSON: {e}")

try:
    with open(PROJECTS_FILE, encoding="utf-8") as f:
        projects = json.load(f)
except FileNotFoundError:
    sys.exit(f"Error: {PROJECTS_FILE} not found.\nExport your Claude data at claude.ai/settings and place the file here.")
except json.JSONDecodeError as e:
    sys.exit(f"Error: {PROJECTS_FILE} is not valid JSON: {e}")

# Filter out previously deleted conversations
if os.path.exists(DELETED_FILE):
    with open(DELETED_FILE, encoding="utf-8") as f:
        deleted = set(json.load(f))
    before = len(conversations)
    conversations = [c for c in conversations if c["uuid"] not in deleted]
    if before != len(conversations):
        print(f"Skipped {before - len(conversations)} previously deleted conversations")

# Sort newest first
conversations.sort(key=lambda c: c.get("updated_at", ""), reverse=True)


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

# Build and write index using the same function as serve.py
index_html = build_index(conversations, projects)
with open(os.path.join(OUT_DIR, "index.html"), "w", encoding="utf-8") as f:
    f.write(index_html)
print(f"Generated index.html with {len(conversations)} conversations")


# --- Individual conversation pages ---

def render_message_content(msg):
    parts = []
    content = msg.get("content", [])
    if not content:
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
                truncated = text[:TOOL_RESULT_MAX_CHARS]
                if len(text) > TOOL_RESULT_MAX_CHARS:
                    note = f' <em style="font-weight:normal;text-transform:none">(showing {TOOL_RESULT_MAX_CHARS:,} of {len(text):,} characters)</em>'
                else:
                    note = ""
                out.append(
                    f'<div class="tool-result">'
                    f'<span class="tool-label">Result{note}</span>'
                    f'<pre><code>{html.escape(truncated)}</code></pre>'
                    f'</div>'
                )
    return "".join(out)


def render_text(text):
    if not text:
        return ""
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

print(f"Done! Run: python3 serve.py")


# --- Projects page ---

def fmt_date(iso):
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.strftime("%b %d, %Y")
    except Exception:
        return iso or ""

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
