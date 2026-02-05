from flask import Flask, render_template, request, redirect, session, send_file, flash, jsonify, url_for
import sqlite3
from io import BytesIO
from functools import wraps
from datetime import datetime, timedelta
import json
import csv
import re
import os
import secrets
import platform
import sys
import random
import time

app = Flask(__name__)
app.secret_key = "super_secret_key_kenas_walfredon_2024"
app.config['STATIC_FOLDER'] = 'static'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'

# Buat folder uploads jika belum ada
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

ACCOUNTS = ["Affiliate 1", "Affiliate 2", "Affiliate 3", "Affiliate 4"]
CATEGORIES = ["Ide", "Stok", "Skrip", "TikTok", "Reels", "Story", "Analisis", "Strategi"]

def get_db():
    """Get database connection"""
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize database with all tables"""
    conn = get_db()
    c = conn.cursor()
    
    # Table untuk content
    c.execute("""
        CREATE TABLE IF NOT EXISTS content (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account TEXT NOT NULL,
            category TEXT NOT NULL,
            text TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            tags TEXT,
            priority TEXT DEFAULT 'normal',
            status TEXT DEFAULT 'active'
        )
    """)
    
    # Index untuk pencarian
    c.execute("CREATE INDEX IF NOT EXISTS idx_account_category ON content (account, category)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON content (created_at)")
    
    # Table untuk daily_notes
    c.execute("""
        CREATE TABLE IF NOT EXISTS daily_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT UNIQUE NOT NULL,
            note TEXT NOT NULL,
            mood TEXT DEFAULT 'neutral',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Table untuk tasks
    c.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'pending',
            priority TEXT DEFAULT 'medium',
            due_date TEXT,
            assigned_to TEXT DEFAULT 'Kenas',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            category TEXT
        )
    """)
    
    # Table untuk content_analytics
    c.execute("""
        CREATE TABLE IF NOT EXISTS content_analytics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content_id INTEGER,
            views INTEGER DEFAULT 0,
            likes INTEGER DEFAULT 0,
            shares INTEGER DEFAULT 0,
            comments INTEGER DEFAULT 0,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (content_id) REFERENCES content (id) ON DELETE CASCADE
        )
    """)
    
    # Table untuk tags
    c.execute("""
        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            color TEXT DEFAULT '#6c757d',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Table untuk backup_history
    c.execute("""
        CREATE TABLE IF NOT EXISTS backup_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            item_count INTEGER,
            backup_type TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # ============ TABEL BARU UNTUK FITUR BARU ============
    
    # Users table
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            fullname TEXT,
            email TEXT,
            phone TEXT,
            password TEXT,
            role TEXT DEFAULT 'user',
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # User preferences table
    c.execute("""
        CREATE TABLE IF NOT EXISTS user_preferences (
            username TEXT PRIMARY KEY,
            theme TEXT DEFAULT 'light',
            language TEXT DEFAULT 'id',
            timezone TEXT DEFAULT 'Asia/Jakarta',
            notifications BOOLEAN DEFAULT 1,
            items_per_page INTEGER DEFAULT 20,
            default_view TEXT DEFAULT 'dashboard',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE
        )
    """)
    
    # Login history table
    c.execute("""
        CREATE TABLE IF NOT EXISTS login_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ip_address TEXT,
            user_agent TEXT,
            success BOOLEAN DEFAULT 1,
            FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE
        )
    """)
    
    # Content schedule table
    c.execute("""
        CREATE TABLE IF NOT EXISTS content_schedule (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content_id INTEGER,
            scheduled_date TEXT NOT NULL,
            scheduled_time TEXT,
            platform TEXT,
            status TEXT DEFAULT 'scheduled',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (content_id) REFERENCES content (id) ON DELETE CASCADE
        )
    """)
    
    # Integrations table
    c.execute("""
        CREATE TABLE IF NOT EXISTS integrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            platform TEXT NOT NULL,
            api_key TEXT,
            api_secret TEXT,
            status TEXT DEFAULT 'disconnected',
            connected_at TIMESTAMP,
            disconnected_at TIMESTAMP,
            last_sync TIMESTAMP,
            UNIQUE(username, platform),
            FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE
        )
    """)
    
    # API keys table
    c.execute("""
        CREATE TABLE IF NOT EXISTS api_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            api_key TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_used TIMESTAMP,
            is_active BOOLEAN DEFAULT 1,
            FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE
        )
    """)
    
    # Notifications table
    c.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            type TEXT NOT NULL,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            is_read BOOLEAN DEFAULT 0,
            action_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE
        )
    """)
    
    # ===== TABEL BARU UNTUK AI ASSISTANT =====
    # Table untuk ai_usage_log
    c.execute("""
        CREATE TABLE IF NOT EXISTS ai_usage_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            prompt TEXT NOT NULL,
            action TEXT NOT NULL,
            tokens_used INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE
        )
    """)
    
    # Insert default user jika belum ada
    try:
        c.execute("""
            INSERT OR IGNORE INTO users 
            (username, fullname, email, password, role) 
            VALUES (?,?,?,?,?)
        """, ('Kenas Walfredon', 'Kenas Walfredon', 'kenas@example.com', 'kenasganteng', 'admin'))
        print("✅ Default user created")
    except Exception as e:
        print(f"Note: User already exists or error: {e}")
    
    # Insert default preferences
    try:
        c.execute("""
            INSERT OR IGNORE INTO user_preferences 
            (username, theme, language, timezone) 
            VALUES (?,?,?,?)
        """, ('Kenas Walfredon', 'light', 'id', 'Asia/Jakarta'))
        print("✅ Default preferences created")
    except Exception as e:
        print(f"Note: Preferences already exist or error: {e}")
    
    conn.commit()
    conn.close()
    print("✅ Database initialized successfully")

