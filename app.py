from flask import Flask, render_template, request, redirect
import json
import os
import hashlib

app = Flask(__name__)

# ===== محدودیت درخواست دستی (بدون کتابخانه) =====
import time
from flask import request, jsonify

request_log = {}
MAX_REQUESTS = 100
TIME_WINDOW = 60  # ثانیه


# ===== محافظت از API =====
@app.before_request
def protect_api():
    # فقط مسیرهای API رو چک کن
    if not request.path.startswith('/api/'):
        return None
    
    # بررسی User-Agent (مرورگر باید باشه)
    ua = request.headers.get('User-Agent', '').lower()
    blocked_agents = ['curl', 'wget', 'python', 'requests', 'postman']
    if any(agent in ua for agent in blocked_agents):
        return jsonify({"error": "forbidden", "message": "دسترسی غیرمجاز"}), 403
    
    # بررسی Referer (باید از داخل برنامه باشه)
    referer = request.headers.get('Referer', '')
    allowed_hosts = ['127.0.0.1', 'localhost']
    if referer:
        if not any(host in referer for host in allowed_hosts):
            return jsonify({"error": "forbidden", "message": "درخواست از منبع نامعتبر"}), 403
    
    return None


# ===== لاگ درخواست‌ها =====
import os
from datetime import datetime

LOG_FILE = os.path.expanduser("~/access.log")

@app.after_request
def log_request(response):
    # فایل‌های استاتیک رو لاگ نکن
    if request.path.startswith('/static/'):
        return response
    
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ip = request.remote_addr or "unknown"
            method = request.method
            path_req = request.path
            status = response.status_code
            ua = request.headers.get('User-Agent', '')[:50]
            f.write(f"[{timestamp}] {ip} | {method} {path_req} | {status} | {ua}\n")
    except Exception as e:
        pass
    
    return response

@app.before_request
def rate_limit():
    # فقط برای درخواست‌های API اعمال بشه (نه فایل‌های استاتیک)
    if request.path.startswith('/static/'):
        return None
    
    ip = request.remote_addr or 'unknown'
    now = time.time()
    
    if ip not in request_log:
        request_log[ip] = []
    
    # پاک کردن درخواست‌های قدیمی‌تر از ۱ دقیقه
    request_log[ip] = [t for t in request_log[ip] if now - t < TIME_WINDOW]
    
    if len(request_log[ip]) >= MAX_REQUESTS:
        return jsonify({"error": "too_many_requests", "message": "لطفاً کمی صبر کنید"}), 429
    
    request_log[ip].append(now)
    return None




# ===== هدرهای امنیتی =====
from flask import make_response

@app.after_request
def add_security_headers(response):
    # جلوگیری از Clickjacking
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    # جلوگیری از MIME sniffing
    response.headers['X-Content-Type-Options'] = 'nosniff'
    # فعال‌سازی XSS filter در مرورگرهای قدیمی
    response.headers['X-XSS-Protection'] = '1; mode=block'
    # جلوگیری از ارسال Referer به سایت‌های دیگه
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    # CSP: فقط منابع خودی مجاز باشن (با احتیاط برای فونت‌ها)
    response.headers['Content-Security-Policy'] = "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; media-src 'self'"
    return response



SECRET = "zino_secret_2026_hidden_key"

def make_token(genre, novel):
    return hashlib.md5(f"{SECRET}{genre}-{novel}".encode()).hexdigest()[:12]
@app.route("/api/token/<genre>/<int:novel>")
def api_token(genre, novel):
    return {"token": make_token(genre, novel)}


@app.route("/api/content/<token>/<chapter>")
def api_content(token, chapter):
    found = None
    for genre in ["love", "horror", "sad", "comedy", "thriller", "mystery"]:
        for novel in range(20):
            if make_token(genre, novel) == token:
                found = (genre, novel)
                break
        if found:
            break
    
    if not found:
        return {"error": "not_found"}, 404
    
    genre, novel = found
    import gzip
    path = os.path.expanduser(f"~/.zino_secure/{genre}-{novel}.json.gz")
    
    if not os.path.exists(path):
        return {"error": "coming_soon"}, 404
    
    with gzip.open(path, "rt", encoding="utf-8") as f:
        data = json.load(f)
    
    if chapter == "intro":
        return {
            "title": data["title"],
            "intro": data["intro"],
            "total_chapters": len(data["chapters"])
        }
    
    try:
        ch_num = int(chapter)
        ch = data["chapters"][ch_num - 1]
        return {
            "title": data["title"],
            "chapter": ch,
            "total_chapters": len(data["chapters"])
        }
    except (ValueError, IndexError):
        return {"error": "invalid_chapter"}, 404

@app.route("/")
def home():
    if request.cookies.get("zino_visited") == "true":
        return redirect("/home")
    return render_template("splash.html")

@app.route("/set-visited")
def set_visited():
    response = redirect("/home")
    response.set_cookie("zino_visited", "true", max_age=60*60*24*365)
    return response

@app.route("/home")
def real_home():
    return render_template("index.html")

@app.route("/settings")
def settings():
    return render_template("settings.html")

@app.route("/premium")
def premium():
    return render_template("premium.html")

@app.route("/store")
def store():
    return render_template("store.html")

@app.route("/store/profile")
def profile_shop():
    return render_template("profile-shop.html")

@app.route("/store/reading")
def reading_shop():
    return render_template("reading-shop.html")

@app.route("/store/vip")
def vip_shop():
    return render_template("vip-shop.html")

@app.route("/store/gifts")
def gift_shop():
    return render_template("gift-shop.html")

@app.route("/profile")
def profile():
    return render_template("profile.html")

@app.route("/genres")
def genres():
    return render_template("genres.html")

@app.route("/novels")
def novels():
    return render_template("novels.html")

@app.route("/chapters")
def chapters():
    return render_template("chapters.html")

@app.route("/read")
def read():
    return render_template("read.html")

@app.route("/music")
def music():
    return render_template("music.html")

@app.route("/search")
def search():
    return render_template("search.html")

@app.route("/notifications")
def notifications():
    return render_template("notifications.html")

@app.route("/genre-type")
def genre_type():
    return render_template("genre-type.html")

@app.route("/audiobooks")
def audiobooks():
    return render_template("audiobooks.html")

@app.route("/audio-read")
def audio_read():
    return render_template("audio-read.html")

@app.route("/audio-chapters")
def audio_chapters():
    return render_template("audio-chapters.html")

@app.route("/api/notices")
def get_notices():
    import json, os
    path = os.path.expanduser("~/data/notices.json")
    if not os.path.exists(path):
        return jsonify([])
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return jsonify(data)
    except Exception:
        return jsonify([])

if __name__ == "__main__":
    import os
port = int(os.environ.get("PORT", 5000))
app.run(host="0.0.0.0", port=port)
