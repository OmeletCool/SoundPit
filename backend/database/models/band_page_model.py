import datetime
import sqlalchemy
from sqlalchemy import orm
from ..db_session import SqlAlchemyBase


class BandPageModel(SqlAlchemyBase):
    __tablename__ = 'band_pages'

    id = sqlalchemy.Column(
        sqlalchemy.Integer, primary_key=True, autoincrement=True)

    band_id = sqlalchemy.Column(
        sqlalchemy.Integer, sqlalchemy.ForeignKey("users.id"), unique=True)
    band = orm.relationship('UserModel', back_populates='band_page')

    title = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    description = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    content = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    cover_image = sqlalchemy.Column(sqlalchemy.String, nullable=True)

    created_date = sqlalchemy.Column(
        sqlalchemy.DateTime, default=datetime.datetime.now)
    updated_date = sqlalchemy.Column(
        sqlalchemy.DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now)

    views = sqlalchemy.Column(sqlalchemy.Integer, default=0)
    is_published = sqlalchemy.Column(sqlalchemy.Boolean, default=False)