def upgrade_db():
    """Upgrade database schema if needed"""
    conn = get_db()
    c = conn.cursor()
    
    try:
        # Check if mood column exists in daily_notes
        c.execute("PRAGMA table_info(daily_notes)")
        columns = [col[1] for col in c.fetchall()]
        
        if 'mood' not in columns:
            print("Adding 'mood' column to daily_notes table...")
            c.execute("ALTER TABLE daily_notes ADD COLUMN mood TEXT DEFAULT 'neutral'")
            print("✅ 'mood' column added to daily_notes table")
        
        # Check if ai_usage_log table exists
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ai_usage_log'")
        if not c.fetchone():
            print("Creating 'ai_usage_log' table...")
            c.execute("""
                CREATE TABLE ai_usage_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    prompt TEXT NOT NULL,
                    action TEXT NOT NULL,
                    tokens_used INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            print("✅ 'ai_usage_log' table created")
            
        conn.commit()
        print("✅ Database upgrade completed successfully!")
            
    except Exception as e:
        print(f"❌ Error upgrading database: {e}")
        conn.rollback()
    finally:
        conn.close()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("login"):
            flash("Silakan login terlebih dahulu", "warning")
            return redirect("/")
        return f(*args, **kwargs)
    return decorated_function

# Helper function to create notifications
def create_notification(username, type, title, message, action_url=None):
    """Create a new notification"""
    conn = get_db()
    
    conn.execute("""
        INSERT INTO notifications 
        (username, type, title, message, action_url, created_at)
        VALUES (?,?,?,?,?,CURRENT_TIMESTAMP)
    """, (username, type, title, message, action_url))
    
    conn.commit()
    conn.close()
    
    return True

# Filter custom untuk Jinja2
def nl2br(value):
    """Convert newlines to <br> tags"""
    if value:
        return value.replace('\n', '<br>')
    return value

def format_datetime(value, format='%d %B %Y, %H:%M'):
    """Format datetime"""
    if value:
        if isinstance(value, str):
            try:
                value = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
            except:
                try:
                    value = datetime.strptime(value, '%Y-%m-%d')
                except:
                    return value
        return value.strftime(format)
    return ''

def calculate_time_ago(date_string):
    """Calculate time ago in Indonesian"""
    if not date_string:
        return ''
    
    try:
        if isinstance(date_string, str):
            date = datetime.strptime(date_string, '%Y-%m-%d %H:%M:%S')
        else:
            date = date_string
    except:
        return date_string
    
    now = datetime.now()
    diff = now - date
    
    if diff.days > 365:
        years = diff.days // 365
        return f'{years} tahun yang lalu'
    elif diff.days > 30:
        months = diff.days // 30
        return f'{months} bulan yang lalu'
    elif diff.days > 0:
        return f'{diff.days} hari yang lalu'
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f'{hours} jam yang lalu'
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f'{minutes} menit yang lalu'
    else:
        return 'Baru saja'

# Register filters
app.jinja_env.filters['nl2br'] = nl2br
app.jinja_env.filters['format_datetime'] = format_datetime
app.jinja_env.filters['calculate_time_ago'] = calculate_time_ago

# Inject variables ke semua template
@app.context_processor
def inject_global_vars():
    unread_notifications = 0
    
    if session.get('login'):
        try:
            conn = get_db()
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM notifications WHERE username=? AND is_read=0", 
                     (session['username'],))
            result = c.fetchone()
            unread_notifications = result[0] if result else 0
            conn.close()
        except:
            unread_notifications = 0
    
    return dict(
        datetime=datetime,
        now=datetime.now(),
        accounts=ACCOUNTS,
        categories=CATEGORIES,
        app_name="Affiliate Pro Manager",
        unread_notifications=unread_notifications,
        month_names=['Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni',
                    'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember']
    )

# ==================== ROUTES UTAMA ====================

@app.route("/", methods=["GET", "POST"])
def login():
    if session.get("login"):
        return redirect("/dashboard")
        
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        
        # Update credentials
        if username.lower() == "kenas walfredon" and password == "kenasganteng":
            session["login"] = True
            session["username"] = "Kenas Walfredon"
            session["user_role"] = "admin"
            
            # Update login history
            conn = get_db()
            try:
                conn.execute("""
                    UPDATE users SET last_login=CURRENT_TIMESTAMP 
                    WHERE username=?
                """, (session['username'],))
                
                conn.execute("""
                    INSERT INTO login_history (username, ip_address, user_agent)
                    VALUES (?,?,?)
                """, (session['username'], request.remote_addr, request.user_agent.string))
                
                conn.commit()
            except Exception as e:
                print(f"Error updating login history: {e}")
                conn.rollback()
            finally:
                conn.close()
            
            # Create welcome notification
            try:
                create_notification(
                    session['username'],
                    'system',
                    'Welcome to Affiliate Pro!',
                    'Selamat datang di Affiliate Pro Manager. Mulai kelola konten affiliate Anda dengan mudah.',
                    '/dashboard'
                )
            except:
                pass
            
            flash("Login berhasil! Selamat datang Kenas Walfredon 🎉", "success")
            return redirect("/dashboard")
        else:
            flash("Username atau password salah ❌", "error")
    
    return render_template("login.html")

@app.route("/logout")
def logout():
    username = session.get("username", "User")
    session.clear()
    flash(f"Sampai jumpa {username}! Anda telah logout 👋", "info")
    return redirect("/")

@app.route("/dashboard")
@login_required
def dashboard():
    conn = get_db()
    c = conn.cursor()
    
    # Statistik umum
    c.execute("SELECT COUNT(*) FROM content")
    total_result = c.fetchone()
    total_content = total_result[0] if total_result else 0
    
    c.execute("SELECT COUNT(*) FROM tasks WHERE status='pending'")
    pending_result = c.fetchone()
    pending_tasks = pending_result[0] if pending_result else 0
    
    c.execute("SELECT COUNT(DISTINCT date) FROM daily_notes")
    notes_result = c.fetchone()
    total_notes = notes_result[0] if notes_result else 0
    
    # Content per kategori
    c.execute("""
        SELECT category, COUNT(*) as count 
        FROM content 
        GROUP BY category 
        ORDER BY count DESC 
        LIMIT 5
    """)
    top_categories = c.fetchall()
    
    # Recent content
    c.execute("""
        SELECT account, category, text, created_at 
        FROM content 
        ORDER BY created_at DESC 
        LIMIT 5
    """)
    recent_content = c.fetchall()
    
    # Today's note
    today = datetime.now().strftime("%Y-%m-%d")
    c.execute("SELECT note, mood FROM daily_notes WHERE date=?", (today,))
    today_note = c.fetchone()
    
    # Recent notifications
    try:
        c.execute("""
            SELECT title, message, created_at 
            FROM notifications 
            WHERE username=? 
            ORDER BY created_at DESC 
            LIMIT 3
        """, (session['username'],))
        recent_notifications = c.fetchall()
    except:
        recent_notifications = []
    
    conn.close()
    
    return render_template("dashboard.html", 
                         total_content=total_content,
                         pending_tasks=pending_tasks,
                         total_notes=total_notes,
                         top_categories=top_categories,
                         recent_content=recent_content,
                         today_note=today_note,
                         recent_notifications=recent_notifications,
                         today=today)

# ==================== USER PROFILE ====================

@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    conn = get_db()
    
    if request.method == "POST":
        action = request.form.get('action')
        
        if action == 'update_profile':
            # Update profile data
            fullname = request.form.get('fullname', '').strip()
            email = request.form.get('email', '').strip()
            phone = request.form.get('phone', '').strip()
            
            try:
                conn.execute("""
                    UPDATE users SET 
                    fullname=?, email=?, phone=?, updated_at=CURRENT_TIMESTAMP 
                    WHERE username=?
                """, (fullname, email, phone, session['username']))
                
                session['fullname'] = fullname
                conn.commit()
                flash("✅ Profil berhasil diupdate", "success")
            except Exception as e:
                flash(f"❌ Error updating profile: {e}", "error")
            
        elif action == 'change_password':
            current_password = request.form.get('current_password')
            new_password = request.form.get('new_password')
            confirm_password = request.form.get('confirm_password')
            
            if new_password != confirm_password:
                flash("❌ Password baru tidak cocok", "error")
            else:
                try:
                    conn.execute("""
                        UPDATE users SET 
                        password=?, updated_at=CURRENT_TIMESTAMP 
                        WHERE username=?
                    """, (new_password, session['username']))
                    conn.commit()
                    flash("✅ Password berhasil diubah", "success")
                except Exception as e:
                    flash(f"❌ Error changing password: {e}", "error")
        
        elif action == 'update_preferences':
            theme = request.form.get('theme', 'light')
            language = request.form.get('language', 'id')
            timezone = request.form.get('timezone', 'Asia/Jakarta')
            notifications = request.form.get('notifications', 'on') == 'on'
            items_per_page = request.form.get('items_per_page', 20)
            
            try:
                conn.execute("""
                    INSERT OR REPLACE INTO user_preferences 
                    (username, theme, language, timezone, notifications, items_per_page, updated_at)
                    VALUES (?,?,?,?,?,?,CURRENT_TIMESTAMP)
                """, (session['username'], theme, language, timezone, notifications, items_per_page))
                
                session['theme'] = theme
                conn.commit()
                flash("✅ Preferensi berhasil diupdate", "success")
            except Exception as e:
                flash(f"❌ Error updating preferences: {e}", "error")
    
    # Get user data
    try:
        user = conn.execute("""
            SELECT username, fullname, email, phone, 
                   created_at, last_login
            FROM users 
            WHERE username=?
        """, (session['username'],)).fetchone()
    except:
        user = None
    
    # Get preferences
    try:
        preferences = conn.execute("""
            SELECT theme, language, timezone, notifications, items_per_page
            FROM user_preferences 
            WHERE username=?
        """, (session['username'],)).fetchone()
    except:
        preferences = None
    
    # Get login history
    try:
        login_history = conn.execute("""
            SELECT login_time, ip_address, user_agent 
            FROM login_history 
            WHERE username=? 
            ORDER BY login_time DESC 
            LIMIT 10
        """, (session['username'],)).fetchall()
    except:
        login_history = []
    
    conn.close()
    
    return render_template("profile.html", 
                         user=user,
                         preferences=preferences,
                         login_history=login_history)

# ==================== CALENDAR ====================

@app.route("/calendar")
@login_required
def calendar():
    conn = get_db()
    
    # Get schedule for current month
    year = request.args.get('year', datetime.now().year, type=int)
    month = request.args.get('month', datetime.now().month, type=int)
    
    events = []
    
    try:
        # Get scheduled content
        c = conn.cursor()
        c.execute("""
            SELECT 
                c.id,
                c.account,
                c.category,
                c.text,
                c.created_at,
                s.scheduled_date,
                s.scheduled_time,
                s.platform,
                s.status
            FROM content c
            LEFT JOIN content_schedule s ON c.id = s.content_id
            WHERE s.scheduled_date IS NOT NULL
            AND strftime('%Y-%m', s.scheduled_date) = ?
            ORDER BY s.scheduled_date, s.scheduled_time
        """, (f"{year}-{month:02d}",))
        
        scheduled_content = c.fetchall()
        
        # Get tasks with due dates
        c.execute("""
            SELECT id, title, due_date, priority, status
            FROM tasks
            WHERE due_date IS NOT NULL
            AND strftime('%Y-%m', due_date) = ?
            ORDER BY due_date
        """, (f"{year}-{month:02d}",))
        
        scheduled_tasks = c.fetchall()
        
        # Get notes with dates
        c.execute("""
            SELECT date, note, mood
            FROM daily_notes
            WHERE strftime('%Y-%m', date) = ?
            ORDER BY date
        """, (f"{year}-{month:02d}",))
        
        scheduled_notes = c.fetchall()
        
        # Combine all events
        for item in scheduled_content:
            if item['scheduled_date']:
                events.append({
                    'type': 'content',
                    'title': f"[{item['account']}] {item['category']}",
                    'date': item['scheduled_date'],
                    'time': item['scheduled_time'],
                    'platform': item['platform'],
                    'status': item['status'],
                    'description': item['text'][:100] + '...' if len(item['text']) > 100 else item['text']
                })
        
        for item in scheduled_tasks:
            events.append({
                'type': 'task',
                'title': item['title'],
                'date': item['due_date'],
                'priority': item['priority'],
                'status': item['status']
            })
        
        for item in scheduled_notes:
            events.append({
                'type': 'note',
                'title': 'Daily Note',
                'date': item['date'],
                'mood': item['mood'],
                'description': item['note'][:100] + '...' if len(item['note']) > 100 else item['note']
            })
    except Exception as e:
        print(f"Error fetching calendar events: {e}")
    
    conn.close()
    
    return render_template("calendar.html",
                         events=events,
                         year=year,
                         month=month,
                         current_date=datetime.now().strftime("%Y-%m-%d"))

@app.route("/api/calendar/events")
@login_required
def api_calendar_events():
    """API endpoint for calendar events (for fullcalendar.js)"""
    start = request.args.get('start')
    end = request.args.get('end')
    
    conn = get_db()
    c = conn.cursor()
    
    events = []
    
    try:
        # Get scheduled content
        c.execute("""
            SELECT 
                c.id,
                c.account,
                c.category,
                s.scheduled_date,
                s.scheduled_time,
                s.platform,
                s.status
            FROM content c
            LEFT JOIN content_schedule s ON c.id = s.content_id
            WHERE s.scheduled_date IS NOT NULL
            AND s.scheduled_date BETWEEN ? AND ?
        """, (start, end))
        
        for row in c.fetchall():
            events.append({
                'id': f"content_{row['id']}",
                'title': f"[{row['account']}] {row['category']}",
                'start': f"{row['scheduled_date']} {row['scheduled_time'] or '00:00:00'}",
                'color': '#4361ee',
                'type': 'content'
            })
        
        # Get tasks
        c.execute("""
            SELECT id, title, due_date, priority
            FROM tasks
            WHERE due_date IS NOT NULL
            AND due_date BETWEEN ? AND ?
        """, (start, end))
        
        for row in c.fetchall():
            events.append({
                'id': f"task_{row['id']}",
                'title': row['title'],
                'start': row['due_date'],
                'color': '#f72585' if row['priority'] == 'high' else '#ffc107',
                'type': 'task'
            })
    except Exception as e:
        print(f"Error fetching calendar API events: {e}")
    
    conn.close()
    
    return jsonify(events)

# ==================== AI ASSISTANT ====================

@app.route("/ai-assistant", methods=["GET", "POST"])
@login_required
def ai_assistant():
    if request.method == "POST":
        prompt = request.form.get('prompt', '').strip()
        action = request.form.get('action', 'caption')
        tone = request.form.get('tone', 'professional')
        platform = request.form.get('platform', 'Instagram')
        
        if not prompt:
            flash("❌ Masukkan prompt terlebih dahulu", "error")
            return redirect(url_for('ai_assistant'))
        
        # Generate content based on prompt
        generated_content = generate_ai_content(prompt, action, tone, platform)
        
        # Log AI usage
        try:
            conn = get_db()
            conn.execute("""
                INSERT INTO ai_usage_log (username, prompt, action, tokens_used)
                VALUES (?,?,?,?)
            """, (session['username'], prompt, action, len(prompt.split())))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Warning: Could not log AI usage: {e}")
        
        return render_template("ai_assistant.html",
                             prompt=prompt,
                             generated_content=generated_content,
                             action=action,
                             tone=tone,
                             platform=platform)
    
    return render_template("ai_assistant.html")

def generate_ai_content(prompt, action, tone='professional', platform='Instagram'):
    """Generate content using AI (simulated for now)"""
    
    # Simulate AI processing
    time.sleep(1)
    
    # Convert Indonesian prompts to English for better generation
    prompt_lower = prompt.lower()
    
    # Check for script-related prompts in Indonesian
    script_keywords = ['skrip', 'script', 'naskah', 'video script', 'konten video', '15 detik', '30 detik', '1 menit', 'reels', 'tiktok']
    
    # If user asks for a script, generate proper script content
    if any(keyword in prompt_lower for keyword in script_keywords) or action == 'script':
        # Extract duration if mentioned
        duration = "15-30 detik"
        if '15 detik' in prompt_lower:
            duration = "15 detik"
        elif '30 detik' in prompt_lower:
            duration = "30 detik"
        elif '1 menit' in prompt_lower or '60 detik' in prompt_lower:
            duration = "1 menit"
        
        # Special templates for different platforms and tones
        if platform == 'TikTok':
            if tone == 'casual':
                scripts = [
                    f"""🎬 TIKTOK SCRIPT ({duration})

[0-3 detik] HOOK:
"Hai guys! Ada yang sering bingung bikin konten?" 🤔

[3-8 detik] CONTENT:
"Gue kasih tips bikin script cepat buat {duration}!" 💡
"Pertama, buat hook yang menarik perhatian..."

[8-12 detik] VALUE:
"Kedua, kasih value dalam 10 detik pertama..." ✨

[12-15 detik] CTA:
"Komen 'SCRIPT' buat dapetin template gratis!" 📝""",
                    
                    f"""🔥 TIKTOK SCRIPT ({duration})

INTRO (3 detik):
"OMG, gue baru nemu cara gampang bikin konten viral!" 😱

MAIN (8 detik):
"Caranya? Fokus sama 3 elemen ini:"
"1. Hook yang bikin penasaran" 🎣
"2. Value yang bermanfaat" 💎
"3. CTA yang jelas" 📢

OUTRO (4 detik):
"Save video ini buat referensi!" ⬇️""",
                    
                    f"""💫 SCRIPT {duration.upper()}

[BAGIAN 1 - HOOK]
"Bro, mau kontenmu ramai? Gini caranya!" 🚀

[BAGIAN 2 - ISI]
"{duration} cukup buat:"
"• Intro 3 detik"
"• Konten 8 detik"
"• CTA 4 detik"

[BAGIAN 3 - ACTION]
"Gue udah siapin template di bio!" 👇"""
                ]
            elif tone == 'professional':
                scripts = [
                    f"""📊 PROFESSIONAL TIKTOK SCRIPT
Duration: {duration}

[00:00-00:03] HOOK:
"Mastering content creation in {duration}"

[00:03-00:10] CONTENT:
"Key elements for successful scripts:"
"1. Attention-grabbing opening"
"2. Clear value proposition"
"3. Strong call-to-action"

[00:10-00:15] CTA:
"Download free templates in comments" 📥""",
                    
                    f"""🎯 TIKTOK BUSINESS SCRIPT

HOOK (3s):
"Boost engagement with this {duration} formula"

CONTENT (8s):
"• 0-3s: Grab attention"
"• 3-8s: Deliver value"
"• 8-12s: Show results"

CTA (4s):
"Book consultation (link in bio)" 💼"""
                ]
            else:
                scripts = [
                    f"""✨ TIKTOK CONTENT SCRIPT

🎯 Duration: {duration}
🎯 Platform: TikTok
🎯 Tone: {tone}

[START]
Open with trending sound
Show before/after (if applicable)

[MIDDLE]
Quick tip or hack
Visual demonstration

[END]
Ask question in comments
Use relevant hashtags"""
                ]
            
            return random.choice(scripts)
        
        elif platform == 'Instagram':
            if tone == 'casual':
                scripts = [
                    f"""📱 INSTAGRAM REELS SCRIPT

🎬 Duration: {duration}
💡 Platform: Instagram Reels

[0-4 detik] HOOK:
"Hari ini gue bagiin cara bikin script {duration}!" 🎯

[4-10 detik] CONTENT:
"Step-by-step:"
"1. Hook yang clickable 🎣"
"2. Problem & solution 💡"
"3. Call to action 📢"

[10-15 detik] CTA:
"Simpan buat modal konten!" 💾
"Follow for more tips!" 👉""",
                    
                    f"""🌟 INSTAGRAM STORY SCRIPT

💫 Perfect for {duration} Reels

💬 DIALOG:
"Pssst... rahasia bikin konten viral!"

🎭 VISUALS:
• Text overlay with emojis
• Quick cuts every 2-3 seconds
• Subtle transitions

🎯 CTA:
"Swipe up for template" ⬆️"""
                ]
            else:
                scripts = [
                    f"""📸 INSTAGRAM CONTENT SCRIPT

Duration: {duration}
Tone: {tone}

VISUAL PLAN:
• 0-5s: Eye-catching opening
• 5-12s: Value demonstration
• 12-15s: Clear CTA overlay

CAPTION IDEAS:
"Learn how to create engaging {duration} content"
"↓ Template in bio""",
                    
                    f"""💼 INSTAGRAM BUSINESS REELS

STRUCTURE:
Intro: Problem statement (3s)
Solution: Quick tips (7s)
CTA: Lead generation (5s)

TIPS:
• Use trending audio
• Add subtitles
• Include branding"""
                ]
            
            return random.choice(scripts)
        
        # Default script template for other platforms
        return f"""🎬 VIDEO SCRIPT ({duration})

[0-5 detik] HOOK:
Buat pernyataan menarik atau pertanyaan yang bikin penasaran

[5-12 detik] CONTENT:
Jelaskan poin utama dengan singkat dan jelas

[12-15 detik] CTA:
Ajakan untuk like, comment, atau follow

🎯 TIPS:
• Gunakan teks besar dan jelas
• Tambahkan musik trending
• Pakai efek visual sederhana
• Keep it simple & engaging!"""
    
    # Original logic for other content types
    templates = {
        'caption': {
            'professional': [
                f"🚀 {prompt}\n\nElevate your affiliate marketing strategy with this professional approach. #affiliatemarketing #digitalmarketing",
                f"📊 {prompt}\n\nData-driven insights for better results. #marketingstrategy #businessgrowth",
                f"💼 {prompt}\n\nProfessional tips for affiliate success. #entrepreneurlife #passiveincome"
            ],
            'casual': [
                f"Hey everyone! 👋\n\n{prompt}\n\nWhat do you think? Let me know in the comments! 😊",
                f"OMG, you need to see this! 👀\n\n{prompt}\n\nGame changer for real! 🔥",
                f"Quick tip for you today! 💡\n\n{prompt}\n\nSave this for later! 📌"
            ],
            'friendly': [
                f"Hi friends! 🤗\n\n{prompt}\n\nHope this helps you on your journey! ❤️",
                f"Just wanted to share this with my amazing community! 🌟\n\n{prompt}",
                f"Feeling excited to share this with you all! 🎉\n\n{prompt}"
            ],
            'motivational': [
                f"Believe in yourself! 💪\n\n{prompt}\n\nYou've got this! #motivation #successmindset",
                f"Dream big, work hard! ✨\n\n{prompt}\n\nThe only limit is your mind. #inspiration #goals",
                f"Success is not final, failure is not fatal! 🚀\n\n{prompt}\n\nKeep pushing forward! #determination"
            ]
        },
        'script': {
            'professional': [
                f"Hello everyone, welcome back to the channel. Today we're discussing: {prompt}\n\nFirst, let's look at the key points...",
                f"In this video, we'll explore {prompt} in detail. This is crucial for anyone in affiliate marketing.",
                f"Welcome to this comprehensive guide on {prompt}. We'll cover everything you need to know."
            ],
            'casual': [
                f"What's up guys! So today we're talking about {prompt}. This is gonna be fun!",
                f"Hey everyone, grab your coffee because today we're diving into {prompt}!",
                f"OMG you guys, I'm so excited to talk about {prompt} today!"
            ]
        },
        'idea': [
            f"Content Idea: {prompt}\n\nPlatform: {platform}\nFormat: Video + Carousel\nCTA: Link in bio\nHashtags: #affiliate #marketing",
            f"Strategy: {prompt}\n\nSchedule: 3x per week\nTarget: Beginners\nTools needed: Canva, Video editor",
            f"Campaign Concept: {prompt}\n\nDuration: 7 days\nBudget: $100\nExpected ROI: 300%"
        ],
        'hashtag': [
            f"#{prompt.replace(' ', '')} #affiliatemarketing #digitalmarketing #onlinbusiness #makemoneyonline #passiveincome #entrepreneur",
            f"#{prompt.replace(' ', '')} #socialmediamarketing #contentcreator #digitalcreator #marketingtips #businessstrategy",
            f"#{prompt.replace(' ', '')} #marketingstrategy #growthhacking #viralcontent #trending #successmindset"
        ]
    }
    
    if action in templates:
        if isinstance(templates[action], dict):
            # For actions with tone variations
            if tone in templates[action]:
                template_list = templates[action][tone]
            else:
                template_list = templates[action]['professional']
        else:
            # For actions without tone variations
            template_list = templates[action]
        
        template = random.choice(template_list)
        return template
    
    return f"Generated content about: {prompt}\n\nTone: {tone}\nPlatform: {platform}\n\nThis is AI-generated content based on your input."

