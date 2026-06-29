#!/usr/bin/env python3
"""
Publish a Braille Mind post to LinkedIn via the official LinkedIn API.

This uses only the Python standard library (no pip installs).

------------------------------------------------------------------------------
ONE-TIME SETUP
------------------------------------------------------------------------------
1. Go to https://www.linkedin.com/developers/apps and click "Create app".
   - Associate it with a LinkedIn Page (you can make a simple one).
2. On the app's "Products" tab, request and add:
       "Share on LinkedIn"      (gives the w_member_social scope)
       "Sign In with LinkedIn using OpenID Connect"   (gives openid, profile)
   Both are self-serve and usually approved instantly.
3. On the "Auth" tab:
   - Copy your Client ID and Client Secret.
   - Under "Authorized redirect URLs", add EXACTLY:  http://localhost:8765/callback
4. Copy build/linkedin_config.example.json to build/linkedin_config.json and
   fill in client_id and client_secret. (linkedin_config.json is gitignored.)

------------------------------------------------------------------------------
USAGE
------------------------------------------------------------------------------
    python build/publish_linkedin.py --auth
        One-time (and again every ~60 days): opens your browser, you approve,
        and the access token is saved to build/linkedin_token.json.

    python build/publish_linkedin.py <post-slug>
        Posts linkedin/<post-slug>.txt to your LinkedIn feed.
        Example:  python build/publish_linkedin.py navigating-stem-as-a-blind-phd-student

    python build/publish_linkedin.py --latest
        Posts the most recently dated post.

Tip: run `python build/build.py` first so the linkedin/*.txt files are current.
"""

import json
import os
import sys
import time
import webbrowser
import urllib.parse
import urllib.request
import urllib.error
from http.server import BaseHTTPRequestHandler, HTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(ROOT, "build")
CONFIG_PATH = os.path.join(BUILD, "linkedin_config.json")
TOKEN_PATH = os.path.join(BUILD, "linkedin_token.json")
LINKEDIN_DIR = os.path.join(ROOT, "linkedin")

REDIRECT_URI = "http://localhost:8765/callback"
SCOPES = "openid profile w_member_social"
# LinkedIn versions the API by month. Bump this occasionally if you get a
# version error; use a recent YYYYMM value from their changelog.
LINKEDIN_VERSION = "202506"


# --------------------------------------------------------------------------- #
def die(msg):
    sys.exit("ERROR: " + msg)


def load_config():
    if not os.path.exists(CONFIG_PATH):
        die("Missing build/linkedin_config.json. Copy linkedin_config.example.json "
            "to linkedin_config.json and fill in your client_id and client_secret. "
            "See the setup notes at the top of this file.")
    with open(CONFIG_PATH, encoding="utf-8") as f:
        cfg = json.load(f)
    if not cfg.get("client_id") or not cfg.get("client_secret"):
        die("client_id / client_secret not set in build/linkedin_config.json.")
    return cfg


def save_token(data):
    data["obtained_at"] = int(time.time())
    with open(TOKEN_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print("Saved token to build/linkedin_token.json")


def load_token():
    if not os.path.exists(TOKEN_PATH):
        die("No saved token. Run:  python build/publish_linkedin.py --auth")
    with open(TOKEN_PATH, encoding="utf-8") as f:
        return json.load(f)


def http_post_form(url, fields):
    body = urllib.parse.urlencode(fields).encode()
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    with urllib.request.urlopen(req) as r:
        return json.load(r)


def http_get_json(url, token):
    req = urllib.request.Request(url, method="GET")
    req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req) as r:
        return json.load(r)


# --------------------------------------------------------------------------- #
# OAuth (Authorization Code flow with a tiny local callback server)
# --------------------------------------------------------------------------- #
class _CodeHandler(BaseHTTPRequestHandler):
    code = None
    error = None

    def do_GET(self):
        params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        _CodeHandler.code = params.get("code", [None])[0]
        _CodeHandler.error = params.get("error_description", params.get("error", [None]))[0]
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        msg = "Authorization complete. You can close this tab and return to the terminal."
        if _CodeHandler.error:
            msg = "Authorization failed: " + str(_CodeHandler.error)
        self.wfile.write(("<html><body style='font-family:sans-serif;padding:2rem'>"
                          "<h2>Braille Mind → LinkedIn</h2><p>" + msg +
                          "</p></body></html>").encode())

    def log_message(self, *args):
        pass  # silence


