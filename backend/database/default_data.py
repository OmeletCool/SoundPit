from backend.database import db_session
from backend.database.models.users_model import UserModel
import secrets

def default_data():
    db_sess = db_session.create_session()
    user = db_sess.query(UserModel).filter(UserModel.username == "admin").first()
    if not user:
        user = UserModel()
        user.username = "admin"
        user.email = "admin@neon.crm"
        # Генерируем сложный пароль при первом запуске
        admin_password = secrets.token_urlsafe(16)
        print(f"\n🔐 ПАРОЛЬ АДМИНА: {admin_password}\n")
        user.set_password(admin_password)
        user.name = "OVERLORD"
        user.role = "admin"
        user.about = "Создатель системы"
        db_sess.add(user)
        db_sess.commit()