@app.route("/api/ai/generate", methods=["POST"])
@login_required
def api_ai_generate():
    """API endpoint for AI content generation"""
    data = request.get_json()
    prompt = data.get('prompt', '').strip()
    action = data.get('action', 'caption')
    
    if not prompt:
        return jsonify({'error': 'Prompt is required'}), 400
    
    generated_content = generate_ai_content(prompt, action)
    
    return jsonify({
        'success': True,
        'content': generated_content,
        'prompt': prompt,
        'action': action
    })

@app.route("/content-manager/save-ai", methods=["POST"])
@login_required
def save_ai_content():
    """Save AI generated content to content manager"""
    account = request.form.get('account')
    category = request.form.get('category')
    content = request.form.get('content', '').strip()
    
    if not account or not category or not content:
        flash("❌ Semua field harus diisi", "error")
        return redirect(url_for('ai_assistant'))
    
    conn = get_db()
    c = conn.cursor()
    
    try:
        c.execute("""
            INSERT INTO content (account, category, text, priority) 
            VALUES (?,?,?,?)
        """, (account, category, content, 'high'))
        
        # Create analytics entry
        content_id = c.lastrowid
        c.execute("INSERT INTO content_analytics (content_id) VALUES (?)", (content_id,))
        
        conn.commit()
        
        # Create notification
        create_notification(
            session['username'],
            'content',
            'AI Content Saved',
            f'AI generated content saved to {account} - {category}',
            url_for('manage', account=account, category=category)
        )
        
        flash(f"✅ Konten AI berhasil disimpan ke {account} - {category}", "success")
        
    except Exception as e:
        flash(f"❌ Error: {str(e)}", "error")
    finally:
        conn.close()
    
    return redirect(url_for('ai_assistant'))

