import os
import json
import uuid
import secrets
from datetime import datetime, timedelta, timezone
from functools import wraps
from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, jsonify, abort
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

# --- App Configuration & Paths ---
app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'a_very_secret_key_for_development_v10')
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=8)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max upload

NOTIFICATIONS_FILE = 'notifications.json'
USERS_FILE = 'users.json'
CONFIG_FILE = 'site_config.json'
CALENDAR_FILE = 'calendar_events.json'
RECOVERY_KEY_FILE = 'admin_recovery.key'

UPLOAD_FOLDER = os.path.join('static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Timezone: Asia/Kolkata (IST = UTC+5:30)
IST = timezone(timedelta(hours=5, minutes=30))

def get_now_ist():
    """Returns current datetime in Asia/Kolkata timezone."""
    return datetime.now(IST)

def parse_iso(dt_str):
    """Safely parses ISO datetime string to an IST-aware datetime object."""
    if not dt_str:
        return None
    try:
        dt = datetime.fromisoformat(dt_str)
        if dt.tzinfo is None:
            # Treat naive timestamps stored by form inputs as IST
            dt = dt.replace(tzinfo=IST)
        else:
            dt = dt.astimezone(IST)
        return dt
    except (ValueError, TypeError):
        return None

# --- Helpers ---
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'pdf', 'png', 'jpg', 'jpeg', 'docx', 'xlsx'}

def read_json(file_path):
    is_list_based = ('users' in file_path or 'notifications' in file_path or 'calendar' in file_path)
    default_return = [] if is_list_based else {}
    if not os.path.exists(file_path):
        return default_return
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            return json.loads(content) if content else default_return
    except (json.JSONDecodeError, IOError):
        return default_return

def write_json(file_path, data):
    """Atomic write to prevent file corruption."""
    temp_path = f"{file_path}.tmp"
    with open(temp_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)
    os.replace(temp_path, file_path)

def normalize_notification(n):
    """Ensures consistent fields and backward compatibility for notification objects."""
    if not isinstance(n, dict):
        return n
    # Normalize status: 'published', 'draft', 'scheduled', 'archived'
    if 'status' not in n or not n['status']:
        if n.get('type') == 'archive':
            n['status'] = 'archived'
        else:
            n['status'] = 'published'

    # Normalize department and year to lists
    dept = n.get('department', [])
    if isinstance(dept, str):
        n['department'] = [dept] if dept else ['all']
    elif not isinstance(dept, list):
        n['department'] = ['all']

    year = n.get('year', [])
    if isinstance(year, str):
        n['year'] = [year] if year else ['all']
    elif not isinstance(year, list):
        n['year'] = ['all']

    return n

def verify_password(stored_password, provided_password):
    """Verifies password using hash or legacy plaintext fallback."""
    if not stored_password or not provided_password:
        return False
    if stored_password.startswith(('scrypt:', 'pbkdf2:', 'argon2:')):
        return check_password_hash(stored_password, provided_password)
    return stored_password == provided_password

def cleanup_unused_files():
    """Scans for and deletes files in uploads folder that are no longer referenced."""
    all_notifications = read_json(NOTIFICATIONS_FILE)
    site_config = read_json(CONFIG_FILE)
    calendar_events = read_json(CALENDAR_FILE)
    used_filenames = set()

    for notif in all_notifications:
        url = notif.get('attachment_url', '')
        if url and '/static/uploads/' in url:
            used_filenames.add(url.split('/')[-1])

    for link in site_config.get('quick_links', []):
        url = link.get('url', '')
        if url and '/static/uploads/' in url:
            used_filenames.add(url.split('/')[-1])

    for ev in calendar_events:
        url = ev.get('attachment_url', '')
        if url and '/static/uploads/' in url:
            used_filenames.add(url.split('/')[-1])

    if not os.path.exists(UPLOAD_FOLDER):
        return
    for filename in os.listdir(UPLOAD_FOLDER):
        if filename not in used_filenames:
            try:
                os.remove(os.path.join(UPLOAD_FOLDER, filename))
            except OSError as e:
                print(f"Error deleting file {filename}: {e}")

# --- CSRF Protection ---
@app.before_request
def ensure_csrf_token():
    if '_csrf_token' not in session:
        session['_csrf_token'] = secrets.token_hex(24)

