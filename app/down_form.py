from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, BooleanField, DecimalField, IntegerField
from wtforms.validators import DataRequired, IPAddress, URL, NumberRange

class DWNForm(FlaskForm):
    save_video=BooleanField(label='Качаем видео?', default=False)
    yt_url = StringField('Youtube URL:', default='https://www.youtube.com/',
                       validators=[DataRequired(), URL()])
    # isTOR = BooleanField('TOR:', default=True)
    stop = SubmitField('Stop process', name='stop', render_kw={'disabled': True})
    submit = SubmitField('Convert & download', name='save', render_kw={'disabled': False})
    save_video = BooleanField(label='Pull video?', default=False)
    # start_from = DecimalField(label='Starts from (for list):', default=0, places=0,
    #                    validators=[DataRequired(), NumberRange(min=0, max=1000)])
    start_from = IntegerField(label='Starts from (for list):', default=0,
                              validators=[NumberRange(min=0, max=1000), ])
    stop_at = IntegerField(label='Stop at (for list):', default=1000,
                           validators=[NumberRange(min=0, max=1000), ])

if __name__ == '__main__':
    print('all done')
