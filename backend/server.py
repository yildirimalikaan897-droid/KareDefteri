#!/usr/bin/env python3
"""
KareDefteri Backend Server
A REST API server built with Python's http.server
"""

import json
import os
import sys
import re
import uuid
import time
import random
import string
import hashlib
import mimetypes
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timedelta
from io import BytesIO
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import bcrypt
import jwt

from database import get_db, init_db

# Config
SECRET_KEY = 'karedefteri-secret-key-2026'
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), 'uploads')
POSTS_DIR = os.path.join(UPLOAD_DIR, 'posts')
STORIES_DIR = os.path.join(UPLOAD_DIR, 'stories')
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), '..', 'frontend')
HOST = '0.0.0.0'
PORT = int(os.environ.get('PORT', 8000))

# SMTP Email Config
SMTP_HOST = os.environ.get('SMTP_HOST', 'smtp.gmail.com')
SMTP_PORT = int(os.environ.get('SMTP_PORT', 587))
SMTP_USER = os.environ.get('SMTP_USER', '')
SMTP_PASS = os.environ.get('SMTP_PASS', '')
SMTP_FROM = os.environ.get('SMTP_FROM', SMTP_USER)

os.makedirs(POSTS_DIR, exist_ok=True)
os.makedirs(STORIES_DIR, exist_ok=True)

# ---- Helper Functions ----

def generate_token(user_id, role):
    payload = {
        'user_id': user_id,
        'role': role,
        'exp': datetime.utcnow() + timedelta(days=7),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, SECRET_KEY, algorithm='HS256')

def verify_token(token):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def generate_verification_code():
    return ''.join(random.choices(string.digits, k=6))


