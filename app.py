import os
import random
from flask import Flask, render_template, request, redirect, url_for, session, flash
from backend.database import db_session
from backend.database.models.users_model import UserModel
from backend.database.default_data import default_data
from backend.forms.user_forms import LoginForm, RegisterForm

app = Flask(__name__)
app.secret_key = 'neon_music_crm_secret'

TRANSLATIONS = {
    'ru': {'devs': 'Разработчики', 'send': 'Отправить', 'login': 'Войти', 'reg': 'Регистрация', 'back': 'Назад', 'search_place': 'НАПРИМЕР: БЛА БЛА БЛА'},
    'en': {'devs': 'Developers', 'send': 'Submit', 'login': 'Login', 'reg': 'Register', 'back': 'Back', 'search_place': 'EXAMPLE: BLA BLA BLA'},
    'sq': {'devs': 'Zhvilluesit', 'send': 'Dërgo', 'login': 'Hyrje', 'reg': 'Regjistrohu', 'back': 'Prapa', 'search_place': 'SHEMBULL: BLA BLA BLA'}
}
@app.context_processor
def inject_vars():
    lang = session.get('lang', 'ru')
    return dict(txt=TRANSLATIONS.get(lang, TRANSLATIONS['ru']))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/action_gateway', methods=['POST'])
def change_name():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return redirect(url_for('index'))

@app.route('/set_lang/<lang>')
def set_lang(lang):
    if lang in TRANSLATIONS:
        session['lang'] = lang
    # Возвращаемся туда, откуда пришли, или на главную
    return redirect(request.referrer or url_for('index'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    login_form = LoginForm()
    reg_form = RegisterForm()
    
    # Обработка ВХОДА
    if 'submit_login' in request.form and login_form.validate_on_submit():
        db_sess = db_session.create_session()
        user = db_sess.query(UserModel).filter(UserModel.username == login_form.username.data).first()
        if user and user.check_password(login_form.password.data):
            session['user_id'] = user.id
            session['display_name'] = user.name
            session['role'] = user.role
            return redirect(url_for('admin_panel' if user.role == 'admin' else 'index'))
        return render_template('login.html', login_form=login_form, reg_form=reg_form, error="Неверный логин или пароль", active_tab='login')

    # Обработка РЕГИСТРАЦИИ
    if 'submit_register' in request.form and reg_form.validate_on_submit():
        if reg_form.password.data != reg_form.password_again.data:
            return render_template('login.html', login_form=login_form, reg_form=reg_form, error="Пароли не совпадают", active_tab='register')
        
        db_sess = db_session.create_session()
        if db_sess.query(UserModel).filter(UserModel.email == reg_form.email.data).first():
            return render_template('login.html', login_form=login_form, reg_form=reg_form, error="Такая почта уже есть", active_tab='register')
            
        role = request.form.get('role', 'user')
        user = UserModel(
            username=reg_form.username.data,
            name=reg_form.name.data,
            email=reg_form.email.data,
            about=reg_form.about.data,
            role=role,
            funds=random.randint(1000, 20000) if role == 'band' else 0
        )
        user.set_password(reg_form.password.data)
        db_sess.add(user)
        db_sess.commit()
        
        session['user_id'] = user.id
        session['display_name'] = user.name
        session['role'] = user.role
        return redirect(url_for('index'))

    return render_template('login.html', login_form=login_form, reg_form=reg_form, active_tab='login')

@app.route('/admin')
def developers():
    if session.get('role') != 'admin':
        return redirect(url_for('index'))
    db_sess = db_session.create_session()
    bands = db_sess.query(UserModel).filter(UserModel.role == 'band').all()
    return render_template('admin.html', bands=bands)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    # Инициализация БД
    os.makedirs('db', exist_ok=True)
    db_session.global_init("db/music_crm.sqlite")
    default_data() # Создаем админа
    app.run(debug=True)