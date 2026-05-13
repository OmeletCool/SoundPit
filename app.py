import os
import json
import re
import datetime
import random
import string
import sqlalchemy
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.utils import secure_filename
from backend.database import db_session
from backend.database.models.users_model import UserModel
from backend.database.models.band_page_model import BandPageModel
from backend.database.models.user_rating_model import UserRating
from backend.database.default_data import default_data
from backend.forms.user_forms import LoginForm, RegisterForm

app = Flask(__name__)
app.secret_key = 'super_secret_neon_key_2026'
BOT_API_SECRET = 'neon_bot_secret_token_2026'

UPLOAD_FOLDER = 'band_verifications'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs('static/images/band_covers', exist_ok=True)
os.makedirs('static/music/tracks', exist_ok=True)

ALLOWED_AUDIO_EXTENSIONS = {'mp3', 'wav', 'ogg', 'flac', 'm4a'}

def allowed_file_audio(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_AUDIO_EXTENSIONS

def load_translations():
    with open('static/languages.json', 'r', encoding='utf-8') as f:
        return json.load(f)

TRANSLATIONS = load_translations()

@app.context_processor
def inject_vars():
    lang = session.get('lang', 'ru')
    return dict(txt=TRANSLATIONS.get(lang, TRANSLATIONS['ru']), current_lang=lang)

def get_txt(key, default=''):
    lang = session.get('lang', 'ru')
    return TRANSLATIONS.get(lang, TRANSLATIONS.get('ru', {})).get(key, default)

def verify_bot_token(token):
    return token == BOT_API_SECRET

@app.route('/')
def index():
    band_page = None
    show_pending = False
    top_data = []
    hot_data = []

    db_sess = db_session.create_session()

    top_rated = db_sess.query(BandPageModel).join(
        UserModel, BandPageModel.band_id == UserModel.id
    ).filter(
        UserModel.role == 'band',
        UserModel.status == 'active',
        BandPageModel.is_published == True,
        BandPageModel.votes > 0
    ).order_by(BandPageModel.rating.desc()).limit(5).all()

    hot_bands = db_sess.query(BandPageModel).join(
        UserModel, BandPageModel.band_id == UserModel.id
    ).filter(
        UserModel.role == 'band',
        UserModel.status == 'active',
        BandPageModel.is_published == True
    ).order_by(BandPageModel.created_date.desc()).limit(5).all()

    top_data = [
        {
            'page_id': b.id,
            'title': b.title or b.band.name,
            'cover_image': b.cover_image,
            'rating': round(b.rating, 1),
            'votes': b.votes
        } for b in top_rated
    ]

    hot_data = [
        {
            'page_id': b.id,
            'title': b.title or b.band.name,
            'cover_image': b.cover_image
        } for b in hot_bands
    ]

    # Личная страница группы
    if 'user_id' in session and session.get('role') == 'band':
        user = db_sess.query(UserModel).filter(
            UserModel.id == session['user_id']
        ).first()
        if user:
            if user.status == 'pending':
                show_pending = True
            else:
                band_page = db_sess.query(BandPageModel).filter(
                    BandPageModel.band_id == user.id
                ).first()

    db_sess.close()

    return render_template('index.html',
                           band_page=band_page,
                           show_pending=show_pending,
                           top_bands=top_data,
                           hot_bands=hot_data)

@app.route('/set_lang/<lang>')
def set_lang(lang):
    if lang in TRANSLATIONS:
        session['lang'] = lang
    return redirect(request.referrer or url_for('index'))

@app.route('/api/search_bands')
def api_search_bands():
    query = request.args.get('q', '').strip()
    db_sess = db_session.create_session()

    if not query:
        db_sess.close()
        return json.dumps([], ensure_ascii=False)

    try:
        pages = db_sess.query(BandPageModel).join(
            UserModel, BandPageModel.band_id == UserModel.id
        ).filter(
            UserModel.role == 'band',
            UserModel.status == 'active',
            BandPageModel.is_published == True,
            sqlalchemy.or_(
                sqlalchemy.func.lower(BandPageModel.title).contains(query.lower()),
                sqlalchemy.func.lower(UserModel.name).contains(query.lower())
            )
        ).limit(10).all()

        result = [
            {
                'page_id': page.id,
                'title': page.title or page.band.name,
                'username': page.band.username
            }
            for page in pages
        ]
    except Exception as e:
        print(f"Search error: {e}")
        result = []

    db_sess.close()
    return json.dumps(result, ensure_ascii=False)

@app.route('/api/rate_band/<int:page_id>', methods=['POST'])
def rate_band(page_id):
    if 'user_id' not in session:
        return jsonify({'error': get_txt('login_to_search', 'Нужно войти')}), 401

    data = request.get_json()
    score = data.get('score')

    if not score or score < 1 or score > 5:
        return jsonify({'error': 'Некорректная оценка'}), 400

    db_sess = db_session.create_session()
    band_page = db_sess.query(BandPageModel).filter(BandPageModel.id == page_id).first()

    if not band_page:
        db_sess.close()
        return jsonify({'error': 'Страница не найдена'}), 404

    existing_rating = db_sess.query(UserRating).filter(
        UserRating.user_id == session['user_id'],
        UserRating.band_page_id == page_id
    ).first()

    if existing_rating:
        existing_rating.score = score
    else:
        new_vote = UserRating(
            user_id=session['user_id'],
            band_page_id=page_id,
            score=score
        )
        db_sess.add(new_vote)

    all_scores = db_sess.query(UserRating.score).filter(
        UserRating.band_page_id == page_id
    ).all()
    scores_list = [s[0] for s in all_scores]

    if scores_list:
        band_page.rating = sum(scores_list) / len(scores_list)
        band_page.votes = len(scores_list)
    else:
        band_page.rating = 0
        band_page.votes = 0

    db_sess.commit()
    result = {'new_rating': round(band_page.rating, 1), 'votes': band_page.votes}
    db_sess.close()

    return jsonify(result)

@app.route('/api/bot/create_moderator', methods=['POST'])
def api_create_moderator():
    token = request.headers.get('X-Bot-Secret')
    if not verify_bot_token(token):
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.json
    if not data:
        return jsonify({'error': 'No data'}), 400

    db_sess = db_session.create_session()

    existing = db_sess.query(UserModel).filter(
        sqlalchemy.or_(
            UserModel.email == data.get('email'),
            UserModel.username == data.get('login')
        )
    ).first()

    if existing:
        db_sess.close()
        return jsonify({'error': 'User already exists'}), 409

    password = data.get('password')
    if not password:
        password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))

    user = UserModel(
        username=data.get('login'),
        name=data.get('name'),
        email=data.get('email'),
        about=data.get('reason', ''),
        role='admin',
        status='active',
        funds=0
    )
    user.set_password(password)
    db_sess.add(user)
    db_sess.commit()

    user_id = user.id
    db_sess.close()

    return jsonify({
        'success': True,
        'user_id': user_id,
        'temp_password': password
    })

