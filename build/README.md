# Publishing workflow for Braille Mind

This site is fully generated from the `content/` folder. You write Markdown; a
script turns it into the published HTML site **and** a LinkedIn-ready version of
each post. You should rarely need to touch raw HTML.

## One-time setup

Install the one dependency (only needed once per machine):

```bash
pip install -r build/requirements.txt
```

## Writing a new post

1. Create a Markdown file in `content/posts/`. Name it `YYYY-MM-DD-some-title.md`
   (the date prefix sets the order; the rest becomes the page URL/slug).
2. Start the file with this front matter, then write your post in Markdown:

   ```markdown
   ---
   title: "Your Post Title"
   date: 2025-06-28
   summary: "One-sentence teaser shown in the blog list and link previews."
   tags: [Accessibility, Neuroscience]
   subtitle: Optional subtitle shown under the title
   ---

   Your post body. **Bold**, *italic*, [links](https://example.com),
   lists, headings (## like this), quotes, and code all work.
   ```

3. Build the site:

   ```bash
   python build/build.py
   ```

   This regenerates the home page, the blog index, the post page, the
   Publications & Media page, About, and Contact — and writes a LinkedIn draft
   to `linkedin/your-slug.txt`.

4. Preview locally (optional):

   ```bash
   python build/build.py --serve      # then open http://localhost:8000
   ```

5. Publish to the live site (commits and pushes to GitHub Pages):

   ```bash
   python build/build.py --push
   ```

   Your site is live at https://braillemind.com a minute or two later.

## Posting to LinkedIn

You have two options.

**Option A — copy/paste (no setup).** After building, open
`linkedin/<your-post-slug>.txt`. It's plain text with the links and hashtags
already laid out — copy it, paste into LinkedIn, post.

**Option B — one-command posting via the LinkedIn API.** A one-time setup, then
publishing is a single command.

1. Create a LinkedIn app at https://www.linkedin.com/developers/apps and add the
   "Share on LinkedIn" and "Sign In with LinkedIn using OpenID Connect"
   products (both self-serve). In the app's **Auth** tab, add the redirect URL
   `http://localhost:8765/callback` and copy your Client ID and Secret.
2. Copy `build/linkedin_config.example.json` to `build/linkedin_config.json`
   and paste in your client_id and client_secret. (This file is gitignored, so
   your secret is never committed.)
3. Authorize once (re-do this roughly every 60 days when the token expires):

   ```bash
   python build/publish_linkedin.py --auth
   ```

   Your browser opens, you approve, and a token is saved locally.
4. Publish a post to your LinkedIn feed:

   ```bash
   python build/build.py                                   # refresh the text
   python build/publish_linkedin.py <your-post-slug>       # or: --latest
   ```

Full setup details are in the comments at the top of `build/publish_linkedin.py`.
LinkedIn versions its API by month; if you ever get a version error, bump the
`LINKEDIN_VERSION` value near the top of that file to a recent `YYYYMM`.

## Editing other pages

- **About text:** `content/pages/about.md`
- **Publications, talks, podcasts, media:** `content/publications.json`
- **Site title, navigation, social links:** `content/config.json`

Edit those, run `python build/build.py`, and everything updates.

## What's generated vs. what you edit

| You edit (source)              | Generated (don't edit by hand)        |
|--------------------------------|----------------------------------------|
| `content/posts/*.md`           | `posts/*.html`, `blog.html`, `index.html` |
| `content/pages/about.md`       | `about.html`                           |
| `content/publications.json`    | `publications.html`                    |
| `content/config.json`          | navigation + footer on every page      |
| —                              | `linkedin/*.txt`                       |
