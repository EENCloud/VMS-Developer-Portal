from flask_wtf import FlaskForm
from wtforms.fields import (
    SelectMultipleField, SubmitField,
    DateTimeLocalField, HiddenField)


class TimeSelectForm(FlaskForm):
    type = SelectMultipleField(
        'Event Types', choices=[])
    start = DateTimeLocalField(
        'Start Time', format='%Y-%m-%dT%H:%M')
    end = DateTimeLocalField(
        'End Time', format='%Y-%m-%dT%H:%M')
    timezone = HiddenField()
    submit = SubmitField('Filter')
