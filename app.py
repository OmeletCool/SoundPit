import os
import json
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
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

# Загрузка переводов из JSON
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
    return render_template('index.html')

@app.route('/set_lang/<lang>')
def set_lang(lang):
    if lang in TRANSLATIONS:
        session['lang'] = lang
    return redirect(request.referrer or url_for('index'))

# API для подсказок групп (только для авторизованных)
@app.route('/api/suggest')
def api_suggest():
    if 'user_id' not in session:
        return jsonify({'suggestions': []})
    
    query = request.args.get('q', '')
    db_sess = db_session.create_session()
    
    bands = db_sess.query(UserModel).filter(
        UserModel.role == 'band',
        UserModel.status == 'active',
        UserModel.name.contains(query)
    ).limit(5).all()
    
    suggestions = [{'id': b.id, 'name': b.name} for b in bands]
    return jsonify({'suggestions': suggestions})

@app.route('/login', methods=['GET', 'POST'])
def login():
    login_form = LoginForm()
    reg_form = RegisterForm()
    error = None
    active_tab = 'login'
    
    # Если пытались что-то сделать без аккаунта
    if request.args.get('register_first'):
        error = TRANSLATIONS.get(session.get('lang', 'ru'), {}).get('register_first', 'Сначала зарегистрируйтесь или войдите в аккаунт')
        active_tab = 'register'
    
    # Вход
    if request.method == 'POST' and 'submit_login' in request.form:
        if login_form.validate_on_submit():
            db_sess = db_session.create_session()
            user = db_sess.query(UserModel).filter(
                UserModel.username == login_form.username.data
            ).first()
            
            if user and user.check_password(login_form.password.data):
                if user.role == 'band' and user.status == 'pending':
                    error = "Ваш аккаунт группы на проверке. Ожидайте подтверждения."
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
                error = "Неверный логин или пароль"
                active_tab = 'login'
        else:
            error = "Ошибка валидации формы"
            active_tab = 'login'
    
    # Регистрация
    elif request.method == 'POST' and 'submit_register' in request.form:
        if reg_form.validate_on_submit():
            db_sess = db_session.create_session()
            
            # Проверка занятости email
            if db_sess.query(UserModel).filter(UserModel.email == reg_form.email.data).first():
                error = "Почта уже зарегистрирована"
                active_tab = 'register'
                db_sess.close()
                return render_template('login.html', login_form=login_form, reg_form=reg_form, 
                                     error=error, active_tab=active_tab)
            
            # Проверка занятости username
            if db_sess.query(UserModel).filter(UserModel.username == reg_form.username.data).first():
                error = "Логин уже занят"
                active_tab = 'register'
                db_sess.close()
                return render_template('login.html', login_form=login_form, reg_form=reg_form, 
                                     error=error, active_tab=active_tab)
            
            role = request.form.get('role', 'user')
            
            # 🔥 Загрузка документов для групп
            docs_path = None
            if role == 'band' and reg_form.documents.data:
                filename = secure_filename(reg_form.documents.data.filename)
                user_folder = os.path.join(app.config['UPLOAD_FOLDER'], reg_form.username.data)
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
                rkn_number=request.form.get('rkn_number') if role == 'band' else None,
                docs_path=docs_path,
                status=status,
                funds=0
            )
            user.set_password(reg_form.password.data)
            db_sess.add(user)
            db_sess.commit()
            
            # 🔥 Сохраняем сессию ПОСЛЕ коммита
            session['user'] = user.username
            session['user_id'] = user.id
            session['display_name'] = user.name
            session['role'] = user.role
            session['status'] = user.status
            
            db_sess.close()
            
            if role == 'band':
                flash("Ваша заявка отправлена на проверку.", "info")
            
            return redirect(url_for('index'))
        else:
            error = "Ошибка валидации формы"
            active_tab = 'register'
    
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
    # Если нет аккаунта — редирект на регистрацию с сообщением
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

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    db_session.global_init("db/music_crm.sqlite")
    default_data()
    app.run(debug=True)