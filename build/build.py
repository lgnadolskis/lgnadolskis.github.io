#!/usr/bin/env python3
"""
Braille Mind static-site builder.

Turns Markdown sources in /content into the published HTML site, and writes a
LinkedIn-ready version of each post into /linkedin.

Usage:
    python build/build.py            # build the whole site
    python build/build.py --push     # build, then git add/commit/push
    python build/build.py --serve    # build, then preview at http://localhost:8000

Write posts as Markdown files in content/posts/ with YAML-ish front matter:

    ---
    title: "My Post Title"
    date: 2025-01-31
    summary: "One-sentence teaser shown in the blog list."
    tags: [Accessibility, Neuroscience]
    subtitle: Optional subtitle shown under the title
    ---

    Your post body in **Markdown**.

Then run the builder. That's the whole workflow.
"""

import json
import os
import re
import sys
import html
import subprocess
import datetime as dt

try:
    import markdown
except ImportError:
    sys.exit("Missing dependency. Run:  pip install -r build/requirements.txt")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT = os.path.join(ROOT, "content")
POSTS_SRC = os.path.join(CONTENT, "posts")
POSTS_OUT = os.path.join(ROOT, "posts")
LINKEDIN_OUT = os.path.join(ROOT, "linkedin")

MD = markdown.Markdown(extensions=["extra", "sane_lists", "smarty"])


# --------------------------------------------------------------------------- #
# Loading & parsing
# --------------------------------------------------------------------------- #
def load_json(name):
    with open(os.path.join(CONTENT, name), encoding="utf-8") as f:
        return json.load(f)


def parse_frontmatter(text):
    """Tiny front-matter parser. Returns (meta dict, body str)."""
    meta, body = {}, text
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            raw = text[3:end].strip()
            body = text[end + 4:].lstrip("\n")
            for line in raw.splitlines():
                if ":" not in line:
                    continue
                key, val = line.split(":", 1)
                key, val = key.strip(), val.strip()
                if val.startswith("[") and val.endswith("]"):
                    val = [v.strip().strip('"\'') for v in val[1:-1].split(",") if v.strip()]
                else:
                    val = val.strip('"\'')
                meta[key] = val
    return meta, body


def slugify(name):
    name = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", name)   # drop date prefix
    name = re.sub(r"\.md$", "", name)
    name = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return name


def fmt_date(value):
    if isinstance(value, str):
        try:
            value = dt.datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            return value
    if hasattr(value, "strftime"):
        return value.strftime("%B ") + str(value.day) + value.strftime(", %Y")
    return str(value)


def load_posts(cfg):
    posts = []
    if not os.path.isdir(POSTS_SRC):
        return posts
    for fn in os.listdir(POSTS_SRC):
        if not fn.endswith(".md"):
            continue
        with open(os.path.join(POSTS_SRC, fn), encoding="utf-8") as f:
            meta, body = parse_frontmatter(f.read())
        MD.reset()
        post = {
            "slug": slugify(fn),
            "title": meta.get("title", fn),
            "subtitle": meta.get("subtitle", ""),
            "date_raw": meta.get("date", ""),
            "date": fmt_date(meta.get("date", "")),
            "summary": meta.get("summary", ""),
            "tags": meta.get("tags", []) if isinstance(meta.get("tags", []), list) else [meta.get("tags")],
            "html": MD.convert(body),
            "md_body": body,
        }
        posts.append(post)
    posts.sort(key=lambda p: str(p["date_raw"]), reverse=True)
    return posts


# --------------------------------------------------------------------------- #
# HTML templates
# --------------------------------------------------------------------------- #
def head(cfg, title, description, rel=""):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta name="description" content="{html.escape(description)}" />
  <meta name="author" content="{html.escape(cfg['author'])}" />
  <meta property="og:title" content="{html.escape(title)}" />
  <meta property="og:description" content="{html.escape(description)}" />
  <meta property="og:type" content="website" />
  <title>{html.escape(title)}</title>
  <link rel="icon" type="image/x-icon" href="{rel}assets/favicon.ico" />
  <link href="{rel}css/styles.css" rel="stylesheet" />
</head>
<body>
  <a class="skip-link" href="#main">Skip to content</a>
"""


def header(cfg, current, rel=""):
    links = ""
    for item in cfg["nav"]:
        href = rel + item["href"]
        aria = ' aria-current="page"' if item["href"] == current else ""
        links += f'        <li><a href="{href}"{aria}>{html.escape(item["label"])}</a></li>\n'
    return f"""  <header class="site-header">
    <nav class="nav" aria-label="Primary">
      <a class="brand" href="{rel}index.html">
        <span class="dots" aria-hidden="true"><i></i><i></i><i></i><i></i><i></i><i></i></span>
        {html.escape(cfg['site_title'])}
      </a>
      <div class="nav-right">
        <button class="nav-toggle" aria-expanded="false" aria-controls="nav-links" aria-label="Toggle menu">☰</button>
        <ul class="nav-links" id="nav-links">
{links}        </ul>
        <button class="theme-toggle" type="button" aria-pressed="false" aria-label="Switch theme">🌙</button>
      </div>
    </nav>
  </header>
