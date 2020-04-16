import sqlite3

import click
from flask import current_app, g
from flask.cli import with_appcontext

def init_app(app):
    #When the app is closing, we close the database
    app.teardown_appcontext(close_db)
    #Add a comppand to our application
    app.cli.add_command(init_db_command)

def init_db():
    #store database object
    db = get_db()
    #Open our schema sql file and execute each line 
    with current_app.open_resource('schema.sql') as f:
        db.executescript(f.read().decode('utf8'))


@click.command('init-db')
@with_appcontext
def init_db_command():
    """Clear the existing data and create new tables."""
    init_db()
    click.echo('Initialized the database.')

    
def get_db():
    #Return the database object
    if 'db' not in g:
        g.db = sqlite3.connect(
            current_app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        sqlite3.register_adapter(bool, int)
        sqlite3.register_converter("BOOLEAN", lambda v: v != '0')
        g.db.row_factory = sqlite3.Row

    return g.db


def close_db(e=None):
    #Remove the database object from our 'g' object
    db = g.pop('db', None)
    #If it's still open, close it.
    if db is not None:
        db.close()