# ==================== INTEGRATIONS ====================

@app.route("/integrations", methods=["GET", "POST"])
@login_required
def integrations():
    conn = get_db()
    
    if request.method == "POST":
        action = request.form.get('action')
        
        if action == 'connect_social':
            platform = request.form.get('platform')
            api_key = request.form.get('api_key', '').strip()
            api_secret = request.form.get('api_secret', '').strip()
            
            if not api_key:
                flash("❌ API Key diperlukan", "error")
            else:
                # Save API credentials
                conn.execute("""
                    INSERT OR REPLACE INTO integrations 
                    (username, platform, api_key, api_secret, status, connected_at)
                    VALUES (?,?,?,?,?,CURRENT_TIMESTAMP)
                """, (session['username'], platform, api_key, api_secret, 'connected'))
                
                conn.commit()
                
                # Create notification
                create_notification(
                    session['username'],
                    'system',
                    f'Connected to {platform}',
                    f'Successfully connected to {platform} integration.',
                    '/integrations'
                )
                
                flash(f"✅ Berhasil terhubung dengan {platform}", "success")
            
        elif action == 'disconnect':
            platform = request.form.get('platform')
            
            conn.execute("""
                UPDATE integrations SET 
                status='disconnected', disconnected_at=CURRENT_TIMESTAMP 
                WHERE username=? AND platform=?
            """, (session['username'], platform))
            
            conn.commit()
            flash(f"✅ Berhasil putuskan koneksi {platform}", "success")
        
        elif action == 'generate_api_key':
            api_key = secrets.token_urlsafe(32)
            
            conn.execute("""
                INSERT OR REPLACE INTO api_keys 
                (username, api_key, created_at)
                VALUES (?,?,CURRENT_TIMESTAMP)
            """, (session['username'], api_key))
            
            conn.commit()
            return render_template("integrations.html", new_api_key=api_key)
        
        elif action == 'revoke_api_key':
            api_key = request.form.get('api_key')
            
            conn.execute("""
                UPDATE api_keys SET is_active=0 
                WHERE username=? AND api_key=?
            """, (session['username'], api_key))
            
            conn.commit()
            flash("✅ API Key berhasil dinonaktifkan", "success")
    
    # Get connected integrations
    try:
        integrations_list = conn.execute("""
            SELECT platform, status, connected_at, last_sync
            FROM integrations 
            WHERE username=?
            ORDER BY connected_at DESC
        """, (session['username'],)).fetchall()
    except:
        integrations_list = []
    
    # Get API keys
    try:
        api_keys = conn.execute("""
            SELECT api_key, created_at, last_used, is_active
            FROM api_keys 
            WHERE username=? AND is_active=1
            ORDER BY created_at DESC
        """, (session['username'],)).fetchall()
    except:
        api_keys = []
    
    conn.close()
    
    # Available platforms for integration
    platforms = [
        {'name': 'Instagram', 'icon': 'instagram', 'status': 'available'},
        {'name': 'TikTok', 'icon': 'tiktok', 'status': 'available'},
        {'name': 'YouTube', 'icon': 'youtube', 'status': 'available'},
        {'name': 'Facebook', 'icon': 'facebook', 'status': 'available'},
        {'name': 'Twitter', 'icon': 'twitter', 'status': 'available'},
        {'name': 'Google Drive', 'icon': 'google', 'status': 'available'},
        {'name': 'Dropbox', 'icon': 'dropbox', 'status': 'available'},
        {'name': 'Slack', 'icon': 'slack', 'status': 'coming_soon'},
    ]
    
    return render_template("integrations.html",
                         integrations=integrations_list,
                         api_keys=api_keys,
                         platforms=platforms)

