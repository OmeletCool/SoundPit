from flask import Flask, render_template, request, redirect, url_for, session, flash
from backend.database.csv_manager import init_db, register_user, verify_user, update_display_name

app = Flask(__name__)
app.secret_key = 'super_secret_music_key'


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        action = request.form.get('action')
        username = request.form.get('username').strip()
        password = request.form.get('password').strip()

        if action == 'register':
            if register_user(username, password):
                session['user'] = username
                session['display_name'] = username
                return redirect(url_for('index'))
            else:
                flash("Этот логин уже занят! Выберите другой.", "danger")

        if action == 'login':
            user = verify_user(username, password)
            if user:
                session['user'] = user['username']
                session['display_name'] = user['display_name']
                return redirect(url_for('index'))
            else:
                flash("Неверный логин или пароль.", "danger")

    return render_template('login.html')


@app.route('/change_name', methods=['POST'])
def change_name():
    if 'user' in session:
        new_name = request.form.get('new_name')
        if new_name:
            update_display_name(session['user'], new_name)
            session['display_name'] = new_name
    return redirect(request.referrer)


@app.route('/')
def index():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('index.html')


@app.route('/remix', methods=['GET', 'POST'])
def remix():
    if 'user' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        return "Скебоб"  # логика сохранения

    return render_template('remix.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/developers')
def developers():
    return render_template('developers.html')


if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
