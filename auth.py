import functools

from flask import (Blueprint, flash, g, redirect, render_template, request, session, url_for)

from werkzeug.security import check_password_hash, generate_password_hash

from pkghound.db import get_db

bp = Blueprint('auth', __name__, url_prefix='/auth')


@bp.route('/register', methods=('GET', 'POST'))
def register():
    #If the user has submitted
    if request.method == 'POST':
        #Store the form data
        username = request.form['username']
        password = request.form['password']
        #Store the db object
        db = get_db()
        error = None
        #Check the data has been retrieved
        if not username:
            error = 'Username is required.'
        elif not password:
            error = 'Password is required.'
            #Check if the user already exists
        elif db.execute(
            'SELECT id FROM user WHERE username = ?', (username,)
        ).fetchone() is not None:
            error = 'User {} is already registered.'.format(username)

        if error is None:
            #Insert the user's information, and hash the password
            db.execute(
                'INSERT INTO user (username, password) VALUES (?, ?)',
                (username, generate_password_hash(password))
            )
            #Commit to database
            db.commit()
            #Redirect to the login page
            return redirect(url_for('auth.login'))
        #Flash any errors
        flash(error)
    #Display the register page
    return render_template('auth/register.html')

@bp.route('/login', methods=('GET', 'POST'))
def login():
    #Check if the user has submitted
    if request.method == 'POST':
        #Store the form data
        username = request.form['username']
        password = request.form['password']
        #Store the database object
        db = get_db()
        error = None
        #Execute a SQL query
        user = db.execute(
            'SELECT * FROM user WHERE username = ?', (username,)
        ).fetchone()

        if user is None:
            error = 'Incorrect username.'
        #Check the user password
        elif not check_password_hash(user['password'], password):
            error = 'Incorrect password.'

        if error is None:
            #Clear the session and store the user id in the session object
            session.clear()
            session['user_id'] = user['id']
            #redirect to main page
            return redirect(url_for('index'))
    #Display any errors
        flash(error)
    #Render login page
    return render_template('auth/login.html')

@bp.before_app_request
def load_logged_in_user():
    #Get user_id
    user_id = session.get('user_id')
    #if no user, empty user object in 'g' object
    if user_id is None:
        g.user = None
    else:
        #Executre SQL query
        g.user = get_db().execute(
            'SELECT * FROM user WHERE id = ?', (user_id,)
        ).fetchone()


@bp.route('/logout')
def logout():
    #Clear the session and redirect to index
    session.clear()
    return redirect(url_for('index'))

#Wrapper to ensure login 
def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for('auth.login'))

        return view(**kwargs)

    return wrapped_view