@app.route('/login', methods=['GET', 'POST'])
def login():
    login_form = LoginForm()
    reg_form = RegisterForm()
    error = None
    active_tab = 'login'

    if request.method == 'POST' and 'submit_login' in request.form:
        if login_form.validate_on_submit():
            db_sess = db_session.create_session()
            user = db_sess.query(UserModel).filter(
                sqlalchemy.or_(
                    UserModel.username == login_form.username.data,
                    UserModel.email == login_form.username.data
                )
            ).first()

            if user and user.check_password(login_form.password.data):
                if user.role == 'band' and user.status == 'pending':
                    error = get_txt('pending_hint', 'Ваш аккаунт группы на проверке.')
                    db_sess.close()
                    return render_template('login.html', login_form=login_form, reg_form=reg_form,
                                           error=error, active_tab='login')

                session['user'] = user.username
                session['user_id'] = user.id
                session['display_name'] = user.name
                session['role'] = user.role
                session['status'] = user.status
                db_sess.close()
                return redirect(url_for('index'))
            else:
                error = get_txt('invalid_credentials', 'Неверный логин или пароль')
                active_tab = 'login'
            db_sess.close()

    elif request.method == 'POST' and 'submit_register' in request.form:
        active_tab = 'register'
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        password_again = request.form.get('password_again', '')

        if not username or len(username) < 3:
            error = get_txt('username_length', 'Логин должен быть от 3 символов')
            return render_template('login.html', login_form=login_form, reg_form=reg_form,
                                   error=error, active_tab=active_tab)

        if not email or '@' not in email:
            error = get_txt('invalid_email', 'Некорректный email')
            return render_template('login.html', login_form=login_form, reg_form=reg_form,
                                   error=error, active_tab=active_tab)

        if len(password) < 6:
            error = get_txt('password_length', 'Пароль слишком короткий')
            return render_template('login.html', login_form=login_form, reg_form=reg_form,
                                   error=error, active_tab=active_tab)

        if password != password_again:
            error = get_txt('passwords_mismatch', 'Пароли не совпадают')
            return render_template('login.html', login_form=login_form, reg_form=reg_form,
                                   error=error, active_tab=active_tab)

        db_sess = db_session.create_session()

        if db_sess.query(UserModel).filter(UserModel.username == username).first():
            error = get_txt('username_taken', 'Этот логин уже занят')
            db_sess.close()
            return render_template('login.html', login_form=login_form, reg_form=reg_form,
                                   error=error, active_tab=active_tab)

        if db_sess.query(UserModel).filter(UserModel.email == email).first():
            error = get_txt('email_taken', 'Эта почта уже зарегистрирована')
            db_sess.close()
            return render_template('login.html', login_form=login_form, reg_form=reg_form,
                                   error=error, active_tab=active_tab)

        role = request.form.get('role', 'user')
        status = 'pending' if role == 'band' else 'active'

        docs_path = None
        if role == 'band' and request.files.get('documents'):
            file = request.files.get('documents')
            if file and file.filename:
                filename = secure_filename(file.filename)
                user_folder = os.path.join(app.config['UPLOAD_FOLDER'], username)
                os.makedirs(user_folder, exist_ok=True)
                file_path = os.path.join(user_folder, filename)
                file.save(file_path)
                docs_path = file_path

        user = UserModel(
            username=username,
            name=request.form.get('name', ''),
            email=email,
            about=request.form.get('about', ''),
            role=role,
            inn=request.form.get('inn') if role == 'band' else None,
            rkn_number=request.form.get('rkn_number') if role == 'band' else None,
            rep_name=request.form.get('rep_name') if role == 'band' else None,
            rep_email=request.form.get('rep_email') if role == 'band' else None,
            docs_path=docs_path,
            status=status,
            funds=0
        )
        user.set_password(password)
        db_sess.add(user)
        db_sess.commit()

        session['user'] = user.username
        session['user_id'] = user.id
        session['display_name'] = user.name
        session['role'] = user.role
        session['status'] = user.status

        db_sess.close()
        return redirect(url_for('index'))

    return render_template('login.html', login_form=login_form, reg_form=reg_form,
                           error=error, active_tab=active_tab)

