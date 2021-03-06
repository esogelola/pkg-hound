import os

from flask import Flask
from . import (db, auth,package)


def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__ ,instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY='dev',
        DATABASE=os.path.join(app.instance_path, 'pkghound.sqlite'),
        UPLOAD_FOLDER = os.path.join('pkghound', 'static', 'packages'),
        PACKAGES_FOLDER = os.path.join('static','packages'),
        ALLOWED_EXTENSIONS = { 'png', 'jpg', 'jpeg', 'gif'},

    )

    
    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    #initialize database
    db.init_app(app)
    #Regiser authentication and package blue prints (urls) to this app
    app.register_blueprint(auth.bp)
    app.register_blueprint(package.bp)
    
    app.add_url_rule('/', endpoint='index')
    return app