"""


def footer(cfg, rel=""):
    social = "".join(
        f'<li><a href="{html.escape(s["href"])}">{html.escape(s["label"])}</a></li>'
        for s in cfg["social"]
    )
    year = dt.date.today().year
    return f"""  <footer class="site-footer">
    <div class="footer-inner">
      <p>&copy; {year} {html.escape(cfg['author'])}. All rights reserved.</p>
      <ul class="footer-links">{social}</ul>
    </div>
  </footer>
  <script src="{rel}js/scripts.js"></script>
</body>
</html>
"""


def tag_html(tags):
    return "".join(f'<span class="tag">{html.escape(t)}</span>' for t in tags if t)


def post_card(post, rel=""):
    return f"""      <li class="post-card">
        <h2><a href="{rel}posts/{post['slug']}.html">{html.escape(post['title'])}</a></h2>
        <p class="post-meta">{html.escape(post['date'])}</p>
        <p>{html.escape(post['summary'])}</p>
        <p>{tag_html(post['tags'])}</p>
        <a class="btn" href="{rel}posts/{post['slug']}.html">Read more <span aria-hidden="true">&rarr;</span></a>
      </li>
"""


# --------------------------------------------------------------------------- #
# Page builders
# --------------------------------------------------------------------------- #
def write(path, content):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("  wrote", os.path.relpath(path, ROOT))


def build_index(cfg, posts):
    recent = "".join(post_card(p) for p in posts[:5]) or "<li><p>No posts yet.</p></li>"
    body = head(cfg, cfg["site_title"], cfg["description"]) + header(cfg, "index.html") + f"""  <section class="hero">
    <div class="container">
      <span class="eyebrow">Braille Mind</span>
      <h1>Welcome to Braille Mind</h1>
      <p>{html.escape(cfg['tagline'])}</p>
    </div>
  </section>
  <main id="main">
    <div class="container">
      <h2 class="visually-hidden">Latest posts</h2>
      <ul class="post-list">
{recent}      </ul>
      <p style="margin-top:2rem"><a class="btn--ghost btn" href="blog.html">See all posts</a></p>
      {subscribe_block(cfg)}
    </div>
  </main>
""" + footer(cfg)
    write(os.path.join(ROOT, "index.html"), body)


def build_blog(cfg, posts):
    cards = "".join(post_card(p) for p in posts) or "<li><p>No posts yet.</p></li>"
    body = head(cfg, f"Blog | {cfg['site_title']}", "All posts on Braille Mind.") + header(cfg, "blog.html") + f"""  <main id="main">
    <div class="container">
      <h1>Blog</h1>
      <p class="lead">Notes on accessibility, neuroscience, and technology.</p>
      <ul class="post-list">
{cards}      </ul>
    </div>
  </main>
""" + footer(cfg)
    write(os.path.join(ROOT, "blog.html"), body)


def build_post(cfg, post):
    desc = post["summary"] or post["title"]
    sub = f'<p class="lead">{html.escape(post["subtitle"])}</p>' if post["subtitle"] else ""
    body = head(cfg, f"{post['title']} | {cfg['site_title']}", desc, rel="../") + header(cfg, "blog.html", rel="../") + f"""  <main id="main">
    <div class="container">
      <a class="back-link" href="../blog.html"><span aria-hidden="true">&larr;</span> All posts</a>
      <article>
        <header class="article-header">
          <p class="post-meta">{html.escape(post['date'])}</p>
          <h1>{html.escape(post['title'])}</h1>
          {sub}
          <p>{tag_html(post['tags'])}</p>
        </header>
        <div class="article-body">
{post['html']}
        </div>
      </article>
    </div>
  </main>
""" + footer(cfg, rel="../")
    write(os.path.join(POSTS_OUT, f"{post['slug']}.html"), body)


def build_about(cfg):
    with open(os.path.join(CONTENT, "pages", "about.md"), encoding="utf-8") as f:
        MD.reset()
        body_html = MD.convert(f.read())
    body = head(cfg, f"About | {cfg['site_title']}", "About Lucas Gil Nadolskis.") + header(cfg, "about.html") + f"""  <main id="main">
    <div class="container">
      <h1>About</h1>
      <div class="prose">
{body_html}
      </div>
    </div>
  </main>
