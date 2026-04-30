import sqlalchemy
from ..db_session import SqlAlchemyBase


class UserRating(SqlAlchemyBase):
    __tablename__ = 'user_ratings'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    user_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey("users.id"), nullable=False)
    band_page_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey("band_pages.id"), nullable=False)
    score = sqlalchemy.Column(sqlalchemy.Integer, nullable=False)

    # Уникальная связка: один пользователь — одна оценка на страницу
    __table_args__ = (
        sqlalchemy.UniqueConstraint('user_id', 'band_page_id', name='_user_band_uc'),
    )
    # Убрали back_populates, чтобы не ломало существующие модели