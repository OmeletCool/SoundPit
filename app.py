import os
import json
import re
import datetime
import sqlalchemy
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename
from backend.database import db_session
from backend.database.models.users_model import UserModel
from backend.database.models.band_page_model import BandPageModel
from backend.database.default_data import default_data
from backend.forms.user_forms import LoginForm, RegisterForm

app = Flask(__name__)
app.secret_key = 'super_secret_neon_key_2026'
UPLOAD_FOLDER = 'band_verifications'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs('static/images/band_covers', exist_ok=True)


def load_translations():
    with open('static/languages.json', 'r', encoding='utf-8') as f:
        return json.load(f)


TRANSLATIONS = load_translations()


@app.context_processor
def inject_vars():
    lang = session.get('lang', 'ru')
    return dict(txt=TRANSLATIONS.get(lang, TRANSLATIONS['ru']), current_lang=lang)


@app.route('/')
def index():
    band_page = None
    show_pending = False
    if 'user_id' in session and session.get('role') == 'band':
        db_sess = db_session.create_session()
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

    return render_template('index.html', band_page=band_page, show_pending=show_pending)


@app.route('/set_lang/<lang>')
def set_lang(lang):
    if lang in TRANSLATIONS:
        session['lang'] = lang
    return redirect(request.referrer or url_for('index'))