""" + footer(cfg)
    write(os.path.join(ROOT, "about.html"), body)


def build_cv(cfg):
    path = os.path.join(CONTENT, "pages", "cv.md")
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        MD.reset()
        body_html = MD.convert(f.read())
    downloads = (
        '<p class="cv-downloads">'
        '<a class="btn" href="Lucas_Gil_Nadolskis_CV.pdf">Download CV (PDF)</a> '
        '<a class="btn btn--ghost" href="Lucas_Gil_Nadolskis_CV.docx">Download CV (Word)</a>'
        '</p>'
    )
    body = head(cfg, f"CV | {cfg['site_title']}", "Curriculum vitae of Lucas Gil Nadolskis.") + header(cfg, "cv.html") + f"""  <main id="main">
    <div class="container">
      <h1>Curriculum Vitae</h1>
      {downloads}
      <div class="prose">
{body_html}
      </div>
    </div>
  </main>
""" + footer(cfg)
    write(os.path.join(ROOT, "cv.html"), body)


def build_speaking(cfg):
    path = os.path.join(CONTENT, "pages", "speaking.md")
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        MD.reset()
        body_html = MD.convert(f.read())
    body = head(cfg, f"Speaking & Media | {cfg['site_title']}", "Book Lucas Gil Nadolskis for talks, panels, podcasts, and media on bionic vision and accessible science.") + header(cfg, "speaking.html") + f"""  <main id="main">
    <div class="container">
      <h1>Speaking &amp; Media</h1>
      <div class="prose">
{body_html}
      </div>
      {subscribe_block(cfg)}
    </div>
  </main>
""" + footer(cfg)
    write(os.path.join(ROOT, "speaking.html"), body)


def subscribe_block(cfg, rel=""):
    username = cfg.get("buttondown", "")
    if username:
        return f"""<section class="section-block" aria-labelledby="subscribe-heading">
        <h2 id="subscribe-heading">Follow along</h2>
        <p>New posts and appearances, straight to your inbox.</p>
        <form action="https://buttondown.com/api/emails/embed-subscribe/{html.escape(username)}" method="post" target="_blank" class="subscribe-form">
          <label for="bd-email">Email address</label>
          <input type="email" name="email" id="bd-email" required autocomplete="email" placeholder="you@example.com" />
          <button class="btn" type="submit">Subscribe</button>
        </form>
        <p>Prefer a feed reader? <a href="{rel}feed.xml">RSS feed</a>. Powered by Buttondown; unsubscribe anytime.</p>
      </section>"""
    mailto = "mailto:lgnadolskis@gmail.com?subject=Subscribe%20to%20Braille%20Mind"
    return f"""<section class="section-block" aria-labelledby="subscribe-heading">
        <h2 id="subscribe-heading">Follow along</h2>
        <p>New posts and appearances, straight to you: <a class="btn" href="{mailto}">Subscribe by email</a> <a class="btn btn--ghost" href="{rel}feed.xml">RSS feed</a></p>
      </section>"""


def build_feed(cfg, posts):
    items = ""
    for p in posts:
        link = f"{cfg['url'].rstrip('/')}/posts/{p['slug']}.html"
        try:
            pub = dt.datetime.strptime(str(p["date_raw"]), "%Y-%m-%d").strftime("%a, %d %b %Y 00:00:00 GMT")
        except ValueError:
            pub = ""
        items += f"""  <item>
    <title>{html.escape(p['title'])}</title>
    <link>{html.escape(link)}</link>
    <guid>{html.escape(link)}</guid>
    <pubDate>{pub}</pubDate>
    <description>{html.escape(p['summary'])}</description>
  </item>
"""
    feed = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
  <title>{html.escape(cfg['site_title'])}</title>
  <link>{html.escape(cfg['url'])}</link>
  <description>{html.escape(cfg['description'])}</description>
  <language>en-us</language>
{items}</channel>
</rss>
"""
    write(os.path.join(ROOT, "feed.xml"), feed)


def build_contact(cfg):
    links = "".join(
        f'<li><a href="{html.escape(s["href"])}">{html.escape(s["label"])}</a></li>'
        for s in cfg["social"]
    )
    body = head(cfg, f"Contact | {cfg['site_title']}", "Get in touch with Lucas Gil Nadolskis.") + header(cfg, "contact.html") + f"""  <main id="main">
    <div class="container">
      <h1>Contact</h1>
      <p class="lead">Reach out with questions, comments, or collaborations.</p>
      <ul class="link-grid">
{links}
      </ul>
    </div>
  </main>
""" + footer(cfg)
    write(os.path.join(ROOT, "contact.html"), body)


