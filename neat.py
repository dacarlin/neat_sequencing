# -*- coding: utf-8 -*-
from sqlite3 import dbapi2 as sqlite3
from datetime import datetime
from flask import Flask, request, session, url_for, redirect, render_template, abort, g, flash, _app_ctx_stack
from werkzeug import check_password_hash, generate_password_hash
from io import StringIO, BytesIO
import pandas

DATABASE = '/tmp/neat.db'
PER_PAGE = 1000
DEBUG = True
SECRET_KEY = 'secret key!'

app = Flask( __name__ )
app.config.from_object( __name__ )

def get_db():
    """Opens a new database connection if there is none yet for the
    current application context.
    """
    top = _app_ctx_stack.top
    if not hasattr(top, 'sqlite_db'):
        top.sqlite_db = sqlite3.connect(app.config['DATABASE'])
        top.sqlite_db.row_factory = sqlite3.Row
    return top.sqlite_db

@app.teardown_appcontext
def close_database(exception):
    """Closes the database again at the end of the request."""
    top = _app_ctx_stack.top
    if hasattr(top, 'sqlite_db'):
        top.sqlite_db.close()

def init_db():
    """Initializes the database."""
    db = get_db()
    with app.open_resource('schema.sql', mode='r') as f:
        db.cursor().executescript(f.read())
    db.commit()

@app.cli.command('initdb')
def initdb_command():
    """Creates the database tables."""
    init_db()
    print('Initialized the database.')

def query_db(query, args=(), one=False):
    """Queries the database and returns a list of dictionaries."""
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    return (rv[0] if rv else None) if one else rv

def get_user_id(username):
    """Convenience method to look up the id for a username."""
    rv = query_db('select user_id from user where username = ?', [username], one=True)
    return rv[0] if rv else None

def format_datetime(timestamp):
    """Format a timestamp for display."""
    return datetime.utcfromtimestamp(timestamp).strftime('%Y-%m-%d at %H:%M')

@app.before_request
def before_request():
    g.user = None
    if 'user_id' in session:
        g.user = query_db('select * from user where user_id = ?', [session['user_id']], one=True)

###### login/logout of users and registering

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Logs the user in."""
    if g.user:
        return redirect(url_for('timeline'))
    error = None
    if request.method == 'POST':
        user = query_db('''select * from user where
            username = ?''', [request.form['username']], one=True)
        if user is None:
            error = 'Invalid username'
        elif not check_password_hash(user['pw_hash'],
                                     request.form['password']):
            error = 'Invalid password'
        else:
            flash('You were logged in')
            session['user_id'] = user['user_id']
            return redirect(url_for('timeline'))
    return render_template('login.html', error=error)

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Registers the user."""
    if g.user:
        return redirect(url_for('timeline'))
    error = None
    if request.method == 'POST':
        # if not request.form['username']:
            # error = 'You have to enter a username'
        if not request.form['email'] or \
                '@' not in request.form['email']:
            error = 'You have to enter a valid email address'
        elif not request.form['password']:
            error = 'You have to enter a password'
        # elif request.form['password'] != request.form['password2']:
            # error = 'The two passwords do not match'
        elif get_user_id(request.form['email']) is not None:
            error = 'The username is already taken'
        else:
            db = get_db()
            db.execute('''insert into user (
              username, email, pw_hash) values (?, ?, ?)''',
              [request.form['email'], request.form['email'],
               generate_password_hash(request.form['password'])])
            db.commit()
            flash('You were successfully registered and can login now')
            return redirect( url_for( 'login' ) )
    return render_template('register.html', error=error)

@app.route('/logout')
def logout():
    """Logs the user out."""
    flash('You were logged out')
    session.pop('user_id', None)
    return redirect( '/' )

################# dashbaord, ordering plates, orderig sequeinc g

@app.route('/')
def timeline():
    '''Renders the user dashboard (if no user is logged in, displays marketing page!)'''
    if not g.user:
        return render_template( 'hero.html' )

    plates = query_db('''select * from plate where owner = ?''', (g.user['user_id'],) )
    sequencing = query_db('''select * from sequencing where owner = ?''', (g.user['user_id'],) )

    return render_template('dash.html', plates=plates, sequencing=sequencing)

@app.route('/add_message', methods=['POST'])
def add_message():
    """Requests a set of plates for this user"""

    if 'user_id' not in session:
        abort(401)

    db = get_db()
    plates_requested = int( request.form[ 'plate_number_select' ] )
    for pt in range( plates_requested ):
        db.execute('''insert into plate(owner) values (?)''', (g.user['user_id'],))
        db.commit()
    flash( 'Order was registered' )
    return redirect( url_for('timeline') )

@app.route('/order_sequencing', methods=['POST'])
def order_sequencing():
    """The user places an order for sequencing"""
    if 'user_id' not in session:
        abort(401)

    print( 'File keys:', list( request.files.keys() ) )

    if 'file' not in request.files:
        flash( 'No file part' )
        return redirect( '/' )
    file_handle = request.files['file']
    if file_handle.filename == '':
        flash( 'No file selected' )
        return redirect( '/' )
    if file_handle:
        bytes_io = BytesIO( request.files['file'].read() )
        byte_str = bytes_io.read()
        text_obj = byte_str.decode('UTF-8')  # Or use the encoding you expect
        str_obj = StringIO(text_obj)
        df = pandas.read_csv( str_obj, index_col=0 )

    db = get_db()
    db.execute('''insert into sequencing(owner) values (?)''', (g.user['user_id'],))
    db.commit()
    flash( 'Plate was registered' )
    return redirect( url_for( 'timeline' ) )

# add some filters to jinja
app.jinja_env.filters['datetimeformat'] = format_datetime

#################### admin and process

@app.route('/orders')
def orders():
    plates = query_db('select * from plate')
    sequencing = query_db('select * from sequencing')
    print( plates )
    print( dir( plates[0] ) )
    print( list( plates[0].keys() ) )
    return render_template( 'orders.html', plates=plates, sequencing=sequencing )
