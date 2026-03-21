import re
import io
from flask import Flask, render_template, request, redirect, url_for, session, send_file
from werkzeug.utils import secure_filename
from backend.database.csv_manager import init_db, register_user, verify_user, update_display_name

app = Flask(__name__)
app.secret_key = 'neon_music_crm_secret'

TRANSLATIONS = {
    'ru': {'devs': 'Разработчики', 'send': 'Отправить', 'login': 'Войти', 'reg': 'Регистрация', 'back': 'Назад', 'save': 'Сохранить', 'remix_title': 'Студия Ремиксов', 'search_place': 'Например: Alice in Chains', 'change_name': 'Сменить имя'},
    'en': {'devs': 'Developers', 'send': 'Submit', 'login': 'Login', 'reg': 'Register', 'back': 'Back', 'save': 'Save', 'remix_title': 'Remix Studio', 'search_place': 'For example: Alice in Chains', 'change_name': 'Change Name'},
    'sq': {'devs': 'Zhvilluesit', 'send': 'Dërgo', 'login': 'Hyrje', 'reg': 'Regjistrohu', 'back': 'Prapa', 'save': 'Ruaj', 'remix_title': 'Studio Remix', 'search_place': 'Shembull: Alice in Chains', 'change_name': 'Ndrysho emrin'}
}

@app.context_processor
def inject_vars():
    lang = session.get('lang', 'ru')
    return dict(txt=TRANSLATIONS.get(lang, TRANSLATIONS['ru']))

@app.route('/set_lang/<lang>')
def set_lang(lang):
    if lang in TRANSLATIONS: session['lang'] = lang
    return redirect(request.referrer or url_for('index'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        action = request.form.get('action')
        u, p = request.form.get('username', ''), request.form.get('password', '')
        if re.match(r'^[a-zA-Z0-9_]{1,20}$', u):
            if action == 'register':
                if register_user(u, p):
                    session['user'] = session['display_name'] = u
                    return redirect(url_for('index'))
            else:
                user = verify_user(u, p)
                if user:
                    session['user'], session['display_name'] = user['username'], user['display_name']
                    return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/change_name', methods=['POST'])
def change_name():
    new_name = request.form.get('new_name')
    if new_name and 'user' in session:
        update_display_name(session['user'], new_name)
        session['display_name'] = new_name
    return redirect(request.referrer)

@app.route('/')
def index():
    if 'user' not in session: return redirect(url_for('login'))
    return render_template('index.html')

@app.route('/remix', methods=['GET', 'POST'])
def remix():
    if 'user' not in session: return redirect(url_for('login'))
    if request.method == 'POST':
        file = request.files.get('audio_file')
        if file and file.filename != '':
            return send_file(io.BytesIO(file.read()), mimetype=file.mimetype, as_attachment=True, download_name=f"remix_{secure_filename(file.filename)}")
    return render_template('remix.html')

@app.route('/developers')
def developers(): return render_template('developers.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)