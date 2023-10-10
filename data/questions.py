import sqlalchemy
from sqlalchemy.sql import func
from sqlalchemy_serializer import SerializerMixin
from .db_session import SqlAlchemyBase


class Question(SqlAlchemyBase, SerializerMixin):
    __tablename__ = 'questions'
    id = sqlalchemy.Column(sqlalchemy.Integer, unique=True, autoincrement=True, primary_key=True)
    message_id = sqlalchemy.Column(sqlalchemy.Integer, unique=True, default=0)
    username = sqlalchemy.Column(sqlalchemy.String)
    user_id = sqlalchemy.Column(sqlalchemy.Integer)
    adm_username = sqlalchemy.Column(sqlalchemy.String, default="none")
    time_created = sqlalchemy.Column(sqlalchemy.DateTime(timezone=True), server_default=func.now())
    text = sqlalchemy.Column(sqlalchemy.String)