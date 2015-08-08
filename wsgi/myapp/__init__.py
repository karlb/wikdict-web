import os

from flask import Flask, render_template, redirect, request, url_for, flash

ADMINS = ['karl42@gmail.com']

app = Flask(__name__.split('.')[0])
app.debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
if not app.debug:
    import logging

    from logging.handlers import RotatingFileHandler
    file_handler = RotatingFileHandler(
        os.environ['OPENSHIFT_LOG_DIR'] + '/flask.log',
        maxBytes=10000, backupCount=1)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)

    from logging.handlers import SMTPHandler
    credentials = (os.environ.get('SENDGRID_USER'),
                   os.environ.get('SENDGRID_PASSWORD'))
    mail_handler = SMTPHandler('smtp.sendgrid.net',
                               'server-error@trackmyowe.com',
                               ADMINS, 'TrackMyOwe.com Error',
                               credentials)
    mail_handler.setLevel(logging.ERROR)
    app.logger.addHandler(mail_handler)

app.secret_key = os.environ['OPENSHIFT_SECRET_TOKEN']


@app.route("/")
def index():
    return render_template('index.html')


if __name__ == "__main__":
    app.run()