@app.route('/api/search_bands')
def api_search_bands():
    query = request.args.get('q', '').strip().lower()
    db_sess = db_session.create_session()

    if query:
        bands = db_sess.query(UserModel).filter(
            UserModel.role == 'band',
            UserModel.status == 'active',
            sqlalchemy.func.lower(UserModel.name).contains(query)
        ).limit(10).all()
    else:
        bands = []

    result = [
        {
            'id': band.id,
            'name': band.name,
            'username': band.username
        }
        for band in bands
    ]

    db_sess.close()
    return json.dumps(result, ensure_ascii=False)


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
                UserModel.username == login_form.username.data
            ).first()

            if user and user.check_password(login_form.password.data):
                if user.role == 'band' and user.status == 'pending':
                    error = TRANSLATIONS.get(session.get('lang', 'ru'), {}).get(
                        'pending_hint', 'Ваш аккаунт группы на проверке.')
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
                error = TRANSLATIONS.get(session.get('lang', 'ru'), {}).get(
                    'invalid_credentials', 'Неверный логин или пароль')
                active_tab = 'login'
            db_sess.close()

    elif request.method == 'POST' and 'submit_register' in request.form:
        active_tab = 'register'
        password = request.form.get('password', '')
        password_again = request.form.get('password_again', '')
        email = request.form.get('email', '')
        username = request.form.get('username', '')

        if len(password) < 8 or len(password) > 32:
            error = TRANSLATIONS.get(session.get('lang', 'ru'), {}).get(
                'password_length', 'Пароль должен быть от 8 до 32 символов')
            return render_template('login.html', login_form=login_form, reg_form=reg_form,
                                   error=error, active_tab=active_tab)

        if not re.search(r'[a-zA-Z]', password) or not re.search(r'[0-9]', password):
            error = TRANSLATIONS.get(session.get('lang', 'ru'), {}).get(
                'password_chars', 'Пароль должен содержать буквы и цифры')
            return render_template('login.html', login_form=login_form, reg_form=reg_form,
                                   error=error, active_tab=active_tab)

        if password != password_again:
            error = TRANSLATIONS.get(session.get('lang', 'ru'), {}).get(
                'passwords_mismatch', 'Пароли не совпадают')
            return render_template('login.html', login_form=login_form, reg_form=reg_form,
                                   error=error, active_tab=active_tab)

        email_regex = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
        if email and not re.match(email_regex, email):
            error = TRANSLATIONS.get(session.get('lang', 'ru'), {}).get(
                'invalid_email', 'Некорректный формат почты')
            return render_template('login.html', login_form=login_form, reg_form=reg_form,
                                   error=error, active_tab=active_tab)

        db_sess = db_session.create_session()

        if email and db_sess.query(UserModel).filter(UserModel.email == email).first():
            error = TRANSLATIONS.get(session.get('lang', 'ru'), {}).get(
                'email_taken', 'Почта уже зарегистрирована')
            db_sess.close()
            return render_template('login.html', login_form=login_form, reg_form=reg_form,
                                   error=error, active_tab=active_tab)

        if db_sess.query(UserModel).filter(UserModel.username == username).first():
            error = TRANSLATIONS.get(session.get('lang', 'ru'), {}).get(
                'username_taken', 'Логин уже занят')
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
                user_folder = os.path.join(
                    app.config['UPLOAD_FOLDER'], username)
                os.makedirs(user_folder, exist_ok=True)
                file_path = os.path.join(user_folder, filename)
                file.save(file_path)
                docs_path = file_path

        user = UserModel(
            username=username,
            name=request.form.get('name', ''),
            email=email if role == 'user' else None,
            about=request.form.get('about', ''),
            role=role,
            inn=request.form.get('inn') if role == 'band' else None,
            rkn_number=request.form.get(
                'rkn_number') if role == 'band' else None,
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
    user = db_sess.query(UserModel).filter(
        UserModel.id == session['user_id']).first()
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
    if query:
        bands = db_sess.query(UserModel).filter(
            UserModel.role == 'band',
            UserModel.status == 'active',
            UserModel.name.contains(query)
        ).all()
    else:
        bands = db_sess.query(UserModel).filter(
            UserModel.role == 'band',
            UserModel.status == 'active'
        ).all()
    db_sess.close()
    return render_template('search.html', bands=bands, query=query)


@app.route('/band_page/create', methods=['GET', 'POST'])
def create_band_page():
    if 'user_id' not in session or session.get('role') != 'band':
        return redirect(url_for('login'))

    if session.get('status') == 'pending':
        return redirect(url_for('index'))

    db_sess = db_session.create_session()
    user = db_sess.query(UserModel).filter(
        UserModel.id == session['user_id']).first()

    if not user:
        db_sess.close()
        return redirect(url_for('login'))

    existing_page = db_sess.query(BandPageModel).filter(
        BandPageModel.band_id == user.id).first()
    if existing_page:
        db_sess.close()
        return redirect(url_for('edit_band_page', page_id=existing_page.id))

    if request.method == 'POST':
        title = request.form.get('title', '')
        description = request.form.get('description', '')
        content = request.form.get('content', '')

        cover_image = None
        if request.files.get('cover_image'):
            file = request.files.get('cover_image')
            if file and file.filename:
                filename = secure_filename(file.filename)
                cover_folder = os.path.join('static', 'images', 'band_covers')
                os.makedirs(cover_folder, exist_ok=True)
                file_path = os.path.join(cover_folder, f"{user.id}_{filename}")
                file.save(file_path)
                cover_image = f"/static/images/band_covers/{user.id}_{filename}"

        band_page = BandPageModel(
            band_id=user.id,
            title=title,
            description=description,
            content=content,
            cover_image=cover_image,
            is_published=True
        )

        db_sess.add(band_page)
        db_sess.commit()
        db_sess.close()

        return redirect(url_for('view_band_page', page_id=band_page.id))

    db_sess.close()
    return render_template('create_band_page.html')


@app.route('/band_page/<int:page_id>/edit', methods=['GET', 'POST'])
def edit_band_page(page_id):
    if 'user_id' not in session or session.get('role') != 'band':
        return redirect(url_for('login'))

    db_sess = db_session.create_session()
    band_page = db_sess.query(BandPageModel).filter(
        BandPageModel.id == page_id).first()

    if not band_page or band_page.band_id != session['user_id']:
        db_sess.close()
        return redirect(url_for('index'))

    if request.method == 'POST':
        band_page.title = request.form.get('title', '')
        band_page.description = request.form.get('description', '')
        band_page.content = request.form.get('content', '')
        band_page.updated_date = datetime.datetime.now()

        if request.files.get('cover_image'):
            file = request.files.get('cover_image')
            if file and file.filename:
                filename = secure_filename(file.filename)
                cover_folder = os.path.join('static', 'images', 'band_covers')
                os.makedirs(cover_folder, exist_ok=True)
                file_path = os.path.join(
                    cover_folder, f"{session['user_id']}_{filename}")
                file.save(file_path)
                band_page.cover_image = f"/static/images/band_covers/{session['user_id']}_{filename}"

        db_sess.commit()
        db_sess.close()

        return redirect(url_for('view_band_page', page_id=page_id))

    db_sess.close()
    return render_template('edit_band_page.html', band_page=band_page)


@app.route('/band_page/<int:page_id>')
def view_band_page(page_id):
    db_sess = db_session.create_session()
    band_page = db_sess.query(BandPageModel).filter(
        BandPageModel.id == page_id).first()

    if not band_page:
        db_sess.close()
        return redirect(url_for('index'))

    band_page.views += 1
    db_sess.commit()

    band = db_sess.query(UserModel).filter(
        UserModel.id == band_page.band_id).first()

    db_sess.close()
    return render_template('view_band_page.html', band_page=band_page, band=band)


@app.route('/logout')
def logout():
    lang = session.get('lang', 'ru')
    session.clear()
    session['lang'] = lang
    return redirect(url_for('index'))


if __name__ == '__main__':
    db_session.global_init("db/music_crm.sqlite")
    default_data()
    app.run(host='127.0.0.1', port=8000, debug=True)