def build_publications(cfg):
    data = load_json("publications.json")
    blocks = ""
    for sec in data["sections"]:
        items = ""
        for it in sec["items"]:
            meta_bits = " · ".join(b for b in [it.get("authors"), it.get("venue"), str(it.get("year") or "")] if b)
            links = it.get("links") or ([{"label": "Link", "url": it["url"]}] if it.get("url") else [])
            primary = links[0]["url"] if links else ""
            link_open = f'<a href="{html.escape(primary)}">' if primary else ""
            link_close = "</a>" if primary else ""
            links_row = ""
            if len(links) >= 2:
                chips = " ".join(
                    f'<a class="pub-link" href="{html.escape(l["url"])}">{html.escape(l["label"])}</a>'
                    for l in links
                )
                links_row = f'\n          <p class="pub-links">{chips}</p>'
            items += f"""        <li class="pub-item">
          <p class="pub-title">{link_open}{html.escape(it['title'])}{link_close}</p>
          <p class="pub-meta">{html.escape(meta_bits)}</p>
          <p class="pub-desc">{html.escape(it.get('desc',''))}</p>{links_row}
        </li>
"""
        blocks += f"""      <section class="section-block">
        <h2>{html.escape(sec['title'])}</h2>
        <ul class="pub-list">
{items}        </ul>
      </section>
"""
    body = head(cfg, f"Publications & Media | {cfg['site_title']}", "Papers, talks, podcasts, and media by Lucas Gil Nadolskis.") + header(cfg, "publications.html") + f"""  <main id="main">
    <div class="container container--wide">
      <h1>Publications &amp; Media</h1>
      <p class="lead">{html.escape(data['intro'])}</p>
{blocks}    </div>
  </main>
""" + footer(cfg)
    write(os.path.join(ROOT, "publications.html"), body)


# --------------------------------------------------------------------------- #
# LinkedIn export
# --------------------------------------------------------------------------- #
def linkedin_text(post, cfg):
    """Plain-text, copy-paste-ready LinkedIn post."""
    body = post["md_body"]
    # strip markdown to readable plain text
    body = re.sub(r"!\[.*?\]\(.*?\)", "", body)                 # images
    body = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r"\1 (\2)", body)  # links -> text (url)
    body = re.sub(r"^#{1,6}\s*", "", body, flags=re.M)          # headings
    body = re.sub(r"\*\*([^*]+)\*\*", r"\1", body)              # bold
    body = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"\1", body)     # italics
    body = re.sub(r"`([^`]+)`", r"\1", body)                    # inline code
    body = re.sub(r"\n{3,}", "\n\n", body).strip()

    url = f"{cfg['url'].rstrip('/')}/posts/{post['slug']}.html"
    tags = " ".join("#" + re.sub(r"[^A-Za-z0-9]", "", t) for t in post["tags"] if t)
    return f"""{post['title']}

{body}

Read the full post: {url}

{tags}
""".strip() + "\n"


def build_linkedin(cfg, posts):
    for p in posts:
        write(os.path.join(LINKEDIN_OUT, f"{p['slug']}.txt"), linkedin_text(p, cfg))


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def git_push():
    print("\nCommitting and pushing to GitHub...")
    ts = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    subprocess.run(["git", "-C", ROOT, "add", "-A"], check=True)
    res = subprocess.run(["git", "-C", ROOT, "commit", "-m", f"Publish update ({ts})"])
    if res.returncode == 0:
        subprocess.run(["git", "-C", ROOT, "push"], check=True)
        print("Pushed. GitHub Pages will update in a minute or two.")
    else:
        print("Nothing to commit.")


def serve():
    import http.server, socketserver, functools
    os.chdir(ROOT)
    handler = functools.partial(http.server.SimpleHTTPRequestHandler)
    with socketserver.TCPServer(("", 8000), handler) as httpd:
        print("\nPreview at http://localhost:8000  (Ctrl+C to stop)")
        httpd.serve_forever()


def main():
    cfg = load_json("config.json")
    os.makedirs(POSTS_OUT, exist_ok=True)
    os.makedirs(LINKEDIN_OUT, exist_ok=True)
    posts = load_posts(cfg)

    print("Building Braille Mind...")
    build_index(cfg, posts)
    build_blog(cfg, posts)
    for p in posts:
        build_post(cfg, p)
    build_about(cfg)
    build_cv(cfg)
    build_speaking(cfg)
    build_contact(cfg)
    build_publications(cfg)
    build_feed(cfg, posts)
    build_linkedin(cfg, posts)
    print(f"\nDone. {len(posts)} post(s) built.")

    if "--push" in sys.argv:
        git_push()
    if "--serve" in sys.argv:
        serve()


if __name__ == "__main__":
    main()
# end of build.py