# ==================== NOTIFICATIONS ====================

@app.route("/notifications")
@login_required
def notifications():
    conn = get_db()
    
    # Get notifications
    c = conn.cursor()
    try:
        c.execute("""
            SELECT 
                id,
                type,
                title,
                message,
                is_read,
                created_at,
                action_url
            FROM notifications 
            WHERE username=?
            ORDER BY created_at DESC
            LIMIT 50
        """, (session['username'],))
        
        notifications_list = c.fetchall()
    except:
        notifications_list = []
    
    # Mark as read if requested
    mark_read = request.args.get('mark_read')
    if mark_read == 'all':
        try:
            c.execute("""
                UPDATE notifications SET is_read=1 
                WHERE username=? AND is_read=0
            """, (session['username'],))
            conn.commit()
            flash("✅ Semua notifikasi ditandai sebagai dibaca", "success")
        except:
            pass
    
    # Count unread
    try:
        c.execute("""
            SELECT COUNT(*) FROM notifications 
            WHERE username=? AND is_read=0
        """, (session['username'],))
        result = c.fetchone()
        unread_count = result[0] if result else 0
    except:
        unread_count = 0
    
    conn.close()
    
    return render_template("notifications.html",
                         notifications=notifications_list,
                         unread_count=unread_count)

@app.route("/notification/<int:notification_id>/read")
@login_required
def mark_notification_read(notification_id):
    conn = get_db()
    
    try:
        conn.execute("""
            UPDATE notifications SET is_read=1 
            WHERE id=? AND username=?
        """, (notification_id, session['username']))
        conn.commit()
    except:
        pass
    
    conn.close()
    
    return jsonify({'success': True})

@app.route("/notifications/clear")
@login_required
def clear_notifications():
    conn = get_db()
    
    try:
        conn.execute("DELETE FROM notifications WHERE username=?", (session['username'],))
        conn.commit()
        flash("✅ Semua notifikasi berhasil dihapus", "success")
    except:
        flash("❌ Gagal menghapus notifikasi", "error")
    
    conn.close()
    
    return redirect(url_for('notifications'))

@app.route("/api/notifications/unread-count")
@login_required
def api_unread_notifications():
    conn = get_db()
    c = conn.cursor()
    
    try:
        c.execute("""
            SELECT COUNT(*) FROM notifications 
            WHERE username=? AND is_read=0
        """, (session['username'],))
        result = c.fetchone()
        count = result[0] if result else 0
    except:
        count = 0
    
    conn.close()
    
    return jsonify({'count': count})

# ==================== CONTENT MANAGER DASHBOARD ====================

@app.route("/content-manager")
@login_required
def content_manager():
    """Show all accounts and categories for content management"""
    conn = get_db()
    c = conn.cursor()
    
    # Create dictionary with all zero values first
    counts_dict = {}
    for account in ACCOUNTS:
        for category in CATEGORIES:
            key = f"{account}_{category}"
            counts_dict[key] = 0
    
    # Get content counts for each account and category
    try:
        c.execute("""
            SELECT account, category, COUNT(*) as count 
            FROM content 
            GROUP BY account, category
            ORDER BY account, category
        """)
        content_counts = c.fetchall()
        
        # Update dictionary with actual counts
        for row in content_counts:
            key = f"{row['account']}_{row['category']}"
            counts_dict[key] = row['count']
    except Exception as e:
        print(f"Error fetching content counts: {e}")
    
    conn.close()
    
    return render_template("content_manager.html",
                         accounts=ACCOUNTS,
                         categories=CATEGORIES,
                         counts_dict=counts_dict)

# ==================== IDE MANAGER ====================

@app.route("/ide-manager", methods=["GET", "POST"])
@login_required
def ide_manager():
    """Halaman khusus untuk mengelola ide-ide kreatif"""
    conn = get_db()
    c = conn.cursor()
    
    if request.method == "POST":
        account = request.form.get("account")
        text = request.form.get("text", "").strip()
        tags = request.form.get("tags", "").strip()
        priority = request.form.get("priority", "normal")
        
        if text and account:
            try:
                c.execute("""
                    INSERT INTO content (account, category, text, tags, priority) 
                    VALUES (?, 'Ide', ?, ?, ?)
                """, (account, text, tags, priority))
                conn.commit()
                flash("✅ Ide berhasil disimpan!", "success")
                
                # Create notification
                create_notification(
                    session['username'],
                    'content',
                    'New Idea Added',
                    f'Added new idea to {account}',
                    url_for('ide_manager')
                )
                
            except Exception as e:
                flash(f"❌ Error: {str(e)}", "error")
        else:
            flash("❌ Semua field harus diisi", "error")
    
    # Get all ideas
    c.execute("""
        SELECT id, account, text, created_at, tags, priority 
        FROM content 
        WHERE category='Ide' 
        ORDER BY created_at DESC
    """)
    ide_data = c.fetchall()
    
    # Get idea counts per account
    c.execute("""
        SELECT account, COUNT(*) as count 
        FROM content 
        WHERE category='Ide' 
        GROUP BY account 
        ORDER BY count DESC
    """)
    ide_counts = c.fetchall()
    
    conn.close()
    
    return render_template("ide_manager.html",
                         ide_data=ide_data,
                         ide_counts=ide_counts,
                         accounts=ACCOUNTS)

@app.route("/delete_ide/<int:id>")
@login_required
def delete_ide(id):
    """Delete specific idea"""
    conn = get_db()
    c = conn.cursor()
    
    try:
        c.execute("DELETE FROM content WHERE id=? AND category='Ide'", (id,))
        conn.commit()
        flash("✅ Ide berhasil dihapus!", "success")
    except Exception as e:
        flash(f"❌ Error: {str(e)}", "error")
    
    conn.close()
    return redirect(url_for('ide_manager'))

# ==================== STOK MANAGER ====================

@app.route("/stok-manager", methods=["GET", "POST"])
@login_required
def stok_manager():
    """Halaman khusus untuk mengelola stok konten"""
    conn = get_db()
    c = conn.cursor()
    
    if request.method == "POST":
        account = request.form.get("account")
        text = request.form.get("text", "").strip()
        tags = request.form.get("tags", "").strip()
        priority = request.form.get("priority", "normal")
        
        if text and account:
            try:
                c.execute("""
                    INSERT INTO content (account, category, text, tags, priority) 
                    VALUES (?, 'Stok', ?, ?, ?)
                """, (account, text, tags, priority))
                conn.commit()
                flash("✅ Stok konten berhasil disimpan!", "success")
                
                # Create notification
                create_notification(
                    session['username'],
                    'content',
                    'New Stock Content Added',
                    f'Added new stock content to {account}',
                    url_for('stok_manager')
                )
                
            except Exception as e:
                flash(f"❌ Error: {str(e)}", "error")
        else:
            flash("❌ Semua field harus diisi", "error")
    
    # Get all stock content
    c.execute("""
        SELECT id, account, text, created_at, tags, priority 
        FROM content 
        WHERE category='Stok' 
        ORDER BY created_at DESC
    """)
    stok_data = c.fetchall()
    
    # Get stock counts per account
    c.execute("""
        SELECT account, COUNT(*) as count 
        FROM content 
        WHERE category='Stok' 
        GROUP BY account 
        ORDER BY count DESC
    """)
    stok_counts = c.fetchall()
    
    conn.close()
    
    return render_template("stok_manager.html",
                         stok_data=stok_data,
                         stok_counts=stok_counts,
                         accounts=ACCOUNTS)

# ==================== SKRIP MANAGER ====================

