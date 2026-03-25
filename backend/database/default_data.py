from backend.database import db_session
from backend.database.models.users_model import UserModel

def default_data():
    db_sess = db_session.create_session()
    user = db_sess.query(UserModel).filter(UserModel.username == "admin").first()
    if not user:
        user = UserModel()
        user.username = "admin"
        user.email = "admin@neon.crm"
        user.set_password("neon_god")
        user.name = "OVERLORD"
        user.role = "admin"
        user.about = "Создатель системы"
        db_sess.add(user)
        db_sess.commit()