from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, TextAreaField, SubmitField, EmailField
from wtforms.validators import DataRequired, Email, EqualTo, Optional


class LoginForm(FlaskForm):
    username = StringField('Логин', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    submit = SubmitField('Войти')


class RegisterForm(FlaskForm):
    # Убрали username и password отсюда
    email = EmailField('Email', validators=[DataRequired()]) # Сделали обязательным
    name = StringField('Имя / Название группы', validators=[DataRequired()])
    about = TextAreaField('О себе / О группе')
    inn = StringField('ИНН', validators=[Optional()])
    rkn_number = StringField(
        'Регистрационный номер РКН', validators=[Optional()])
    documents = FileField('Документы (PDF/ZIP/DOC)', validators=[
        Optional(),
        FileAllowed(['pdf', 'zip', 'doc', 'docx'], 'Только PDF, ZIP, DOC')
    ])
    submit = SubmitField('Зарегистрироваться')