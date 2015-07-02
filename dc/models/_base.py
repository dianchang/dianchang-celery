import os
from flask.ext.sqlalchemy import SQLAlchemy
from flask import Flask

app = Flask(__name__)
mode = os.environ.get('MODE')
print(mode)
if mode == 'PRODUCTION':
    app.config.update(
        SQLALCHEMY_DATABASE_URI="mysql+pymysql://root:sBLkMvu1PlRuZEAEerqa@119.254.102.136:3306/dianchang",
    )
else:
    app.config.update(
        SQLALCHEMY_DATABASE_URI="mysql+pymysql://root:@localhost/dianchang",
    )
db = SQLAlchemy(app)