@app.route('/account')
def account():
    if 'user_id' not in session:
        return redirect(url_for('login', register_first=1))

    db_sess = db_session.create_session()
    user = db_sess.query(UserModel).filter(UserModel.id == session['user_id']).first()

    if not user:
        session.clear()
        db_sess.close()
        return redirect(url_for('login'))

    db_sess.close()
    return render_template('account.html', user=user)

@app.route('/developers')
def developers():
    if 'user' not in session or session.get('role') != 'admin':
        flash("Доступ только для разработчиков", "warning")
        return redirect(url_for('index'))

    db_sess = db_session.create_session()
    pending_bands = db_sess.query(UserModel).filter(
        UserModel.role == 'band',
        UserModel.status == 'pending'
    ).all()
    approved_bands = db_sess.query(UserModel).filter(
        UserModel.role == 'band',
        UserModel.status == 'active'
    ).all()
    db_sess.close()

    return render_template('developers.html',
                           pending_bands=pending_bands,
                           approved_bands=approved_bands)

@app.route('/approve_band/<int:band_id>')
def approve_band(band_id):
    if 'user' not in session or session.get('role') != 'admin':
        return redirect(url_for('index'))

    db_sess = db_session.create_session()
    band = db_sess.query(UserModel).filter(UserModel.id == band_id).first()

    if band and band.role == 'band':
        band.status = 'active'
        db_sess.commit()
        flash(f"Группа '{band.name}' подтверждена!", "success")

    db_sess.close()
    return redirect(url_for('developers'))

