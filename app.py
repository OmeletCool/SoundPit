import os
import random
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename
from backend.database import db_session
from backend.database.models.users_model import UserModel
from backend.database.default_data import default_data
from backend.forms.user_forms import LoginForm, RegisterForm

app = Flask(__name__)
app.secret_key = 'super_secret_neon_key_2026'

# Папка для документов
UPLOAD_FOLDER = 'band_verifications'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Секретный ключ для разработчиков
ADMIN_SECRET_KEY = 'neon_dev_2026_master_key'

TRANSLATIONS = {
    'ru': {
        'devs': 'РАЗРАБОТЧИКИ',
        'send': 'НАЙТИ',
        'login': 'ВХОД',
        'reg': 'РЕГИСТРАЦИЯ',
        'back': 'НАЗАД',
        'search_place': 'ПОИСК ТРЕКОВ...',
        'pending': 'НА ПРОВЕРКЕ',
        'admin_panel': 'ПАНЕЛЬ АДМИНА'
    },
    'en': {
        'devs': 'DEVS',
        'send': 'SEARCH',
        'login': 'LOGIN',
        'reg': 'SIGN UP',
        'back': 'BACK',
        'search_place': 'SEARCH TRACKS...',
        'pending': 'PENDING',
        'admin_panel': 'ADMIN PANEL'
    },
    'sq': {
        'devs': 'ZHVILLUESIT',
        'send': 'KËRKO',
        'login': 'HYRJE',
        'reg': 'REGJISTROHU',
        'back': 'PRAPA',
        'search_place': 'KËRKO...',
        'pending': 'NË PRITJE',
        'admin_panel': 'PANELI I ADMINISTRATORIT'
    }
}


@app.context_processor
def inject_vars():
    lang = session.get('lang', 'ru')
    return dict(txt=TRANSLATIONS.get(lang, TRANSLATIONS['ru']))


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/set_lang/<lang>')
def set_lang(lang):
    if lang in TRANSLATIONS:
        session['lang'] = lang
    return redirect(request.referrer or url_for('index'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    login_form = LoginForm()
    reg_form = RegisterForm()
    error = None

    # Вход
    if 'submit_login' in request.form and login_form.validate_on_submit():
        db_sess = db_session.create_session()
        user = db_sess.query(UserModel).filter(
            UserModel.username == login_form.username.data
        ).first()

        if user and user.check_password(login_form.password.data):
            # Проверка статуса для групп
            if user.role == 'band' and user.status == 'pending':
                error = "Ваш аккаунт группы на проверке. Ожидайте подтверждения администратора."
                return render_template('login.html', login_form=login_form, reg_form=reg_form,
                                       error=error, active_tab='login')

            session['user'] = user.username
            session['user_id'] = user.id
            session['display_name'] = user.name
            session['role'] = user.role
            return redirect(url_for('index'))
        else:
            error = "Неверный логин или пароль"

    # Регистрация
    elif 'submit_register' in request.form and reg_form.validate_on_submit():
        db_sess = db_session.create_session()

        # Проверка занятости email
        if db_sess.query(UserModel).filter(UserModel.email == reg_form.email.data).first():
            error = "Почта уже зарегистрирована"
            return render_template('login.html', login_form=login_form, reg_form=reg_form,
                                   error=error, active_tab='register')

        # Проверка занятости username
        if db_sess.query(UserModel).filter(UserModel.username == reg_form.username.data).first():
            error = "Логин уже занят"
            return render_template('login.html', login_form=login_form, reg_form=reg_form,
                                   error=error, active_tab='register')

        role = request.form.get('role', 'user')

        # Проверка секретного ключа для разработчиков
        if role == 'admin':
            admin_key = request.form.get('admin_key', '')
            if admin_key != ADMIN_SECRET_KEY:
                error = "Неверный ключ разработчика"
                return render_template('login.html', login_form=login_form, reg_form=reg_form,
                                       error=error, active_tab='register')

        # Обработка загрузки документов для групп
        docs_path = None
        if role == 'band' and reg_form.documents.data:
            filename = secure_filename(reg_form.documents.data.filename)
            user_folder = os.path.join(
                app.config['UPLOAD_FOLDER'], reg_form.username.data)
            os.makedirs(user_folder, exist_ok=True)
            file_path = os.path.join(user_folder, filename)
            reg_form.documents.data.save(file_path)
            docs_path = file_path

        # Определение статуса
        status = 'pending' if role == 'band' else 'active'

        # Создание пользователя
        user = UserModel(
            username=reg_form.username.data,
            name=reg_form.name.data,
            email=reg_form.email.data,
            about=reg_form.about.data,
            role=role,
            inn=request.form.get('inn') if role == 'band' else None,
            rkn_number=request.form.get(
                'rkn_number') if role == 'band' else None,
            docs_path=docs_path,
            status=status,
            funds=random.randint(1000, 5000) if role == 'band' else 0
        )
        user.set_password(reg_form.password.data)
        db_sess.add(user)
        db_sess.commit()

        # Автологин после регистрации
        session['user'] = user.username
        session['user_id'] = user.id
        session['display_name'] = user.name
        session['role'] = user.role

        if role == 'band':
            flash(
                "Ваша заявка отправлена на проверку. Ожидайте подтверждения администратора.", "info")

        return redirect(url_for('index'))

    return render_template('login.html', login_form=login_form, reg_form=reg_form,
                           error=error, active_tab='login')


@app.route('/developers')
def developers():
    # Доступ только для админов
    if 'user' not in session or session.get('role') != 'admin':
        flash("Доступ только для разработчиков", "warning")
        return redirect(url_for('index'))

    db_sess = db_session.create_session()
    # Получаем все группы на проверке
    pending_bands = db_sess.query(UserModel).filter(
        UserModel.role == 'band',
        UserModel.status == 'pending'
    ).all()

    # Получаем все активные группы
    approved_bands = db_sess.query(UserModel).filter(
        UserModel.role == 'band',
        UserModel.status == 'active'
    ).all()

    return render_template('developers.html',
                           pending_bands=pending_bands,
                           approved_bands=approved_bands)


@app.route('/approve_band/<int:band_id>')
def approve_band(band_id):
    # Только админы могут подтверждать
    if 'user' not in session or session.get('role') != 'admin':
        return redirect(url_for('index'))

    db_sess = db_session.create_session()
    band = db_sess.query(UserModel).filter(UserModel.id == band_id).first()
    if band and band.role == 'band':
        band.status = 'active'
        db_sess.commit()
        flash(f"Группа '{band.name}' подтверждена!", "success")

    return redirect(url_for('developers'))


@app.route('/reject_band/<int:band_id>')
def reject_band(band_id):
    # Только админы могут отклонять
    if 'user' not in session or session.get('role') != 'admin':
        return redirect(url_for('index'))

    db_sess = db_session.create_session()
    band = db_sess.query(UserModel).filter(UserModel.id == band_id).first()
    if band and band.role == 'band':
        db_sess.delete(band)
        db_sess.commit()
        flash(f"Заявка группы '{band.name}' отклонена", "warning")

    return redirect(url_for('developers'))


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


if __name__ == '__main__':
    db_session.global_init("db/music_crm.sqlite")
    default_data()
    app.run(debug=True)