@app.route("/skrip-manager", methods=["GET", "POST"])
@login_required
def skrip_manager():
    """Halaman khusus untuk mengelola skrip konten"""
    conn = get_db()
    c = conn.cursor()
    
    if request.method == "POST":
        account = request.form.get("account")
        text = request.form.get("text", "").strip()
        tags = request.form.get("tags", "").strip()
        priority = request.form.get("priority", "normal")
        
        if text and account:
            try:
                c.execute("""
                    INSERT INTO content (account, category, text, tags, priority) 
                    VALUES (?, 'Skrip', ?, ?, ?)
                """, (account, text, tags, priority))
                conn.commit()
                flash("✅ Skrip berhasil disimpan!", "success")
                
                # Create notification
                create_notification(
                    session['username'],
                    'content',
                    'New Script Added',
                    f'Added new script to {account}',
                    url_for('skrip_manager')
                )
                
            except Exception as e:
                flash(f"❌ Error: {str(e)}", "error")
        else:
            flash("❌ Semua field harus diisi", "error")
    
    # Get all scripts
    c.execute("""
        SELECT id, account, text, created_at, tags, priority 
        FROM content 
        WHERE category='Skrip' 
        ORDER BY created_at DESC
    """)
    skrip_data = c.fetchall()
    
    # Get script counts per account
    c.execute("""
        SELECT account, COUNT(*) as count 
        FROM content 
        WHERE category='Skrip' 
        GROUP BY account 
        ORDER BY count DESC
    """)
    skrip_counts = c.fetchall()
    
    conn.close()
    
    return render_template("skrip_manager.html",
                         skrip_data=skrip_data,
                         skrip_counts=skrip_counts,
                         accounts=ACCOUNTS)

# ==================== STRATEGI MANAGER ====================

@app.route("/strategi-manager", methods=["GET", "POST"])
@login_required
def strategi_manager():
    """Halaman khusus untuk mengelola strategi konten"""
    conn = get_db()
    c = conn.cursor()
    
    if request.method == "POST":
        account = request.form.get("account")
        text = request.form.get("text", "").strip()
        tags = request.form.get("tags", "").strip()
        priority = request.form.get("priority", "normal")
        
        if text and account:
            try:
                c.execute("""
                    INSERT INTO content (account, category, text, tags, priority) 
                    VALUES (?, 'Strategi', ?, ?, ?)
                """, (account, text, tags, priority))
                conn.commit()
                flash("✅ Strategi berhasil disimpan!", "success")
                
                # Create notification
                create_notification(
                    session['username'],
                    'content',
                    'New Strategy Added',
                    f'Added new strategy to {account}',
                    url_for('strategi_manager')
                )
                
            except Exception as e:
                flash(f"❌ Error: {str(e)}", "error")
        else:
            flash("❌ Semua field harus diisi", "error")
    
    # Get all strategies
    c.execute("""
        SELECT id, account, text, created_at, tags, priority 
        FROM content 
        WHERE category='Strategi' 
        ORDER BY created_at DESC
    """)
    strategi_data = c.fetchall()
    
    # Get strategy counts per account
    c.execute("""
        SELECT account, COUNT(*) as count 
        FROM content 
        WHERE category='Strategi' 
        GROUP BY account 
        ORDER BY count DESC
    """)
    strategi_counts = c.fetchall()
    
    conn.close()
    
    return render_template("strategi_manager.html",
                         strategi_data=strategi_data,
                         strategi_counts=strategi_counts,
                         accounts=ACCOUNTS)

# ==================== CONTENT MANAGEMENT ====================

@app.route("/manage/<account>/<category>", methods=["GET", "POST"])
@login_required
def manage(account, category):
    conn = get_db()
    c = conn.cursor()

    if request.method == "POST":
        text = request.form.get("text", "").strip()
        tags = request.form.get("tags", "").strip()
        priority = request.form.get("priority", "normal")
        
        if text:
            try:
                c.execute("""
                    INSERT INTO content (account, category, text, tags, priority) 
                    VALUES (?,?,?,?,?)
                """, (account, category, text, tags, priority))
                conn.commit()
                flash("✅ Konten berhasil disimpan!", "success")
                
                # Create analytics entry
                content_id = c.lastrowid
                try:
                    c.execute("INSERT INTO content_analytics (content_id) VALUES (?)", (content_id,))
                    conn.commit()
                except:
                    pass
                
                # Create notification
                try:
                    create_notification(
                        session['username'],
                        'content',
                        'New Content Added',
                        f'Added new content to {account} - {category}',
                        url_for('manage', account=account, category=category)
                    )
                except:
                    pass
                
            except Exception as e:
                flash(f"❌ Error: {str(e)}", "error")
        else:
            flash("❌ Konten tidak boleh kosong", "error")
    
    # Get content with pagination
    page = request.args.get('page', 1, type=int)
    per_page = 20
    offset = (page - 1) * per_page
    
    # Search filter
    search = request.args.get('search', '').strip()
    
    # Build queries
    if search:
        # Get content with search filter
        c.execute("""
            SELECT id, text, created_at, tags, priority 
            FROM content 
            WHERE account=? AND category=? 
            AND (text LIKE ? OR tags LIKE ?)
            ORDER BY created_at DESC 
            LIMIT ? OFFSET ?
        """, (account, category, f'%{search}%', f'%{search}%', per_page, offset))
        
        data = c.fetchall()
        
        # Get total count for search
        c.execute("""
            SELECT COUNT(*) 
            FROM content 
            WHERE account=? AND category=? 
            AND (text LIKE ? OR tags LIKE ?)
        """, (account, category, f'%{search}%', f'%{search}%'))
        count_result = c.fetchone()
        total_count = count_result[0] if count_result else 0
    else:
        # Get content without search filter
        c.execute("""
            SELECT id, text, created_at, tags, priority 
            FROM content 
            WHERE account=? AND category=? 
            ORDER BY created_at DESC 
            LIMIT ? OFFSET ?
        """, (account, category, per_page, offset))
        
        data = c.fetchall()
        
        # Get total count
        c.execute("SELECT COUNT(*) FROM content WHERE account=? AND category=?", 
                 (account, category))
        count_result = c.fetchone()
        total_count = count_result[0] if count_result else 0
    
    total_pages = (total_count + per_page - 1) // per_page if total_count > 0 else 1
    
    # Get statistics
    c.execute("""
        SELECT 
            COUNT(*) as total,
            AVG(LENGTH(text)) as avg_length,
            MIN(created_at) as first_date,
            MAX(created_at) as last_date
        FROM content 
        WHERE account=? AND category=?
    """, (account, category))
    
    stats_result = c.fetchone()
    
    # Handle None stats result
    if stats_result:
        stats = {
            'total': stats_result['total'] or 0,
            'avg_length': float(stats_result['avg_length'] or 0),
            'first_date': stats_result['first_date'],
            'last_date': stats_result['last_date']
        }
    else:
        stats = {
            'total': 0,
            'avg_length': 0,
            'first_date': None,
            'last_date': None
        }
    
    conn.close()
    
    return render_template("manage.html",
                           account=account,
                           category=category,
                           data=data,
                           page=page,
                           total_pages=total_pages,
                           search=search,
                           stats=stats)

@app.route("/update_content", methods=["POST"])
@login_required
def update_content():
    conn = get_db()
    c = conn.cursor()
    
    content_id = request.form.get("id")
    text = request.form.get("text", "").strip()
    tags = request.form.get("tags", "").strip()
    priority = request.form.get("priority", "normal")
    
    if not content_id:
        return jsonify({'success': False, 'error': 'ID konten tidak valid'})
    
    if not text:
        return jsonify({'success': False, 'error': 'Konten tidak boleh kosong'})
    
    try:
        c.execute("""
            UPDATE content 
            SET text=?, tags=?, priority=?, updated_at=CURRENT_TIMESTAMP 
            WHERE id=?
        """, (text, tags, priority, content_id))
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True, 
            'message': 'Konten berhasil diupdate',
            'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'error': str(e)})

@app.route("/delete/<int:id>")
@login_required
def delete_content(id):
    conn = get_db()
    c = conn.cursor()
    
    try:
        # Get account and category for redirect
        c.execute("SELECT account, category FROM content WHERE id=?", (id,))
        content = c.fetchone()
        
        if content:
            # Delete analytics first
            try:
                c.execute("DELETE FROM content_analytics WHERE content_id=?", (id,))
            except:
                pass
            # Delete content
            c.execute("DELETE FROM content WHERE id=?", (id,))
            conn.commit()
            flash("✅ Konten berhasil dihapus!", "success")
            
            account = content['account']
            category = content['category']
            conn.close()
            return redirect(url_for('manage', account=account, category=category))
        else:
            flash("❌ Konten tidak ditemukan", "error")
            conn.close()
            return redirect(request.referrer or url_for('dashboard'))
    except Exception as e:
        conn.rollback()
        flash(f"❌ Error: {str(e)}", "error")
        conn.close()
        return redirect(request.referrer or url_for('dashboard'))

