import datetime
import sqlalchemy
from sqlalchemy import orm
from ..db_session import SqlAlchemyBase
from werkzeug.security import generate_password_hash, check_password_hash


class UserModel(SqlAlchemyBase):
    __tablename__ = 'users'

    id = sqlalchemy.Column(
        sqlalchemy.Integer, primary_key=True, autoincrement=True)
    username = sqlalchemy.Column(
        sqlalchemy.String, index=True, unique=True, nullable=True)
    # Имя юзера или Название группы
    name = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    about = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    email = sqlalchemy.Column(
        sqlalchemy.String, index=True, unique=True, nullable=True)
    # 'user', 'band', 'admin'
    role = sqlalchemy.Column(sqlalchemy.String, default='user')
    funds = sqlalchemy.Column(sqlalchemy.Integer, default=0)

    # Новые поля для музыкальных групп
    inn = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    rkn_number = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    docs_path = sqlalchemy.Column(
        sqlalchemy.String, nullable=True)  # Путь к папке с доками
    # 'active' для юзеров, 'pending'/'approved' для групп
    status = sqlalchemy.Column(sqlalchemy.String, default='active')

    hashed_password = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    created_date = sqlalchemy.Column(
        sqlalchemy.DateTime, default=datetime.datetime.now)

    news = orm.relationship("NewsModel", back_populates='user')

    def set_password(self, password):
        self.hashed_password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.hashed_password, password)