def do_auth():
    cfg = load_config()
    auth_url = "https://www.linkedin.com/oauth/v2/authorization?" + urllib.parse.urlencode({
        "response_type": "code",
        "client_id": cfg["client_id"],
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
        "state": "braillemind",
    })
    print("Opening your browser to authorize LinkedIn access...")
    print("If it doesn't open, paste this URL into your browser:\n" + auth_url + "\n")

    server = HTTPServer(("localhost", 8765), _CodeHandler)
    webbrowser.open(auth_url)
    print("Waiting for authorization on " + REDIRECT_URI + " ...")
    while _CodeHandler.code is None and _CodeHandler.error is None:
        server.handle_request()
    if _CodeHandler.error:
        die("Authorization failed: " + str(_CodeHandler.error))

    token = http_post_form("https://www.linkedin.com/oauth/v2/accessToken", {
        "grant_type": "authorization_code",
        "code": _CodeHandler.code,
        "redirect_uri": REDIRECT_URI,
        "client_id": cfg["client_id"],
        "client_secret": cfg["client_secret"],
    })

    # Get the member id (URN) via OpenID Connect userinfo
    info = http_get_json("https://api.linkedin.com/v2/userinfo", token["access_token"])
    token["member_id"] = info["sub"]
    token["member_name"] = info.get("name", "")
    save_token(token)
    print("Authorized as: " + token.get("member_name", "(unknown)"))
    print("You're ready to post. Try:  python build/publish_linkedin.py --latest")


# --------------------------------------------------------------------------- #
# Posting
# --------------------------------------------------------------------------- #
def pick_slug(arg):
    if arg == "--latest":
        files = sorted(f for f in os.listdir(LINKEDIN_DIR) if f.endswith(".txt"))
        if not files:
            die("No linkedin/*.txt files. Run python build/build.py first.")
        # latest by build order isn't reliable; use newest mtime
        files = sorted(files, key=lambda f: os.path.getmtime(os.path.join(LINKEDIN_DIR, f)))
        return files[-1][:-4]
    return arg


def post_to_linkedin(slug):
    token = load_token()
    age_days = (time.time() - token.get("obtained_at", 0)) / 86400
    if age_days > 59:
        die("Your LinkedIn token is likely expired (>60 days). "
            "Re-run:  python build/publish_linkedin.py --auth")

    txt_path = os.path.join(LINKEDIN_DIR, slug + ".txt")
    if not os.path.exists(txt_path):
        die("No such post text: linkedin/" + slug + ".txt  "
            "(run python build/build.py, or check the slug)")
    with open(txt_path, encoding="utf-8") as f:
        commentary = f.read().strip()

    payload = {
        "author": "urn:li:person:" + token["member_id"],
        "commentary": commentary,
        "visibility": "PUBLIC",
        "distribution": {
            "feedDistribution": "MAIN_FEED",
            "targetEntities": [],
            "thirdPartyDistributionChannels": [],
        },
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False,
    }
    req = urllib.request.Request(
        "https://api.linkedin.com/rest/posts",
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
    )
    req.add_header("Authorization", "Bearer " + token["access_token"])
    req.add_header("Content-Type", "application/json")
    req.add_header("X-Restli-Protocol-Version", "2.0.0")
    req.add_header("LinkedIn-Version", LINKEDIN_VERSION)

    try:
        with urllib.request.urlopen(req) as r:
            post_id = r.headers.get("x-restli-id", "(unknown id)")
            print("Posted to LinkedIn. Post id: " + post_id)
            print("View it on your profile: https://www.linkedin.com/in/me/recent-activity/all/")
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")
        die("LinkedIn API error %s:\n%s\n\nIf this mentions an invalid version, bump "
            "LINKEDIN_VERSION near the top of this file to a recent YYYYMM value." % (e.code, detail))


# --------------------------------------------------------------------------- #
def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    arg = sys.argv[1]
    if arg == "--auth":
        do_auth()
    else:
        post_to_linkedin(pick_slug(arg))


if __name__ == "__main__":
    main()