@app.route('/reject_band/<int:band_id>')
def reject_band(band_id):
    if 'user' not in session or session.get('role') != 'admin':
        return redirect(url_for('index'))

    db_sess = db_session.create_session()
    band = db_sess.query(UserModel).filter(UserModel.id == band_id).first()

    if band and band.role == 'band':
        db_sess.delete(band)
        db_sess.commit()
        flash(f"Заявка группы '{band.name}' отклонена", "warning")

    db_sess.close()
    return redirect(url_for('developers'))

@app.route('/search')
def search():
    if 'user_id' not in session:
        return redirect(url_for('login', register_first=1))

    query = request.args.get('q', '')
    db_sess = db_session.create_session()
    pages = []

    if query:
        pages = db_sess.query(BandPageModel).join(
            UserModel, BandPageModel.band_id == UserModel.id
        ).filter(
            UserModel.role == 'band',
            UserModel.status == 'active',
            sqlalchemy.or_(
                BandPageModel.title.contains(query),
                UserModel.name.contains(query)
            )
        ).all()
    else:
        pages = db_sess.query(BandPageModel).join(
            UserModel, BandPageModel.band_id == UserModel.id
        ).filter(
            UserModel.role == 'band',
            UserModel.status == 'active'
        ).all()

    db_sess.close()
    return render_template('search.html', bands=pages, query=query)

@app.route('/band_page/create', methods=['GET', 'POST'])
def create_band_page():
    if 'user_id' not in session or session.get('role') != 'band':
        flash(get_txt('login_to_search', 'Войдите как группа'), 'warning')
        return redirect(url_for('index'))

    if session.get('status') == 'pending':
        flash(get_txt('pending_message', 'Аккаунт на проверке'), 'warning')
        return redirect(url_for('index'))

    db_sess = db_session.create_session()
    user = db_sess.query(UserModel).filter(UserModel.id == session['user_id']).first()

    if not user:
        db_sess.close()
        return redirect(url_for('login'))

    existing_page = db_sess.query(BandPageModel).filter(BandPageModel.band_id == user.id).first()
    if existing_page:
        db_sess.close()
        return redirect(url_for('edit_band_page', page_id=existing_page.id))

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        content = request.form.get('content', '').strip()
        cover_image = None

        if 'cover_image' in request.files:
            file = request.files['cover_image']
            if file and file.filename:
                filename = secure_filename(file.filename)
                cover_folder = os.path.join('static', 'images', 'band_covers')
                os.makedirs(cover_folder, exist_ok=True)
                timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                new_filename = f"{user.id}_{timestamp}_{filename}"
                file_path = os.path.join(cover_folder, new_filename)
                file.save(file_path)
                cover_image = f"/static/images/band_covers/{new_filename}"

        tracks = []
        for i in range(1, 4):
            track_file = request.files.get(f'track{i}')
            track_name = request.form.get(f'track{i}_name', '').strip()
            if track_file and track_file.filename and allowed_file_audio(track_file.filename):
                filename = secure_filename(track_file.filename)
                music_folder = os.path.join('static', 'music', 'tracks')
                os.makedirs(music_folder, exist_ok=True)
                timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                new_filename = f"{user.id}_track{i}_{timestamp}_{filename}"
                file_path = os.path.join(music_folder, new_filename)
                track_file.save(file_path)
                tracks.append((f"/static/music/tracks/{new_filename}", track_name or filename))
            else:
                tracks.append((None, None))

        if not title:
            flash('Название группы обязательно', 'danger')
            db_sess.close()
            return render_template('create_band_page.html')

        band_page = BandPageModel(
            band_id=user.id,
            title=title,
            description=description,
            content=content,
            cover_image=cover_image,
            is_published=True,
            views=0,
            rating=0.0,
            votes=0,
            track1_path=tracks[0][0], track1_name=tracks[0][1],
            track2_path=tracks[1][0], track2_name=tracks[1][1],
            track3_path=tracks[2][0], track3_name=tracks[2][1]
        )
        
        db_sess.add(band_page)
        db_sess.commit()
        page_id = band_page.id
        db_sess.close()
        
        flash('Страница группы успешно создана!', 'success')
        return redirect(url_for('view_band_page', page_id=page_id))

    db_sess.close()
    return render_template('create_band_page.html')