def send_verification_email(email, code, username):
    """Send verification code via SMTP email"""
    if not SMTP_USER or not SMTP_PASS:
        print(f"[VERIFICATION] SMTP not configured. User: {username}, Email: {email}, Code: {code}")
        return False
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = 'KareDefteri - E-posta Dogrulama Kodu'
        msg['From'] = SMTP_FROM
        msg['To'] = email
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; background-color: #f4f4f4; padding: 20px;">
            <div style="max-width: 500px; margin: 0 auto; background: white; border-radius: 12px; padding: 30px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                <h2 style="color: #e91e63; text-align: center;">KareDefteri</h2>
                <p>Merhaba <strong>{username}</strong>,</p>
                <p>Hesabinizi dogrulamak icin asagidaki kodu kullanin:</p>
                <div style="text-align: center; margin: 25px 0;">
                    <span style="font-size: 32px; font-weight: bold; letter-spacing: 8px; color: #333; background: #f0f0f0; padding: 15px 30px; border-radius: 8px; display: inline-block;">{code}</span>
                </div>
                <p style="color: #666; font-size: 14px;">Bu kod 15 dakika icinde gecerliligini yitirecektir.</p>
                <p style="color: #999; font-size: 12px;">Bu e-postayi siz talep etmediyseniz, lutfen dikkate almayin.</p>
            </div>
        </body>
        </html>
        """
        msg.attach(MIMEText(html_body, 'html'))
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_FROM, email, msg.as_string())
        print(f"[VERIFICATION] Email sent to {email} for user {username}")
        return True
    except Exception as e:
        print(f"[VERIFICATION ERROR] Failed to send email to {email}: {e}")
        return False

def json_response(handler, data, status=200):
    handler.send_response(status)
    handler.send_header('Content-Type', 'application/json')
    handler.send_header('Access-Control-Allow-Origin', '*')
    handler.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
    handler.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
    handler.end_headers()
    handler.wfile.write(json.dumps(data, default=str).encode())

def parse_multipart(handler):
    content_type = handler.headers.get('Content-Type', '')
    if 'multipart/form-data' not in content_type:
        return {}, {}

    boundary = content_type.split('boundary=')[1].strip()
    content_length = int(handler.headers.get('Content-Length', 0))
    body = handler.rfile.read(content_length)

    fields = {}
    files = {}

    parts = body.split(('--' + boundary).encode())
    for part in parts:
        if part in (b'', b'--\r\n', b'--'):
            continue

        if b'\r\n\r\n' not in part:
            continue

        header_data, content = part.split(b'\r\n\r\n', 1)
        if content.endswith(b'\r\n'):
            content = content[:-2]

        header_str = header_data.decode('utf-8', errors='ignore')

        name_match = re.search(r'name="([^"]+)"', header_str)
        filename_match = re.search(r'filename="([^"]+)"', header_str)

        if name_match:
            field_name = name_match.group(1)
            if filename_match:
                files[field_name] = {
                    'filename': filename_match.group(1),
                    'data': content,
                    'content_type': 'image/jpeg'
                }
            else:
                fields[field_name] = content.decode('utf-8', errors='ignore')

    return fields, files

def get_json_body(handler):
    content_length = int(handler.headers.get('Content-Length', 0))
    if content_length == 0:
        return {}
    body = handler.rfile.read(content_length)
    try:
        return json.loads(body.decode())
    except:
        return {}

def get_current_user(handler):
    auth = handler.headers.get('Authorization', '')
    if auth.startswith('Bearer '):
        token = auth[7:]
        payload = verify_token(token)
        if payload:
            db = get_db()
            user = db.execute("SELECT * FROM users WHERE id = ? AND is_banned = 0", (payload['user_id'],)).fetchone()
            db.close()
            if user:
                return dict(user)
    return None

def require_auth(handler):
    user = get_current_user(handler)
    if not user:
        json_response(handler, {'error': 'Yetkilendirme gerekli'}, 401)
        return None
    return user

def require_admin(handler):
    user = require_auth(handler)
    if user and user['role'] != 'admin':
        json_response(handler, {'error': 'Admin yetkisi gerekli'}, 403)
        return None
    return user

def save_uploaded_file(file_data, directory):
    ext = os.path.splitext(file_data['filename'])[1].lower()
    if ext not in ('.jpg', '.jpeg', '.png', '.gif', '.webp'):
        ext = '.jpg'
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(directory, filename)
    with open(filepath, 'wb') as f:
        f.write(file_data['data'])
    return filename


# ---- Request Handler ----

class KareDefteriHandler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()

    def log_message(self, format, *args):
        sys.stderr.write(f"[{datetime.now().strftime('%H:%M:%S')}] {format % args}\n")

    # ---- ROUTING ----

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)

        # API Routes
        if path == '/api/auth/me':
            return self.handle_me()
        elif path == '/api/users/search':
            return self.handle_search_users(params)
        elif re.match(r'^/api/users/(\d+)$', path):
            uid = int(re.match(r'^/api/users/(\d+)$', path).group(1))
            return self.handle_get_user(uid)
        elif re.match(r'^/api/users/(\d+)/posts$', path):
            uid = int(re.match(r'^/api/users/(\d+)/posts$', path).group(1))
            return self.handle_get_user_posts(uid, params)
        elif re.match(r'^/api/users/(\d+)/followers$', path):
            uid = int(re.match(r'^/api/users/(\d+)/followers$', path).group(1))
            return self.handle_get_followers(uid)
        elif re.match(r'^/api/users/(\d+)/following$', path):
            uid = int(re.match(r'^/api/users/(\d+)/following$', path).group(1))
            return self.handle_get_following(uid)
        elif path == '/api/feed':
            return self.handle_get_feed(params)
        elif re.match(r'^/api/posts/(\d+)$', path):
            pid = int(re.match(r'^/api/posts/(\d+)$', path).group(1))
            return self.handle_get_post(pid)
        elif path == '/api/stories/feed':
            return self.handle_get_stories_feed()
        elif path == '/api/admin/stats':
            return self.handle_admin_stats()
        elif path == '/api/admin/reports':
            return self.handle_admin_get_reports(params)
        elif path == '/api/admin/users':
            return self.handle_admin_get_users(params)
        # Serve uploaded files
        elif path.startswith('/uploads/'):
            return self.serve_upload(path)
        # Serve frontend
        else:
            return self.serve_frontend(path)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == '/api/auth/register':
            return self.handle_register()
        elif path == '/api/auth/verify':
            return self.handle_verify_email()
        elif path == '/api/auth/login':
            return self.handle_login()
        elif path == '/api/auth/resend-code':
            return self.handle_resend_code()
        elif path == '/api/posts':
            return self.handle_create_post()
        elif re.match(r'^/api/posts/(\d+)/react$', path):
            pid = int(re.match(r'^/api/posts/(\d+)/react$', path).group(1))
            return self.handle_react_post(pid)
        elif re.match(r'^/api/posts/(\d+)/report$', path):
            pid = int(re.match(r'^/api/posts/(\d+)/report$', path).group(1))
            return self.handle_report_post(pid)
        elif re.match(r'^/api/users/(\d+)/follow$', path):
            uid = int(re.match(r'^/api/users/(\d+)/follow$', path).group(1))
            return self.handle_follow(uid)
        elif path == '/api/stories':
            return self.handle_create_story()
        elif re.match(r'^/api/stories/(\d+)/view$', path):
            sid = int(re.match(r'^/api/stories/(\d+)/view$', path).group(1))
            return self.handle_view_story(sid)
        elif re.match(r'^/api/admin/posts/(\d+)/toggle$', path):
            pid = int(re.match(r'^/api/admin/posts/(\d+)/toggle$', path).group(1))
            return self.handle_admin_toggle_post(pid)
        elif re.match(r'^/api/admin/users/(\d+)/ban$', path):
            uid = int(re.match(r'^/api/admin/users/(\d+)/ban$', path).group(1))
            return self.handle_admin_ban_user(uid)
        elif re.match(r'^/api/admin/users/(\d+)/unban$', path):
            uid = int(re.match(r'^/api/admin/users/(\d+)/unban$', path).group(1))
            return self.handle_admin_unban_user(uid)
        elif re.match(r'^/api/admin/reports/(\d+)/review$', path):
            rid = int(re.match(r'^/api/admin/reports/(\d+)/review$', path).group(1))
            return self.handle_admin_review_report(rid)

        json_response(self, {'error': 'Not found'}, 404)

    def do_DELETE(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if re.match(r'^/api/posts/(\d+)$', path):
            pid = int(re.match(r'^/api/posts/(\d+)$', path).group(1))
            return self.handle_delete_post(pid)
        elif re.match(r'^/api/users/(\d+)/follow$', path):
            uid = int(re.match(r'^/api/users/(\d+)/follow$', path).group(1))
            return self.handle_unfollow(uid)
        elif re.match(r'^/api/posts/(\d+)/react$', path):
            pid = int(re.match(r'^/api/posts/(\d+)/react$', path).group(1))
            return self.handle_remove_reaction(pid)

        json_response(self, {'error': 'Not found'}, 404)

    # ---- AUTH HANDLERS ----

    def handle_register(self):
        data = get_json_body(self)
        username = data.get('username', '').strip()
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        country = data.get('country', 'TR')

        if not username or not email or not password:
            return json_response(self, {'error': 'Tüm alanlar zorunludur'}, 400)

        if len(username) < 3 or len(username) > 30:
            return json_response(self, {'error': 'Kullanıcı adı 3-30 karakter olmalıdır'}, 400)

        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            return json_response(self, {'error': 'Kullanıcı adı sadece harf, rakam ve alt çizgi içerebilir'}, 400)

        if not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
            return json_response(self, {'error': 'Geçerli bir e-posta adresi giriniz'}, 400)

        if len(password) < 6:
            return json_response(self, {'error': 'Şifre en az 6 karakter olmalıdır'}, 400)

        db = get_db()
        existing = db.execute("SELECT id FROM users WHERE username = ? OR email = ?", (username, email)).fetchone()
        if existing:
            db.close()
            return json_response(self, {'error': 'Bu kullanıcı adı veya e-posta zaten kullanımda'}, 409)

        pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        cursor = db.execute(
            "INSERT INTO users (username, email, password_hash, country) VALUES (?, ?, ?, ?)",
            (username, email, pw_hash, country)
        )
        user_id = cursor.lastrowid

        # Generate verification code
        code = generate_verification_code()
        expires = (datetime.utcnow() + timedelta(minutes=15)).isoformat()
        db.execute(
            "INSERT INTO verification_codes (user_id, code, expires_at) VALUES (?, ?, ?)",
            (user_id, code, expires)
        )

        db.commit()
        db.close()

        # Send verification email
        send_verification_email(email, code, username)

        return json_response(self, {
            'message': 'Kayıt başarılı! Doğrulama kodu e-posta adresinize gönderildi.',
            'user_id': user_id,
            'verification_code': code  # DEV only - remove in production
        }, 201)

    def handle_verify_email(self):
        data = get_json_body(self)
        email = data.get('email', '').strip().lower()
        code = data.get('code', '').strip()

        if not email or not code:
            return json_response(self, {'error': 'E-posta ve doğrulama kodu gereklidir'}, 400)

        db = get_db()
        user = db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if not user:
            db.close()
            return json_response(self, {'error': 'Kullanıcı bulunamadı'}, 404)

        vc = db.execute("""
            SELECT * FROM verification_codes
            WHERE user_id = ? AND code = ? AND used = 0
            ORDER BY created_at DESC LIMIT 1
        """, (user['id'], code)).fetchone()

        if not vc:
            db.close()
            return json_response(self, {'error': 'Geçersiz doğrulama kodu'}, 400)

        if datetime.fromisoformat(vc['expires_at']) < datetime.utcnow():
            db.close()
            return json_response(self, {'error': 'Doğrulama kodunun süresi dolmuş'}, 400)

        db.execute("UPDATE verification_codes SET used = 1 WHERE id = ?", (vc['id'],))
        db.execute("UPDATE users SET is_active = 1 WHERE id = ?", (user['id'],))
        db.commit()
        db.close()

        return json_response(self, {'message': 'E-posta doğrulaması başarılı! Artık giriş yapabilirsiniz.'})

    def handle_login(self):
        data = get_json_body(self)
        login_id = data.get('login', '').strip()
        password = data.get('password', '')

        if not login_id or not password:
            return json_response(self, {'error': 'Kullanıcı adı/e-posta ve şifre gereklidir'}, 400)

        db = get_db()
        user = db.execute(
            "SELECT * FROM users WHERE (username = ? OR email = ?)",
            (login_id, login_id.lower())
        ).fetchone()

        if not user:
            db.close()
            return json_response(self, {'error': 'Geçersiz kullanıcı adı veya şifre'}, 401)

        user = dict(user)

        if not bcrypt.checkpw(password.encode(), user['password_hash'].encode()):
            db.close()
            return json_response(self, {'error': 'Geçersiz kullanıcı adı veya şifre'}, 401)

        if user['is_banned']:
            db.close()
            return json_response(self, {'error': 'Hesabınız yasaklanmıştır. Sebep: ' + (user['ban_reason'] or 'Belirtilmemiş')}, 403)

        if not user['is_active']:
            db.close()
            return json_response(self, {'error': 'Hesabınız henüz doğrulanmamış. Lütfen e-posta doğrulamasını tamamlayın.', 'needs_verification': True, 'email': user['email']}, 403)

        db.close()
        token = generate_token(user['id'], user['role'])

        return json_response(self, {
            'message': 'Giriş başarılı!',
            'token': token,
            'user': {
                'id': user['id'],
                'username': user['username'],
                'email': user['email'],
                'role': user['role'],
                'profile_pic': user['profile_pic'],
                'bio': user['bio'],
                'country': user['country']
            }
        })

    def handle_resend_code(self):
        data = get_json_body(self)
        email = data.get('email', '').strip().lower()

        if not email:
            return json_response(self, {'error': 'E-posta gereklidir'}, 400)

        db = get_db()
        user = db.execute("SELECT id, username FROM users WHERE email = ? AND is_active = 0", (email,)).fetchone()
        if not user:
            db.close()
            return json_response(self, {'error': 'Kullanıcı bulunamadı veya zaten doğrulanmış'}, 404)

        code = generate_verification_code()
        expires = (datetime.utcnow() + timedelta(minutes=15)).isoformat()
        db.execute("UPDATE verification_codes SET used = 1 WHERE user_id = ?", (user['id'],))
        db.execute(
            "INSERT INTO verification_codes (user_id, code, expires_at) VALUES (?, ?, ?)",
            (user['id'], code, expires)
        )
        db.commit()
        db.close()

        send_verification_email(email, code, user['username'])

        return json_response(self, {
            'message': 'Yeni doğrulama kodu gönderildi.',
            'verification_code': code  # DEV only
        })

    def handle_me(self):
        user = require_auth(self)
        if not user:
            return

        db = get_db()
        follower_count = db.execute("SELECT COUNT(*) as c FROM follows WHERE following_id = ?", (user['id'],)).fetchone()['c']
        following_count = db.execute("SELECT COUNT(*) as c FROM follows WHERE follower_id = ?", (user['id'],)).fetchone()['c']
        post_count = db.execute("SELECT COUNT(*) as c FROM posts WHERE user_id = ? AND is_visible = 1", (user['id'],)).fetchone()['c']
        db.close()

        return json_response(self, {
            'user': {
                'id': user['id'],
                'username': user['username'],
                'email': user['email'],
                'role': user['role'],
                'profile_pic': user['profile_pic'],
                'bio': user['bio'],
                'country': user['country'],
                'created_at': user['created_at'],
                'followers': follower_count,
                'following': following_count,
                'posts': post_count
            }
        })

    # ---- USER HANDLERS ----

    def handle_search_users(self, params):
        user = require_auth(self)
        if not user:
            return

        q = params.get('q', [''])[0]
        if len(q) < 2:
            return json_response(self, {'users': []})

        db = get_db()
        users = db.execute("""
            SELECT id, username, profile_pic, bio FROM users
            WHERE (username LIKE ? OR email LIKE ?) AND is_active = 1 AND is_banned = 0
            LIMIT 20
        """, (f'%{q}%', f'%{q}%')).fetchall()
        db.close()

        return json_response(self, {'users': [dict(u) for u in users]})

    def handle_get_user(self, uid):
        user = require_auth(self)
        if not user:
            return

        db = get_db()
        target = db.execute("SELECT id, username, profile_pic, bio, country, created_at FROM users WHERE id = ? AND is_active = 1", (uid,)).fetchone()
        if not target:
            db.close()
            return json_response(self, {'error': 'Kullanıcı bulunamadı'}, 404)

        target = dict(target)
        target['followers'] = db.execute("SELECT COUNT(*) as c FROM follows WHERE following_id = ?", (uid,)).fetchone()['c']
        target['following'] = db.execute("SELECT COUNT(*) as c FROM follows WHERE follower_id = ?", (uid,)).fetchone()['c']
        target['posts'] = db.execute("SELECT COUNT(*) as c FROM posts WHERE user_id = ? AND is_visible = 1", (uid,)).fetchone()['c']
        target['is_following'] = db.execute("SELECT id FROM follows WHERE follower_id = ? AND following_id = ?", (user['id'], uid)).fetchone() is not None
        db.close()

        return json_response(self, {'user': target})

    def handle_get_user_posts(self, uid, params):
        user = require_auth(self)
        if not user:
            return

        page = int(params.get('page', ['1'])[0])
        limit = 12
        offset = (page - 1) * limit

        db = get_db()
        posts = db.execute("""
            SELECT p.*, u.username, u.profile_pic,
                (SELECT COUNT(*) FROM reactions WHERE post_id = p.id AND reaction_type = 'like') as likes,
                (SELECT COUNT(*) FROM reactions WHERE post_id = p.id AND reaction_type = 'dislike') as dislikes,
                (SELECT reaction_type FROM reactions WHERE post_id = p.id AND user_id = ?) as my_reaction
            FROM posts p JOIN users u ON p.user_id = u.id
            WHERE p.user_id = ? AND p.is_visible = 1
            ORDER BY p.created_at DESC LIMIT ? OFFSET ?
        """, (user['id'], uid, limit, offset)).fetchall()

        total = db.execute("SELECT COUNT(*) as c FROM posts WHERE user_id = ? AND is_visible = 1", (uid,)).fetchone()['c']
        db.close()

        return json_response(self, {
            'posts': [dict(p) for p in posts],
            'total': total,
            'page': page,
            'pages': (total + limit - 1) // limit
        })

    # ---- FOLLOW HANDLERS ----

    def handle_follow(self, uid):
        user = require_auth(self)
        if not user:
            return

        if user['id'] == uid:
            return json_response(self, {'error': 'Kendinizi takip edemezsiniz'}, 400)

        db = get_db()
        target = db.execute("SELECT id FROM users WHERE id = ? AND is_active = 1 AND is_banned = 0", (uid,)).fetchone()
        if not target:
            db.close()
            return json_response(self, {'error': 'Kullanıcı bulunamadı'}, 404)

        existing = db.execute("SELECT id FROM follows WHERE follower_id = ? AND following_id = ?", (user['id'], uid)).fetchone()
        if existing:
            db.close()
            return json_response(self, {'error': 'Zaten takip ediyorsunuz'}, 409)

        db.execute("INSERT INTO follows (follower_id, following_id) VALUES (?, ?)", (user['id'], uid))
        db.commit()
        db.close()

        return json_response(self, {'message': 'Takip edildi'}, 201)

    def handle_unfollow(self, uid):
        user = require_auth(self)
        if not user:
            return

        db = get_db()
        db.execute("DELETE FROM follows WHERE follower_id = ? AND following_id = ?", (user['id'], uid))
        db.commit()
        db.close()

        return json_response(self, {'message': 'Takipten çıkıldı'})

    def handle_get_followers(self, uid):
        user = require_auth(self)
        if not user:
            return

        db = get_db()
        followers = db.execute("""
            SELECT u.id, u.username, u.profile_pic, u.bio,
                (SELECT id FROM follows WHERE follower_id = ? AND following_id = u.id) as im_following
            FROM follows f JOIN users u ON f.follower_id = u.id
            WHERE f.following_id = ? AND u.is_active = 1
            ORDER BY f.created_at DESC
        """, (user['id'], uid)).fetchall()
        db.close()

        result = [dict(f) for f in followers]
        for r in result:
            r['im_following'] = r['im_following'] is not None

        return json_response(self, {'followers': result})

    def handle_get_following(self, uid):
        user = require_auth(self)
        if not user:
            return

        db = get_db()
        following = db.execute("""
            SELECT u.id, u.username, u.profile_pic, u.bio,
                (SELECT id FROM follows WHERE follower_id = ? AND following_id = u.id) as im_following
            FROM follows f JOIN users u ON f.following_id = u.id
            WHERE f.follower_id = ? AND u.is_active = 1
            ORDER BY f.created_at DESC
        """, (user['id'], uid)).fetchall()
        db.close()

        result = [dict(f) for f in following]
        for r in result:
            r['im_following'] = r['im_following'] is not None

        return json_response(self, {'following': result})

    # ---- POST HANDLERS ----

    def handle_create_post(self):
        user = require_auth(self)
        if not user:
            return

        fields, files = parse_multipart(self)

        if 'image' not in files:
            return json_response(self, {'error': 'Görsel yüklenmedi'}, 400)

        filename = save_uploaded_file(files['image'], POSTS_DIR)
        caption = fields.get('caption', '')

        db = get_db()
        cursor = db.execute(
            "INSERT INTO posts (user_id, image_path, caption) VALUES (?, ?, ?)",
            (user['id'], f'/uploads/posts/{filename}', caption)
        )
        post_id = cursor.lastrowid
        db.commit()
        db.close()

        return json_response(self, {
            'message': 'Gönderi oluşturuldu!',
            'post_id': post_id,
            'image_path': f'/uploads/posts/{filename}'
        }, 201)

    def handle_get_post(self, pid):
        user = require_auth(self)
        if not user:
            return

        db = get_db()
        post = db.execute("""
            SELECT p.*, u.username, u.profile_pic,
                (SELECT COUNT(*) FROM reactions WHERE post_id = p.id AND reaction_type = 'like') as likes,
                (SELECT COUNT(*) FROM reactions WHERE post_id = p.id AND reaction_type = 'dislike') as dislikes,
                (SELECT reaction_type FROM reactions WHERE post_id = p.id AND user_id = ?) as my_reaction
            FROM posts p JOIN users u ON p.user_id = u.id
            WHERE p.id = ? AND p.is_visible = 1
        """, (user['id'], pid)).fetchone()
        db.close()

        if not post:
            return json_response(self, {'error': 'Gönderi bulunamadı'}, 404)

        return json_response(self, {'post': dict(post)})

    def handle_delete_post(self, pid):
        user = require_auth(self)
        if not user:
            return

        db = get_db()
        post = db.execute("SELECT * FROM posts WHERE id = ?", (pid,)).fetchone()
        if not post:
            db.close()
            return json_response(self, {'error': 'Gönderi bulunamadı'}, 404)

        if post['user_id'] != user['id'] and user['role'] != 'admin':
            db.close()
            return json_response(self, {'error': 'Bu gönderiyi silme yetkiniz yok'}, 403)

        db.execute("DELETE FROM posts WHERE id = ?", (pid,))
        db.commit()
        db.close()

        return json_response(self, {'message': 'Gönderi silindi'})

    def handle_get_feed(self, params):
        user = require_auth(self)
        if not user:
            return

        page = int(params.get('page', ['1'])[0])
        limit = 12
        offset = (page - 1) * limit

        db = get_db()
        posts = db.execute("""
            SELECT p.*, u.username, u.profile_pic,
                (SELECT COUNT(*) FROM reactions WHERE post_id = p.id AND reaction_type = 'like') as likes,
                (SELECT COUNT(*) FROM reactions WHERE post_id = p.id AND reaction_type = 'dislike') as dislikes,
                (SELECT reaction_type FROM reactions WHERE post_id = p.id AND user_id = ?) as my_reaction
            FROM posts p
            JOIN users u ON p.user_id = u.id
            WHERE p.user_id IN (SELECT following_id FROM follows WHERE follower_id = ?)
                AND p.is_visible = 1
            ORDER BY p.created_at DESC
            LIMIT ? OFFSET ?
        """, (user['id'], user['id'], limit, offset)).fetchall()

        total = db.execute("""
            SELECT COUNT(*) as c FROM posts
            WHERE user_id IN (SELECT following_id FROM follows WHERE follower_id = ?)
                AND is_visible = 1
        """, (user['id'],)).fetchone()['c']
        db.close()

        return json_response(self, {
            'posts': [dict(p) for p in posts],
            'total': total,
            'page': page,
            'pages': max(1, (total + limit - 1) // limit)
        })

    # ---- REACTION HANDLERS ----

    def handle_react_post(self, pid):
        user = require_auth(self)
        if not user:
            return

        data = get_json_body(self)
        reaction = data.get('reaction')
        if reaction not in ('like', 'dislike'):
            return json_response(self, {'error': 'Geçersiz reaksiyon tipi'}, 400)

        db = get_db()
        post = db.execute("SELECT id FROM posts WHERE id = ? AND is_visible = 1", (pid,)).fetchone()
        if not post:
            db.close()
            return json_response(self, {'error': 'Gönderi bulunamadı'}, 404)

        existing = db.execute("SELECT * FROM reactions WHERE user_id = ? AND post_id = ?", (user['id'], pid)).fetchone()
        if existing:
            if existing['reaction_type'] == reaction:
                # Same reaction - remove it (toggle off)
                db.execute("DELETE FROM reactions WHERE id = ?", (existing['id'],))
            else:
                # Different reaction - update it
                db.execute("UPDATE reactions SET reaction_type = ? WHERE id = ?", (reaction, existing['id']))
        else:
            db.execute("INSERT INTO reactions (user_id, post_id, reaction_type) VALUES (?, ?, ?)",
                       (user['id'], pid, reaction))

        db.commit()

        likes = db.execute("SELECT COUNT(*) as c FROM reactions WHERE post_id = ? AND reaction_type = 'like'", (pid,)).fetchone()['c']
        dislikes = db.execute("SELECT COUNT(*) as c FROM reactions WHERE post_id = ? AND reaction_type = 'dislike'", (pid,)).fetchone()['c']
        my_reaction = db.execute("SELECT reaction_type FROM reactions WHERE post_id = ? AND user_id = ?", (pid, user['id'])).fetchone()
        db.close()

        return json_response(self, {
            'likes': likes,
            'dislikes': dislikes,
            'my_reaction': my_reaction['reaction_type'] if my_reaction else None
        })

    def handle_remove_reaction(self, pid):
        user = require_auth(self)
        if not user:
            return

        db = get_db()
        db.execute("DELETE FROM reactions WHERE user_id = ? AND post_id = ?", (user['id'], pid))
        db.commit()

        likes = db.execute("SELECT COUNT(*) as c FROM reactions WHERE post_id = ? AND reaction_type = 'like'", (pid,)).fetchone()['c']
        dislikes = db.execute("SELECT COUNT(*) as c FROM reactions WHERE post_id = ? AND reaction_type = 'dislike'", (pid,)).fetchone()['c']
        db.close()

        return json_response(self, {'likes': likes, 'dislikes': dislikes, 'my_reaction': None})

    # ---- REPORT HANDLERS ----

    def handle_report_post(self, pid):
        user = require_auth(self)
        if not user:
            return

        data = get_json_body(self)
        reason = data.get('reason', '').strip()

        db = get_db()
        post = db.execute("SELECT id FROM posts WHERE id = ?", (pid,)).fetchone()
        if not post:
            db.close()
            return json_response(self, {'error': 'Gönderi bulunamadı'}, 404)

        existing = db.execute("SELECT id FROM reports WHERE reporter_id = ? AND post_id = ?", (user['id'], pid)).fetchone()
        if existing:
            db.close()
            return json_response(self, {'error': 'Bu gönderiyi zaten raporladınız'}, 409)

        db.execute("INSERT INTO reports (reporter_id, post_id, reason) VALUES (?, ?, ?)",
                   (user['id'], pid, reason))
        db.commit()
        db.close()

        return json_response(self, {'message': 'Gönderi raporlandı'}, 201)

    # ---- STORY HANDLERS (Extra Feature) ----

    def handle_create_story(self):
        user = require_auth(self)
        if not user:
            return

        fields, files = parse_multipart(self)
        if 'image' not in files:
            return json_response(self, {'error': 'Görsel yüklenmedi'}, 400)

        filename = save_uploaded_file(files['image'], STORIES_DIR)
        expires = (datetime.utcnow() + timedelta(hours=24)).isoformat()

        db = get_db()
        cursor = db.execute(
            "INSERT INTO stories (user_id, image_path, expires_at) VALUES (?, ?, ?)",
            (user['id'], f'/uploads/stories/{filename}', expires)
        )
        db.commit()
        db.close()

        return json_response(self, {'message': 'Hikaye oluşturuldu!', 'story_id': cursor.lastrowid}, 201)

    def handle_get_stories_feed(self):
        user = require_auth(self)
        if not user:
            return

        now = datetime.utcnow().isoformat()
        db = get_db()
        # Get stories from followed users + own stories that haven't expired
        stories = db.execute("""
            SELECT s.*, u.username, u.profile_pic,
                (SELECT COUNT(*) FROM story_views WHERE story_id = s.id) as view_count,
                (SELECT id FROM story_views WHERE story_id = s.id AND viewer_id = ?) as viewed
            FROM stories s
            JOIN users u ON s.user_id = u.id
            WHERE (s.user_id IN (SELECT following_id FROM follows WHERE follower_id = ?) OR s.user_id = ?)
                AND s.expires_at > ?
            ORDER BY s.created_at DESC
        """, (user['id'], user['id'], user['id'], now)).fetchall()
        db.close()

        # Group by user
        users_stories = {}
        for s in stories:
            s = dict(s)
            s['viewed'] = s['viewed'] is not None
            uid = s['user_id']
            if uid not in users_stories:
                users_stories[uid] = {
                    'user_id': uid,
                    'username': s['username'],
                    'profile_pic': s['profile_pic'],
                    'stories': []
                }
            users_stories[uid]['stories'].append(s)

        return json_response(self, {'story_groups': list(users_stories.values())})

    def handle_view_story(self, sid):
        user = require_auth(self)
        if not user:
            return

        db = get_db()
        story = db.execute("SELECT * FROM stories WHERE id = ?", (sid,)).fetchone()
        if not story:
            db.close()
            return json_response(self, {'error': 'Hikaye bulunamadı'}, 404)

        # Record view
        try:
            db.execute("INSERT INTO story_views (story_id, viewer_id) VALUES (?, ?)", (sid, user['id']))
            db.commit()
        except:
            pass
        db.close()

        return json_response(self, {'message': 'Görüntülendi'})

    # ---- ADMIN HANDLERS ----

    def handle_admin_stats(self):
        user = require_admin(self)
        if not user:
            return

        db = get_db()
        stats = {
            'total_users': db.execute("SELECT COUNT(*) as c FROM users WHERE role = 'user'").fetchone()['c'],
            'active_users': db.execute("SELECT COUNT(*) as c FROM users WHERE is_active = 1 AND is_banned = 0 AND role = 'user'").fetchone()['c'],
            'banned_users': db.execute("SELECT COUNT(*) as c FROM users WHERE is_banned = 1").fetchone()['c'],
            'inactive_users': db.execute("SELECT COUNT(*) as c FROM users WHERE is_active = 0").fetchone()['c'],
            'total_posts': db.execute("SELECT COUNT(*) as c FROM posts").fetchone()['c'],
            'visible_posts': db.execute("SELECT COUNT(*) as c FROM posts WHERE is_visible = 1").fetchone()['c'],
            'hidden_posts': db.execute("SELECT COUNT(*) as c FROM posts WHERE is_visible = 0").fetchone()['c'],
            'total_reports': db.execute("SELECT COUNT(*) as c FROM reports").fetchone()['c'],
            'pending_reports': db.execute("SELECT COUNT(*) as c FROM reports WHERE status = 'pending'").fetchone()['c'],
        }

        # Country distribution
        countries = db.execute("""
            SELECT country, COUNT(*) as count FROM users
            WHERE role = 'user' AND country != ''
            GROUP BY country ORDER BY count DESC
        """).fetchall()
        stats['country_distribution'] = [dict(c) for c in countries]

        # Posts by date (last 30 days)
        posts_by_date = db.execute("""
            SELECT date(created_at) as date, COUNT(*) as count
            FROM posts
            WHERE created_at >= date('now', '-30 days')
            GROUP BY date(created_at)
            ORDER BY date ASC
        """).fetchall()
        stats['posts_by_date'] = [dict(p) for p in posts_by_date]

        # Users by date (last 30 days)
        users_by_date = db.execute("""
            SELECT date(created_at) as date, COUNT(*) as count
            FROM users WHERE role = 'user'
            AND created_at >= date('now', '-30 days')
            GROUP BY date(created_at)
            ORDER BY date ASC
        """).fetchall()
        stats['users_by_date'] = [dict(u) for u in users_by_date]

        db.close()
        return json_response(self, {'stats': stats})

    def handle_admin_get_reports(self, params):
        user = require_admin(self)
        if not user:
            return

        status = params.get('status', ['pending'])[0]
        page = int(params.get('page', ['1'])[0])
        limit = 20
        offset = (page - 1) * limit

        db = get_db()
        reports = db.execute("""
            SELECT r.*, p.image_path, p.caption, p.user_id as post_owner_id, p.is_visible,
                u.username as reporter_username,
                ou.username as post_owner_username,
                (SELECT COUNT(*) FROM reports WHERE post_id = r.post_id) as total_reports
            FROM reports r
            JOIN posts p ON r.post_id = p.id
            JOIN users u ON r.reporter_id = u.id
            JOIN users ou ON p.user_id = ou.id
            WHERE r.status = ?
            ORDER BY r.created_at DESC
            LIMIT ? OFFSET ?
        """, (status, limit, offset)).fetchall()

        total = db.execute("SELECT COUNT(*) as c FROM reports WHERE status = ?", (status,)).fetchone()['c']
        db.close()

        return json_response(self, {
            'reports': [dict(r) for r in reports],
            'total': total,
            'page': page,
            'pages': max(1, (total + limit - 1) // limit)
        })

    def handle_admin_get_users(self, params):
        user = require_admin(self)
        if not user:
            return

        page = int(params.get('page', ['1'])[0])
        q = params.get('q', [''])[0]
        limit = 20
        offset = (page - 1) * limit

        db = get_db()
        if q:
            users = db.execute("""
                SELECT id, username, email, role, is_active, is_banned, ban_reason, country, created_at,
                    (SELECT COUNT(*) FROM posts WHERE user_id = users.id) as post_count,
                    (SELECT COUNT(*) FROM reports r JOIN posts p ON r.post_id = p.id WHERE p.user_id = users.id) as report_count
                FROM users WHERE (username LIKE ? OR email LIKE ?) AND role = 'user'
                ORDER BY created_at DESC LIMIT ? OFFSET ?
            """, (f'%{q}%', f'%{q}%', limit, offset)).fetchall()
            total = db.execute("SELECT COUNT(*) as c FROM users WHERE (username LIKE ? OR email LIKE ?) AND role = 'user'", (f'%{q}%', f'%{q}%')).fetchone()['c']
        else:
            users = db.execute("""
                SELECT id, username, email, role, is_active, is_banned, ban_reason, country, created_at,
                    (SELECT COUNT(*) FROM posts WHERE user_id = users.id) as post_count,
                    (SELECT COUNT(*) FROM reports r JOIN posts p ON r.post_id = p.id WHERE p.user_id = users.id) as report_count
                FROM users WHERE role = 'user'
                ORDER BY created_at DESC LIMIT ? OFFSET ?
            """, (limit, offset)).fetchall()
            total = db.execute("SELECT COUNT(*) as c FROM users WHERE role = 'user'").fetchone()['c']

        db.close()

        return json_response(self, {
            'users': [dict(u) for u in users],
            'total': total,
            'page': page,
            'pages': max(1, (total + limit - 1) // limit)
        })

    def handle_admin_toggle_post(self, pid):
        user = require_admin(self)
        if not user:
            return

        db = get_db()
        post = db.execute("SELECT * FROM posts WHERE id = ?", (pid,)).fetchone()
        if not post:
            db.close()
            return json_response(self, {'error': 'Gönderi bulunamadı'}, 404)

        new_visibility = 0 if post['is_visible'] else 1
        db.execute("UPDATE posts SET is_visible = ? WHERE id = ?", (new_visibility, pid))
        # Mark related reports as reviewed
        if new_visibility == 0:
            db.execute("UPDATE reports SET status = 'reviewed' WHERE post_id = ?", (pid,))
        db.commit()
        db.close()

        status_text = 'görünür' if new_visibility else 'gizli'
        return json_response(self, {'message': f'Gönderi {status_text} yapıldı', 'is_visible': new_visibility})

    def handle_admin_ban_user(self, uid):
        user = require_admin(self)
        if not user:
            return

        data = get_json_body(self)
        reason = data.get('reason', 'Kural ihlali')

        db = get_db()
        target = db.execute("SELECT * FROM users WHERE id = ? AND role = 'user'", (uid,)).fetchone()
        if not target:
            db.close()
            return json_response(self, {'error': 'Kullanıcı bulunamadı'}, 404)

        db.execute("UPDATE users SET is_banned = 1, ban_reason = ?, banned_at = datetime('now') WHERE id = ?", (reason, uid))
        db.execute("INSERT INTO ban_logs (admin_id, user_id, action, reason) VALUES (?, ?, 'ban', ?)",
                   (user['id'], uid, reason))
        db.commit()
        db.close()

        return json_response(self, {'message': 'Kullanıcı yasaklandı'})

    def handle_admin_unban_user(self, uid):
        user = require_admin(self)
        if not user:
            return

        db = get_db()
        db.execute("UPDATE users SET is_banned = 0, ban_reason = NULL, banned_at = NULL WHERE id = ?", (uid,))
        db.execute("INSERT INTO ban_logs (admin_id, user_id, action, reason) VALUES (?, ?, 'unban', '')",
                   (user['id'], uid))
        db.commit()
        db.close()

        return json_response(self, {'message': 'Kullanıcı yasağı kaldırıldı'})

    def handle_admin_review_report(self, rid):
        user = require_admin(self)
        if not user:
            return

        data = get_json_body(self)
        action = data.get('action', 'dismissed')

        db = get_db()
        report = db.execute("SELECT * FROM reports WHERE id = ?", (rid,)).fetchone()
        if not report:
            db.close()
            return json_response(self, {'error': 'Rapor bulunamadı'}, 404)

        db.execute("UPDATE reports SET status = ? WHERE id = ?", (action, rid))
        db.commit()
        db.close()

        return json_response(self, {'message': 'Rapor güncellendi'})

    # ---- FILE SERVING ----

    def serve_upload(self, path):
        filepath = os.path.join(os.path.dirname(__file__), path.lstrip('/'))
        if os.path.isfile(filepath):
            content_type, _ = mimetypes.guess_type(filepath)
            self.send_response(200)
            self.send_header('Content-Type', content_type or 'application/octet-stream')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Cache-Control', 'max-age=86400')
            self.end_headers()
            with open(filepath, 'rb') as f:
                self.wfile.write(f.read())
        else:
            self.send_response(404)
            self.end_headers()

    def serve_frontend(self, path):
        if path == '/' or path == '':
            path = '/index.html'

        filepath = os.path.join(FRONTEND_DIR, path.lstrip('/'))

        if not os.path.isfile(filepath):
            filepath = os.path.join(FRONTEND_DIR, 'index.html')

        if os.path.isfile(filepath):
            content_type, _ = mimetypes.guess_type(filepath)
            self.send_response(200)
            self.send_header('Content-Type', content_type or 'text/html')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            with open(filepath, 'rb') as f:
                self.wfile.write(f.read())
        else:
            self.send_response(404)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(b'<h1>404 Not Found</h1>')


# ---- MAIN ----

if __name__ == '__main__':
    init_db()
    server = HTTPServer((HOST, PORT), KareDefteriHandler)
    print(f"KareDefteri server running at http://localhost:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
        server.server_close()