# ==================== DAILY NOTES ====================

@app.route("/daily-notes", methods=["GET", "POST"])
@login_required
def daily_notes():
    conn = get_db()
    c = conn.cursor()
    
    today = datetime.now().strftime("%Y-%m-%d")
    
    if request.method == "POST":
        date = request.form.get("date", today)
        note = request.form.get("note", "").strip()
        mood = request.form.get("mood", "neutral")
        
        if note:
            # Check if note exists for this date
            c.execute("SELECT id FROM daily_notes WHERE date=?", (date,))
            existing = c.fetchone()
            
            if existing:
                c.execute("""
                    UPDATE daily_notes 
                    SET note=?, mood=?, updated_at=CURRENT_TIMESTAMP 
                    WHERE date=?
                """, (note, mood, date))
                message = "Catatan harian berhasil diupdate!"
            else:
                c.execute("""
                    INSERT INTO daily_notes (date, note, mood) 
                    VALUES (?,?,?)
                """, (date, note, mood))
                message = "Catatan harian berhasil disimpan!"
            
            conn.commit()
            flash(f"✅ {message}", "success")
        else:
            flash("❌ Catatan tidak boleh kosong", "error")
    
    # Get today's note
    c.execute("SELECT note, mood, created_at FROM daily_notes WHERE date=?", (today,))
    today_note = c.fetchone()
    
    # Get recent notes (30 days)
    c.execute("""
        SELECT date, note, mood, created_at 
        FROM daily_notes 
        ORDER BY date DESC 
        LIMIT 30
    """)
    notes = c.fetchall()
    
    # Get notes statistics
    c.execute("""
        SELECT 
            COUNT(*) as total_notes,
            MIN(date) as first_note,
            MAX(date) as last_note,
            GROUP_CONCAT(mood) as moods
        FROM daily_notes
    """)
    stats_result = c.fetchone()
    
    if stats_result:
        stats = {
            'total_notes': stats_result['total_notes'] or 0,
            'first_note': stats_result['first_note'],
            'last_note': stats_result['last_note'],
            'moods': stats_result['moods']
        }
    else:
        stats = {
            'total_notes': 0,
            'first_note': None,
            'last_note': None,
            'moods': None
        }
    
    conn.close()
    
    return render_template("daily_notes.html", 
                         notes=notes, 
                         today_note=today_note, 
                         today=today,
                         stats=stats)

@app.route("/delete_note/<date>")
@login_required
def delete_note(date):
    conn = get_db()
    c = conn.cursor()
    
    try:
        c.execute("DELETE FROM daily_notes WHERE date=?", (date,))
        conn.commit()
        flash(f"✅ Catatan untuk tanggal {date} berhasil dihapus", "success")
    except:
        flash(f"❌ Gagal menghapus catatan", "error")
    
    conn.close()
    
    return redirect(url_for('daily_notes'))

# ==================== TASK MANAGER ====================