@app.route('/band_page/<int:page_id>/edit', methods=['GET', 'POST'])
def edit_band_page(page_id):
    if 'user_id' not in session or session.get('role') != 'band':
        flash(get_txt('login_to_search', 'Войдите как группу'), 'warning')
        return redirect(url_for('index'))

    db_sess = db_session.create_session()
    band_page = db_sess.query(BandPageModel).filter(BandPageModel.id == page_id).first()

    if not band_page or band_page.band_id != session['user_id']:
        db_sess.close()
        return redirect(url_for('index'))

    if request.method == 'POST':
        band_page.title = request.form.get('title', '').strip()
        band_page.description = request.form.get('description', '').strip()
        band_page.content = request.form.get('content', '').strip()
        band_page.updated_date = datetime.datetime.now()

        if request.files.get('cover_image'):
            file = request.files.get('cover_image')
            if file and file.filename:
                filename = secure_filename(file.filename)
                cover_folder = os.path.join('static', 'images', 'band_covers')
                os.makedirs(cover_folder, exist_ok=True)
                timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                new_filename = f"{session['user_id']}_{timestamp}_{filename}"
                file_path = os.path.join(cover_folder, new_filename)
                file.save(file_path)
                band_page.cover_image = f"/static/images/band_covers/{new_filename}"

        for i in range(1, 4):
            track_file = request.files.get(f'track{i}')
            track_name = request.form.get(f'track{i}_name', '').strip()
            
            if track_file and track_file.filename and allowed_file_audio(track_file.filename):
                filename = secure_filename(track_file.filename)
                music_folder = os.path.join('static', 'music', 'tracks')
                os.makedirs(music_folder, exist_ok=True)
                timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                new_filename = f"{session['user_id']}_track{i}_{timestamp}_{filename}"
                file_path = os.path.join(music_folder, new_filename)
                track_file.save(file_path)
                setattr(band_page, f'track{i}_path', f"/static/music/tracks/{new_filename}")
                setattr(band_page, f'track{i}_name', track_name or filename)
            elif track_name and not getattr(band_page, f'track{i}_path'):
                setattr(band_page, f'track{i}_name', track_name)

        db_sess.commit()
        db_sess.close()
        return redirect(url_for('view_band_page', page_id=page_id))

    db_sess.close()
    return render_template('edit_band_page.html', band_page=band_page)

@app.route('/band_page/<int:page_id>')
def view_band_page(page_id):
    db_sess = db_session.create_session()
    band_page = db_sess.query(BandPageModel).filter(BandPageModel.id == page_id).first()

    if not band_page:
        db_sess.close()
        return redirect(url_for('index'))
    
    band_page.views += 1
    db_sess.commit()
    
    band = db_sess.query(UserModel).filter(UserModel.id == band_page.band_id).first()
    db_sess.close()
    
    return render_template('view_band_page.html', band_page=band_page, band=band)

@app.route('/logout')
def logout():
    lang = session.get('lang', 'ru')
    session.clear()
    session['lang'] = lang
    return redirect(url_for('index'))

if __name__ == '__main__':
    try:
        db_session.global_init("db/music_crm.sqlite")
        default_data()
    except sqlalchemy.exc.OperationalError as e:
        print(f"⚠️ Ошибка базы данных: {e}")
        print("💡 Запустите python fix_db.py или удалите db/music_crm.sqlite")
    app.run(host='127.0.0.1', port=8000, debug=True)