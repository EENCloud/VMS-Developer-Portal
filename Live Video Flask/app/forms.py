from flask_wtf import FlaskForm
from wtforms.fields import (
    SubmitField, StringField)
from wtforms.validators import DataRequired


class AccessTokenForm(FlaskForm):
    token = StringField('Access Token', validators=[DataRequired()])
    baseUrl = StringField('Base URL', validators=[DataRequired()])
    submit = SubmitField('Login')