@app.route("/tasks", methods=["GET", "POST"])
@login_required
def tasks():
    conn = get_db()
    c = conn.cursor()
    
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        priority = request.form.get("priority", "medium")
        due_date = request.form.get("due_date")
        category = request.form.get("category", "")
        
        if title:
            try:
                c.execute("""
                    INSERT INTO tasks (title, description, priority, due_date, category) 
                    VALUES (?,?,?,?,?)
                """, (title, description, priority, due_date, category))
                conn.commit()
                flash("✅ Task berhasil ditambahkan!", "success")
                
                # Create notification
                try:
                    create_notification(
                        session['username'],
                        'task',
                        'New Task Created',
                        f'Created new task: {title}',
                        '/tasks'
                    )
                except:
                    pass
            except Exception as e:
                flash(f"❌ Error: {str(e)}", "error")
        else:
            flash("❌ Judul task tidak boleh kosong", "error")
    
    # Get filter parameters
    status_filter = request.args.get('status', 'all')
    priority_filter = request.args.get('priority', 'all')
    
    # Build query
    query = """
        SELECT id, title, description, status, priority, due_date, 
               created_at, completed_at, category 
        FROM tasks 
        WHERE 1=1
    """
    params = []
    
    if status_filter != 'all':
        query += " AND status = ?"
        params.append(status_filter)
    
    if priority_filter != 'all':
        query += " AND priority = ?"
        params.append(priority_filter)
    
    query += " ORDER BY CASE priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END, due_date ASC"
    
    try:
        c.execute(query, tuple(params))
        tasks_data = c.fetchall()
    except:
        tasks_data = []
    
    # Get task statistics
    try:
        c.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) as completed,
                SUM(CASE WHEN status='pending' THEN 1 ELSE 0 END) as pending,
                SUM(CASE WHEN status='in_progress' THEN 1 ELSE 0 END) as in_progress
            FROM tasks
        """)
        stats_result = c.fetchone()
        
        if stats_result:
            task_stats = {
                'total': stats_result['total'] or 0,
                'completed': stats_result['completed'] or 0,
                'pending': stats_result['pending'] or 0,
                'in_progress': stats_result['in_progress'] or 0
            }
        else:
            task_stats = {
                'total': 0,
                'completed': 0,
                'pending': 0,
                'in_progress': 0
            }
    except:
        task_stats = {
            'total': 0,
            'completed': 0,
            'pending': 0,
            'in_progress': 0
        }
    
    conn.close()
    
    return render_template("tasks.html", 
                         tasks=tasks_data, 
                         today=datetime.now().strftime("%Y-%m-%d"),
                         stats=task_stats,
                         status_filter=status_filter,
                         priority_filter=priority_filter)

@app.route("/update_task_status/<int:task_id>", methods=["POST"])
@login_required
def update_task_status(task_id):
    conn = get_db()
    c = conn.cursor()
    
    try:
        data = request.get_json()
        status = data.get('status', 'pending')
        
        completed_at = None
        if status == 'completed':
            completed_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        c.execute("""
            UPDATE tasks 
            SET status=?, completed_at=? 
            WHERE id=?
        """, (status, completed_at, task_id))
        
        conn.commit()
        
        # Get updated task
        c.execute("SELECT * FROM tasks WHERE id=?", (task_id,))
        task = dict(c.fetchone())
        
        conn.close()
        
        return jsonify({
            'success': True, 
            'task': task,
            'message': f'Status task berhasil diubah ke {status}'
        })
    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'error': str(e)})

@app.route("/delete_task/<int:task_id>")
@login_required
def delete_task(task_id):
    conn = get_db()
    c = conn.cursor()
    
    try:
        c.execute("DELETE FROM tasks WHERE id=?", (task_id,))
        conn.commit()
        conn.close()
        flash("✅ Task berhasil dihapus", "success")
    except Exception as e:
        flash(f"❌ Error: {str(e)}", "error")
    
    return redirect(url_for('tasks'))

# ==================== SEARCH ====================

@app.route("/search", methods=["GET"])
@login_required
def search():
    query = request.args.get('q', '').strip()
    search_type = request.args.get('type', 'all')
    
    if not query:
        return render_template("search.html", results=[], query="")
    
    conn = get_db()
    c = conn.cursor()
    
    search_pattern = f"%{query}%"
    results = []
    
    try:
        if search_type in ['all', 'content']:
            # Search in content
            c.execute("""
                SELECT id, account, category, text, created_at, tags 
                FROM content 
                WHERE text LIKE ? OR tags LIKE ?
                ORDER BY created_at DESC
                LIMIT 50
            """, (search_pattern, search_pattern))
            content_results = c.fetchall()
            for row in content_results:
                results.append({
                    'type': 'content',
                    'id': row['id'],
                    'account': row['account'],
                    'category': row['category'],
                    'text': row['text'],
                    'date': row['created_at'],
                    'tags': row['tags']
                })
        
        if search_type in ['all', 'notes']:
            # Search in daily notes
            c.execute("""
                SELECT date, note, mood, created_at 
                FROM daily_notes 
                WHERE note LIKE ?
                ORDER BY date DESC
                LIMIT 20
            """, (search_pattern,))
            note_results = c.fetchall()
            for row in note_results:
                results.append({
                    'type': 'note',
                    'date': row['date'],
                    'text': row['note'],
                    'mood': row['mood'],
                    'created_at': row['created_at']
                })
        
        if search_type in ['all', 'tasks']:
            # Search in tasks
            c.execute("""
                SELECT id, title, description, status, priority, created_at 
                FROM tasks 
                WHERE title LIKE ? OR description LIKE ?
                ORDER BY created_at DESC
                LIMIT 20
            """, (search_pattern, search_pattern))
            task_results = c.fetchall()
            for row in task_results:
                results.append({
                    'type': 'task',
                    'id': row['id'],
                    'title': row['title'],
                    'description': row['description'],
                    'status': row['status'],
                    'priority': row['priority'],
                    'created_at': row['created_at']
                })
    except Exception as e:
        print(f"Error searching: {e}")
    
    conn.close()
    
    return render_template("search.html", 
                         results=results, 
                         query=query, 
                         search_type=search_type,
                         result_count=len(results))

# ==================== STATISTICS ====================

@app.route("/statistics")
@login_required
def statistics():
    conn = get_db()
    c = conn.cursor()
    
    # General statistics
    try:
        c.execute("SELECT COUNT(*) FROM content")
        total_result = c.fetchone()
        total_content = total_result[0] if total_result else 0
        
        c.execute("SELECT COUNT(DISTINCT date) FROM daily_notes")
        notes_result = c.fetchone()
        total_notes_days = notes_result[0] if notes_result else 0
        
        c.execute("SELECT COUNT(*) FROM tasks WHERE status='completed'")
        tasks_result = c.fetchone()
        completed_tasks = tasks_result[0] if tasks_result else 0
    except:
        total_content = 0
        total_notes_days = 0
        completed_tasks = 0
    
    # Content by account
    try:
        c.execute("""
            SELECT account, COUNT(*) as count 
            FROM content 
            GROUP BY account 
            ORDER BY count DESC
        """)
        content_by_account = c.fetchall()
    except:
        content_by_account = []
    
    # Content by category
    try:
        c.execute("""
            SELECT category, COUNT(*) as count 
            FROM content 
            GROUP BY category 
            ORDER BY count DESC
        """)
        content_by_category = c.fetchall()
    except:
        content_by_category = []
    
    # Daily activity (last 30 days)
    try:
        c.execute("""
            SELECT DATE(created_at) as date, COUNT(*) as count
            FROM content
            WHERE created_at >= date('now', '-30 days')
            GROUP BY DATE(created_at)
            ORDER BY date
        """)
        daily_activity = c.fetchall()
    except:
        daily_activity = []
    
    conn.close()
    
    return render_template("statistics.html",
                         total_content=total_content,
                         total_notes_days=total_notes_days,
                         completed_tasks=completed_tasks,
                         content_by_account=content_by_account,
                         content_by_category=content_by_category,
                         daily_activity=daily_activity)

# ==================== SYSTEM INFO ====================

@app.route("/system_info")
@login_required
def system_info():
    """Show system information"""
    
    info = {
        'python_version': sys.version,
        'platform': platform.platform(),
        'flask_version': '2.3.3',
        'database_size': 0,
        'content_count': 0,
        'notes_count': 0,
        'tasks_count': 0
    }
    
    try:
        if os.path.exists('database.db'):
            info['database_size'] = os.path.getsize('database.db')
    except:
        pass
    
    try:
        conn = get_db()
        c = conn.cursor()
        
        c.execute("SELECT COUNT(*) FROM content")
        content_result = c.fetchone()
        info['content_count'] = content_result[0] if content_result else 0
        
        c.execute("SELECT COUNT(*) FROM daily_notes")
        notes_result = c.fetchone()
        info['notes_count'] = notes_result[0] if notes_result else 0
        
        c.execute("SELECT COUNT(*) FROM tasks")
        tasks_result = c.fetchone()
        info['tasks_count'] = tasks_result[0] if tasks_result else 0
        
        conn.close()
    except:
        pass
    
    return render_template("system_info.html", info=info)

# ==================== EXPORT & IMPORT ====================

@app.route("/export/<account>/<category>")
@login_required
def export(account, category):
    format_type = request.args.get('format', 'txt')
    include_date = request.args.get('date', 'false') == 'true'
    include_tags = request.args.get('tags', 'false') == 'true'
    start_date = request.args.get('start')
    end_date = request.args.get('end')
    
    conn = get_db()
    c = conn.cursor()
    
    # Build query
    query = "SELECT text, created_at, tags FROM content WHERE account=? AND category=?"
    params = [account, category]
    
    if start_date and end_date:
        query += " AND DATE(created_at) BETWEEN ? AND ?"
        params.extend([start_date, end_date])
    
    query += " ORDER BY created_at"
    
    try:
        c.execute(query, tuple(params))
        rows = c.fetchall()
    except:
        rows = []
    
    conn.close()
    
    if format_type == 'json':
        data = []
        for row in rows:
            item = {'content': row['text']}
            if include_date:
                item['date'] = row['created_at']
            if include_tags and row['tags']:
                item['tags'] = row['tags']
            data.append(item)
        
        content = json.dumps(data, indent=2, ensure_ascii=False)
        mimetype = 'application/json'
        filename = f"{account}_{category}_{datetime.now().strftime('%Y%m%d')}.json"
        
    elif format_type == 'csv':
        output = BytesIO()
        writer = csv.writer(output)
        
        headers = ['No', 'Content']
        if include_date:
            headers.append('Date')
        if include_tags:
            headers.append('Tags')
        
        writer.writerow(headers)
        
        for i, row in enumerate(rows, 1):
            row_data = [i, row['text']]
            if include_date:
                row_data.append(row['created_at'])
            if include_tags:
                row_data.append(row['tags'] or '')
            writer.writerow(row_data)
        
        content = output.getvalue()
        mimetype = 'text/csv'
        filename = f"{account}_{category}_{datetime.now().strftime('%Y%m%d')}.csv"
        
    else:  # txt format (default)
        content = f"=== EKSPOR KONTEN ===\n"
        content += f"Akun: {account}\n"
        content += f"Kategori: {category}\n"
        content += f"Tanggal Ekspor: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        content += f"Jumlah Item: {len(rows)}\n"
        content += "="*50 + "\n\n"
        
        for i, row in enumerate(rows, 1):
            content += f"Item #{i}\n"
            if include_date:
                content += f"Tanggal: {row['created_at']}\n"
            if include_tags and row['tags']:
                content += f"Tags: {row['tags']}\n"
            content += "-"*30 + "\n"
            content += row['text'] + "\n\n"
            content += "="*50 + "\n\n"
        
        content = content.encode('utf-8')
        mimetype = 'text/plain'
        filename = f"{account}_{category}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    
    file = BytesIO()
    file.write(content if isinstance(content, bytes) else content.encode('utf-8'))
    file.seek(0)
    
    # Log backup
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("INSERT INTO backup_history (filename, item_count, backup_type) VALUES (?,?,?)",
                  (filename, len(rows), format_type))
        conn.commit()
        conn.close()
    except:
        pass
    
    return send_file(file,
                     as_attachment=True,
                     download_name=filename,
                     mimetype=mimetype)

@app.route("/backup")
@login_required
def backup():
    """Create full backup"""
    try:
        conn = get_db()
        
        # Create backup file
        backup_data = {}
        
        # Backup content
        content = conn.execute("SELECT * FROM content").fetchall()
        backup_data['content'] = [dict(row) for row in content]
        
        # Backup daily notes
        notes = conn.execute("SELECT * FROM daily_notes").fetchall()
        backup_data['daily_notes'] = [dict(row) for row in notes]
        
        # Backup tasks
        tasks = conn.execute("SELECT * FROM tasks").fetchall()
        backup_data['tasks'] = [dict(row) for row in tasks]
        
        # Backup users
        users = conn.execute("SELECT * FROM users").fetchall()
        backup_data['users'] = [dict(row) for row in users]
        
        conn.close()
        
        # Create backup file
        filename = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, indent=2, default=str, ensure_ascii=False)
        
        flash(f"✅ Backup berhasil dibuat: {filename}", "success")
    except Exception as e:
        flash(f"❌ Error creating backup: {str(e)}", "error")
    
    return redirect(url_for('dashboard'))

@app.route("/clear_cache")
@login_required
def clear_cache():
    """Clear application cache"""
    flash("✅ Cache berhasil dibersihkan", "success")
    return redirect(request.referrer or url_for('dashboard'))

# ==================== ERROR HANDLERS ====================

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500

# ==================== INITIALIZATION ====================

if __name__ == "__main__":
    # Create database tables
    try:
        init_db()
        print("✅ Database initialized successfully")
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
    
    # Upgrade database if needed
    try:
        upgrade_db()
        print("✅ Database upgrade completed")
    except Exception as e:
        print(f"❌ Error upgrading database: {e}")
    
    # Run the app
    print("="*50)
    print("Affiliate Content Manager Pro")
    print("="*50)
    print(f"URL: http://localhost:5000")
    print(f"Username: Kenas Walfredon")
    print(f"Password: kenasganteng")
    print("="*50)
    
    app.run(
        debug=True, 
        host='0.0.0.0', 
        port=5000,
        threaded=True
    )