def get_csrf_token():
    if '_csrf_token' not in session:
        session['_csrf_token'] = secrets.token_hex(24)
    return session['_csrf_token']

@app.context_processor
def inject_csrf_and_config():
    site_config = read_json(CONFIG_FILE)
    return {
        'csrf_token': get_csrf_token(),
        'site_config': site_config,
        'departments': site_config.get('departments', []),
        'academic_years': site_config.get('academic_years', []),
        'notification_types': site_config.get('notification_types', []),
        'exam_types': site_config.get('exam_types', [])
    }

def csrf_protect(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if app.config.get('TESTING') and not app.config.get('WTF_CSRF_ENABLED', True):
            return f(*args, **kwargs)
        if request.method == 'POST':
            token = request.form.get('csrf_token') or request.headers.get('X-CSRF-Token')
            if not token or token != session.get('_csrf_token'):
                flash('Invalid or expired security token. Please try again.', 'error')
                return redirect(request.referrer or url_for('admin_dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

# --- USER-FACING ROUTES ---
@app.route('/')
def index():
    site_config = read_json(CONFIG_FILE)
    quick_links = site_config.get('quick_links', [])
    calendar_url = '#exam-calendar'
    for link in quick_links:
        if 'calendar' in link.get('title', '').lower():
            calendar_url = link.get('url', '#exam-calendar')
            break
    return render_template(
        'index.html',
        quick_links=quick_links,
        calendar_url=calendar_url,
        site_config=site_config
    )

@app.route('/api/config')
def api_config():
    """Returns public institutional configuration (departments, years, types)."""
    site_config = read_json(CONFIG_FILE)
    return jsonify({
        'departments': site_config.get('departments', []),
        'academic_years': site_config.get('academic_years', []),
        'notification_types': site_config.get('notification_types', []),
        'exam_types': site_config.get('exam_types', []),
        'portal_settings': site_config.get('portal_settings', {})
    })

@app.route('/api/notifications')
def api_notifications():
    all_notifs = read_json(NOTIFICATIONS_FILE)
    now = get_now_ist()
    updated = False

    active_notifs = []
    archived_notifs = []

    for n in all_notifs:
        n = normalize_notification(n)

        # Scheduled notification auto-publication check
        if n.get('status') == 'scheduled':
            pub_dt = parse_iso(n.get('start_datetime'))
            if pub_dt and pub_dt <= now:
                n['status'] = 'published'
                updated = True

        # STRICT SECURITY: Drafts and future scheduled notifications are NEVER exposed
        if n.get('status') == 'draft':
            continue
        if n.get('status') == 'scheduled':
            pub_dt = parse_iso(n.get('start_datetime'))
            if not pub_dt or pub_dt > now:
                continue

        # Archive check
        if n.get('status') == 'archived' or n.get('type') == 'archive':
            archived_notifs.append(n)
            continue

        # Check timed expiry
        if n.get('end_datetime'):
            end_dt = parse_iso(n.get('end_datetime'))
            if end_dt and end_dt < now:
                n['status'] = 'archived'
                n['type'] = 'archive'
                archived_notifs.append(n)
                updated = True
                continue

        # Dynamic urgency tags for student awareness
        dynamic_type = n.get('type', 'info')
        if n.get('end_datetime'):
            end_dt = parse_iso(n['end_datetime'])
            if end_dt and end_dt >= now:
                time_left = end_dt - now
                if time_left <= timedelta(days=3):
                    dynamic_type = 'urgent'
                elif time_left <= timedelta(days=7) and dynamic_type != 'urgent':
                    dynamic_type = 'upcoming'

        n_copy = dict(n)
        n_copy['type'] = dynamic_type
        active_notifs.append(n_copy)

    if updated:
        write_json(NOTIFICATIONS_FILE, all_notifs)

    active_notifs.sort(key=lambda x: x.get('start_datetime', '1970-01-01T00:00:00'), reverse=True)
    archived_notifs.sort(key=lambda x: x.get('start_datetime', '1970-01-01T00:00:00'), reverse=True)

    # Filtering parameters
    dept_filter = request.args.get('department')
    year_filter = request.args.get('year')
    search_query = request.args.get('search', '').strip().lower()
    category_filter = request.args.get('category', '').strip()
    timeframe = request.args.get('timeframe', '').strip()

    # Search & Advanced Filters helper
    def matches_filters(item):
        if search_query:
            title_text = item.get('title', '').lower()
            body_text = item.get('body', '').lower()
            if search_query not in title_text and search_query not in body_text:
                return False

        if category_filter and category_filter != 'all':
            if item.get('type') != category_filter:
                return False

        if dept_filter and dept_filter != 'all':
            depts = item.get('department', [])
            if 'all' not in depts and dept_filter not in depts:
                return False

        if year_filter and year_filter != 'all':
            years = item.get('year', [])
            if 'all' not in years and year_filter not in years:
                return False

        if timeframe:
            item_dt = parse_iso(item.get('start_datetime'))
            if item_dt:
                age = now - item_dt
                if timeframe == '7days' and age > timedelta(days=7):
                    return False
                elif timeframe == '30days' and age > timedelta(days=30):
                    return False
                elif timeframe == 'semester' and age > timedelta(days=180):
                    return False

        return True

    # Filtered active list for student dashboard / search
    filtered_active = [n for n in active_notifs if matches_filters(n)]

    # Pagination calculation
    page = max(1, int(request.args.get('page', 1)))
    site_config = read_json(CONFIG_FILE)
    default_limit = site_config.get('portal_settings', {}).get('notifications_per_page', 5)
    limit = max(1, int(request.args.get('limit', default_limit)))

    total_filtered = len(filtered_active)
    total_pages = max(1, (total_filtered + limit - 1) // limit)
    offset = (page - 1) * limit
    paginated_results = filtered_active[offset:offset + limit]

    # Maintain existing response keys for complete backward compatibility
    response_data = {
        'guidelines': [n for n in active_notifs if n.get('type') == 'guideline'],
        'common': [
            n for n in active_notifs
            if ('all' in n.get('department', []) or not n.get('department')) and
               ('all' in n.get('year', []) or not n.get('year')) and
               n.get('type') in ['common', 'info', 'urgent', 'upcoming']
        ],
        'archive': archived_notifs,
        'departmental': [],
        # Enhanced fields for search, filtering, and pagination
        'filtered': paginated_results,
        'pagination': {
            'total': total_filtered,
            'page': page,
            'limit': limit,
            'total_pages': total_pages
        }
    }

    if dept_filter and year_filter:
        response_data['departmental'] = [
            n for n in active_notifs
            if ('all' in n.get('department', []) or dept_filter in n.get('department', [])) and
               ('all' in n.get('year', []) or year_filter in n.get('year', [])) and
               n.get('type') == 'departmental'
        ]

    return jsonify(response_data)

@app.route('/api/calendar')
def api_calendar():
    """Returns examination calendar entries, supporting department and year filters."""
    calendar_events = read_json(CALENDAR_FILE)
    dept_filter = request.args.get('department')
    year_filter = request.args.get('year')

    filtered_events = []
    for ev in calendar_events:
        depts = ev.get('departments', ['all'])
        years = ev.get('years', ['all'])

        if dept_filter and dept_filter != 'all':
            if 'all' not in depts and dept_filter not in depts:
                continue

        if year_filter and year_filter != 'all':
            if 'all' not in years and year_filter not in years:
                continue

        filtered_events.append(ev)

    # Sort chronologically by date
    filtered_events.sort(key=lambda x: x.get('date', '9999-12-31'))
    return jsonify(filtered_events)

# --- ADMIN PANEL ROUTES ---
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        users = read_json(USERS_FILE)
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        user = next((u for u in users if isinstance(u, dict) and u.get('username') == username), None)
        if user and verify_password(user.get('password', ''), password):
            # If stored password is still legacy plaintext, upgrade to secure hash immediately
            if not user.get('password', '').startswith(('scrypt:', 'pbkdf2:', 'argon2:')):
                user['password'] = generate_password_hash(password)
                write_json(USERS_FILE, users)

            session['logged_in'] = True
            session['username'] = username
            flash('Logged in successfully.', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid username or password.', 'error')

    return render_template('login.html')

@app.route('/admin/recover', methods=['GET', 'POST'])
def admin_recover():
    """Authorized recovery endpoint using server-generated emergency recovery key."""
    if request.method == 'POST':
        recovery_key = request.form.get('recovery_key', '').strip()
        username = request.form.get('username', '').strip() or 'admin'
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not recovery_key:
            flash('Emergency recovery key is required.', 'error')
            return render_template('login.html', show_recover=True)

        if not new_password or len(new_password) < 6:
            flash('New password must be at least 6 characters.', 'error')
            return render_template('login.html', show_recover=True)

        if new_password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('login.html', show_recover=True)

        # Check recovery key from file or environment variable
        stored_key = ''
        if os.path.exists(RECOVERY_KEY_FILE):
            with open(RECOVERY_KEY_FILE, 'r', encoding='utf-8') as f:
                stored_key = f.read().strip()
        elif 'ADMIN_RECOVERY_KEY' in os.environ:
            stored_key = os.environ['ADMIN_RECOVERY_KEY'].strip()

        if not stored_key or not secrets.compare_digest(stored_key, recovery_key):
            flash('Invalid recovery key. Technical administrator authorization required.', 'error')
            return render_template('login.html', show_recover=True)

        # Reset password securely
        users = read_json(USERS_FILE)
        hashed = generate_password_hash(new_password)
        found = False
        for u in users:
            if isinstance(u, dict) and u.get('username') == username:
                u['password'] = hashed
                found = True
                break
        if not found:
            users.append({'username': username, 'password': hashed})

        write_json(USERS_FILE, users)

        # Rotate recovery key after successful recovery for security
        new_token = secrets.token_urlsafe(32)
        with open(RECOVERY_KEY_FILE, 'w', encoding='utf-8') as f:
            f.write(new_token.strip())

        flash('Password successfully reset! You can now log in with your new password.', 'success')
        return redirect(url_for('admin_login'))

    return render_template('login.html', show_recover=True)

@app.route('/admin/change-password', methods=['POST'])
@login_required
@csrf_protect
def admin_change_password():
    users = read_json(USERS_FILE)
    username = session.get('username', 'admin')
    current_pass = request.form.get('current_password', '')
    new_pass = request.form.get('new_password', '')
    confirm_pass = request.form.get('confirm_password', '')

    user = next((u for u in users if isinstance(u, dict) and u.get('username') == username), None)
    if not user or not verify_password(user.get('password', ''), current_pass):
        flash('Incorrect current password.', 'error')
        return redirect(url_for('admin_dashboard'))

    if len(new_pass) < 6:
        flash('New password must be at least 6 characters long.', 'error')
        return redirect(url_for('admin_dashboard'))

    if new_pass != confirm_pass:
        flash('New passwords do not match.', 'error')
        return redirect(url_for('admin_dashboard'))

    user['password'] = generate_password_hash(new_pass)
    write_json(USERS_FILE, users)
    flash('Admin password updated successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/logout')
def admin_logout():
    session.pop('logged_in', None)
    session.pop('username', None)
    flash('Logged out successfully.', 'success')
    return redirect(url_for('admin_login'))

@app.route('/admin')
@login_required
def admin_dashboard():
    notifications = read_json(NOTIFICATIONS_FILE)
    calendar_events = read_json(CALENDAR_FILE)
    now = get_now_ist()
    updated = False

    for notif in notifications:
        notif = normalize_notification(notif)
        # Check auto-publish for scheduled
        if notif.get('status') == 'scheduled':
            pub_dt = parse_iso(notif.get('start_datetime'))
            if pub_dt and pub_dt <= now:
                notif['status'] = 'published'
                updated = True

        # Check auto-archive for expired
        if notif.get('status') == 'published' and notif.get('end_datetime'):
            end_dt = parse_iso(notif['end_datetime'])
            if end_dt and end_dt < now:
                notif['status'] = 'archived'
                notif['type'] = 'archive'
                updated = True

    if updated:
        write_json(NOTIFICATIONS_FILE, notifications)

    site_config = read_json(CONFIG_FILE)

    active_notifications = [n for n in notifications if n.get('status') == 'published']
    scheduled_notifications = [n for n in notifications if n.get('status') == 'scheduled']
    draft_notifications = [n for n in notifications if n.get('status') == 'draft']
    archived_notifications = [n for n in notifications if n.get('status') == 'archived']

    # Sort each list
    active_notifications.sort(key=lambda x: x.get('start_datetime', ''), reverse=True)
    scheduled_notifications.sort(key=lambda x: x.get('start_datetime', ''))
    draft_notifications.sort(key=lambda x: x.get('start_datetime', ''), reverse=True)
    archived_notifications.sort(key=lambda x: x.get('start_datetime', ''), reverse=True)
    calendar_events.sort(key=lambda x: x.get('date', ''))

    return render_template(
        'admin.html',
        active_notifications=active_notifications,
        scheduled_notifications=scheduled_notifications,
        draft_notifications=draft_notifications,
        archived_notifications=archived_notifications,
        calendar_events=calendar_events,
        quick_links=site_config.get('quick_links', []),
        site_config=site_config
    )

@app.route('/admin/add', methods=['POST'])
@login_required
@csrf_protect
def add_notification():
    notifications = read_json(NOTIFICATIONS_FILE)
    attachment_path = ''

    if 'attachment_file' in request.files:
        file = request.files['attachment_file']
        if file and file.filename != '' and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            # Prefix timestamp to avoid filename clashes
            unique_filename = f"{int(datetime.now().timestamp())}_{filename}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_filename))
            attachment_path = url_for('static', filename=f'uploads/{unique_filename}', _external=True)

    publish_action = request.form.get('publish_action', 'publish')
    start_dt = request.form.get('start_datetime')

    if publish_action == 'draft':
        status = 'draft'
        if not start_dt:
            start_dt = get_now_ist().strftime('%Y-%m-%dT%H:%M')
    elif publish_action == 'schedule':
        status = 'scheduled'
        if not start_dt:
            flash('Scheduled notifications require a valid future start date and time.', 'error')
            return redirect(url_for('admin_dashboard'))
    else:
        status = 'published'
        if not start_dt:
            start_dt = get_now_ist().strftime('%Y-%m-%dT%H:%M')

    departments = request.form.getlist('department')
    if not departments:
        departments = ['all']

    years = request.form.getlist('year')
    if not years:
        years = ['all']

    new_notif = {
        'id': str(uuid.uuid4()),
        'title': request.form.get('title', '').strip(),
        'body': request.form.get('body', '').strip(),
        'type': request.form.get('type', 'common'),
        'status': status,
        'department': departments,
        'year': years,
        'attachment_url': attachment_path if attachment_path else request.form.get('attachment_url', '').strip(),
        'is_popup': 'is_popup' in request.form,
        'start_datetime': start_dt,
        'end_datetime': request.form.get('end_datetime') if request.form.get('expiry_type') == 'timed' and request.form.get('end_datetime') else None
    }

    notifications.append(new_notif)
    write_json(NOTIFICATIONS_FILE, notifications)

    if status == 'draft':
        flash('Notification saved as draft!', 'success')
    elif status == 'scheduled':
        flash('Notification scheduled successfully!', 'success')
    else:
        flash('Notification published successfully!', 'success')

    return redirect(url_for('admin_dashboard'))

@app.route('/admin/edit/<notification_id>', methods=['POST'])
@login_required
@csrf_protect
def edit_notification(notification_id):
    notifications = read_json(NOTIFICATIONS_FILE)
    found = False

    for notif in notifications:
        if notif.get('id') == notification_id:
            found = True
            attachment_path = notif.get('attachment_url', '')

            if request.form.get('attach_type') == 'file' and 'attachment_file' in request.files:
                file = request.files['attachment_file']
                if file and file.filename != '' and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    unique_filename = f"{int(datetime.now().timestamp())}_{filename}"
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_filename))
                    attachment_path = url_for('static', filename=f'uploads/{unique_filename}', _external=True)
            elif request.form.get('attach_type') == 'url':
                attachment_path = request.form.get('attachment_url', '').strip()

            publish_action = request.form.get('publish_action')
            status = notif.get('status', 'published')
            if publish_action == 'draft':
                status = 'draft'
            elif publish_action == 'schedule':
                status = 'scheduled'
            elif publish_action == 'publish':
                status = 'published'

            departments = request.form.getlist('department')
            if not departments:
                departments = ['all']

            years = request.form.getlist('year')
            if not years:
                years = ['all']

            notif.update({
                'title': request.form.get('title', '').strip(),
                'body': request.form.get('body', '').strip(),
                'type': request.form.get('type', notif.get('type', 'common')),
                'status': status,
                'department': departments,
                'year': years,
                'is_popup': 'is_popup' in request.form,
                'start_datetime': request.form.get('start_datetime') or notif.get('start_datetime'),
                'end_datetime': request.form.get('end_datetime') if request.form.get('expiry_type') == 'timed' and request.form.get('end_datetime') else None,
                'attachment_url': attachment_path
            })
            break

    if found:
        write_json(NOTIFICATIONS_FILE, notifications)
        cleanup_unused_files()
        flash('Notification updated successfully!', 'success')
    else:
        flash('Notification not found.', 'error')

    return redirect(url_for('admin_dashboard'))

@app.route('/admin/publish/<notification_id>', methods=['POST'])
@login_required
@csrf_protect
def publish_draft_notification(notification_id):
    """Directly publishes a draft or scheduled notification."""
    notifications = read_json(NOTIFICATIONS_FILE)
    found = False
    for notif in notifications:
        if notif.get('id') == notification_id:
            notif['status'] = 'published'
            notif['start_datetime'] = get_now_ist().strftime('%Y-%m-%dT%H:%M')
            found = True
            break

    if found:
        write_json(NOTIFICATIONS_FILE, notifications)
        flash('Notification published successfully!', 'success')
    else:
        flash('Notification not found.', 'error')

    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete/<notification_id>', methods=['POST'])
@login_required
@csrf_protect
def delete_notification(notification_id):
    notifications = [n for n in read_json(NOTIFICATIONS_FILE) if n.get('id') != notification_id]
    write_json(NOTIFICATIONS_FILE, notifications)
    cleanup_unused_files()
    flash('Notification deleted successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

# --- CALENDAR ADMIN ROUTES ---
@app.route('/admin/calendar/add', methods=['POST'])
@login_required
@csrf_protect
def add_calendar_event():
    calendar_events = read_json(CALENDAR_FILE)
    departments = request.form.getlist('departments') or ['all']
    years = request.form.getlist('years') or ['all']

    new_event = {
        'id': f"cal-{uuid.uuid4().hex[:8]}",
        'title': request.form.get('title', '').strip(),
        'exam_type': request.form.get('exam_type', 'other'),
        'date': request.form.get('date', '').strip(),
        'time_session': request.form.get('time_session', '').strip(),
        'departments': departments,
        'years': years,
        'venue': request.form.get('venue', '').strip(),
        'description': request.form.get('description', '').strip()
    }
    calendar_events.append(new_event)
    write_json(CALENDAR_FILE, calendar_events)
    flash('Examination calendar entry added successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/calendar/edit/<event_id>', methods=['POST'])
@login_required
@csrf_protect
def edit_calendar_event(event_id):
    calendar_events = read_json(CALENDAR_FILE)
    found = False
    for ev in calendar_events:
        if ev.get('id') == event_id:
            found = True
            departments = request.form.getlist('departments') or ['all']
            years = request.form.getlist('years') or ['all']
            ev.update({
                'title': request.form.get('title', '').strip(),
                'exam_type': request.form.get('exam_type', ev.get('exam_type', 'other')),
                'date': request.form.get('date', '').strip(),
                'time_session': request.form.get('time_session', '').strip(),
                'departments': departments,
                'years': years,
                'venue': request.form.get('venue', '').strip(),
                'description': request.form.get('description', '').strip()
            })
            break

    if found:
        write_json(CALENDAR_FILE, calendar_events)
        flash('Examination calendar entry updated successfully!', 'success')
    else:
        flash('Calendar entry not found.', 'error')

    return redirect(url_for('admin_dashboard'))

@app.route('/admin/calendar/delete/<event_id>', methods=['POST'])
@login_required
@csrf_protect
def delete_calendar_event(event_id):
    calendar_events = [ev for ev in read_json(CALENDAR_FILE) if ev.get('id') != event_id]
    write_json(CALENDAR_FILE, calendar_events)
    flash('Examination calendar entry deleted successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

# --- QUICK ACCESS LINKS & CONFIG ROUTES ---
@app.route('/admin/links/update', methods=['POST'])
@login_required
@csrf_protect
def update_config_links():
    site_config = read_json(CONFIG_FILE)
    for i, link in enumerate(site_config.get('quick_links', [])):
        link['title'] = request.form.get(f"title_{i}", link['title'])
        file_key = f'file_{i}'
        if file_key in request.files:
            file = request.files[file_key]
            if file and file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                unique_filename = f"{int(datetime.now().timestamp())}_{filename}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_filename))
                link['url'] = url_for('static', filename=f'uploads/{unique_filename}', _external=True)
                continue
        link['url'] = request.form.get(f"url_{i}") or link['url']

    write_json(CONFIG_FILE, site_config)
    cleanup_unused_files()
    flash('Quick access links updated successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)