from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired


class ExportForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    directory = StringField(
        'Directory',
        validators=[DataRequired()],
        default='/')
    notes = TextAreaField('Notes')
    tags = TextAreaField('Tags', description='Separate tags with commas.')
    submit = SubmitField('Export')
