from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, TextAreaField, SubmitField, EmailField, RadioField
from wtforms.validators import DataRequired, Email, EqualTo, Optional

class LoginForm(FlaskForm):
    username = StringField('Логин', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    submit = SubmitField('Войти')

class RegisterForm(FlaskForm):
    username = StringField('Логин', validators=[DataRequired()])
    email = EmailField('Email', validators=[DataRequired(), Email()])
    name = StringField('Имя / Название группы', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    password_again = PasswordField('Повторите пароль', validators=[
        DataRequired(), EqualTo('password', message='Пароли должны совпадать')
    ])
    about = TextAreaField('О себе / О группе')
    
    # Выбор роли
    role = RadioField('Тип аккаунта', choices=[
        ('user', '🎧 Слушатель'),
        ('band', '🎸 Музыкальная группа')
    ], default='user', validators=[DataRequired()])
    
    # Поля для музыкальных групп
    inn = StringField('ИНН', validators=[Optional()])
    rkn_number = StringField('Регистрационный номер РКН', validators=[Optional()])
    band_email = EmailField('Email представителя', validators=[Optional()])
    documents = FileField('Документы (PDF/ZIP/DOC)', validators=[
        Optional(),
        FileAllowed(['pdf', 'zip', 'doc', 'docx'], 'Только PDF, ZIP, DOC')
    ])
    
    submit = SubmitField('Зарегистрироваться')