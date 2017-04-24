# -*- coding: utf-8 -*-
from sqlite3 import dbapi2 as sqlite3
from datetime import datetime
from flask import Flask, request, session, url_for, redirect, render_template, abort, g, flash, _app_ctx_stack, Markup
from werkzeug import check_password_hash, generate_password_hash
from io import StringIO, BytesIO
import pandas
import time

# this for debug only
# need to find good settigns for deploy

DATABASE = 'neat.db'
PER_PAGE = 1000
DEBUG = True
SECRET_KEY = 'secret key!'

app = Flask( __name__ )
app.config.from_object( __name__ )

# database connections
# basically taken from flask example
# badly need a rework

def get_db():
    """Opens a new database connection if there is none yet for the
    current application context.
    """
    # what is application context?
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
    """Command line tool: initializes the database."""
    db = get_db()
    with app.open_resource('schema.sql', mode='r') as f:
        db.cursor().executescript(f.read())
    db.commit()

@app.cli.command('initdb')
def initdb_command():
    """Command line tool: Creates the database tables."""
    init_db()
    print('Initialized the database.')

def query_db(query, args=(), one=False):
    """Queries the database and returns a list of dictionaries."""
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    return (rv[0] if rv else None) if one else rv

def get_user_id(user_name):
    """Convenience method to look up the id for a user_name."""
    rv = query_db('select user_id from user where user_name = ?', [user_name], one=True)
    return rv[0] if rv else None

def format_datetime(timestamp):
    """Format a timestamp for display."""
    return datetime.utcfromtimestamp(timestamp).strftime('%Y-%m-%d at %H:%M')

@app.before_request
def before_request():
    g.user = None
    if 'user_id' in session:
        g.user = query_db('select * from user where user_id = ?', [session['user_id']], one=True)

###### sign in/out of users

@app.route('/sign_in', methods=['GET', 'POST'])
def sign_in():
    """Logs the user in."""
    if g.user:
        return redirect(url_for('index'))
    error = None
    if request.method == 'POST':
        user = query_db('''select * from user where
            user_name = ?''', [request.form['user_name']], one=True)
        if user is None:
            error = 'No record of user name "{}". Try again?'.format(request.form['user_name'])
        elif not check_password_hash(user['pw_hash'],
                                     request.form['password']):
            error = 'Invalid password'
        else:
            flash('You were logged in')
            session['user_id'] = user['user_id']
            return redirect(url_for('index'))
    # if a get request
    return render_template('sign_in.html', error=error)

########### sign up!
# what information do we need at first? just email and password
# if somebody wants to order some plates, well, they gotta pay
# so we need a separate form for processing payments
# possibly just can outsource this?

@app.route('/sign_up', methods=['GET', 'POST'])
def sign_up():
    '''
    New customer sign up
    '''
    if g.user:
        return redirect(url_for('index'))
    error = None
    if request.method == 'POST':
        # if not request.form['user_name']:
            # error = 'You have to enter a user_name'
        if not request.form['email'] or \
                '@' not in request.form['email']:
            error = 'You have to enter a valid email address'
        elif not request.form['password']:
            error = 'You have to enter a password'
        elif get_user_id(request.form['email']) is not None:
            error = 'The email "{}" is already being used. Is this your email address? Please email us service@neatseq.com'.format(request.form['email'])
        else:
            db = get_db()
            db.execute('''insert into user (
              user_name, email, pw_hash) values (?, ?, ?)''',
              [request.form['email'], request.form['email'],
               generate_password_hash(request.form['password'])])
               # could add a date here (date joined)
            db.commit()
            flash('Creating sequencing dashboard')
            flash('You were successfully signed up and your sequencing dashboard was created. You can sign in now!')
            return redirect( url_for( 'sign_in' ) )
    # else, if this is a get request
    return render_template('sign_up.html', error=error)

@app.route('/logout')
def logout():
    """Logs the user out."""
    flash('You were logged out')
    session.pop('user_id', None)
    return redirect( '/' )

################# dashbaord, ordering plates, orderig sequeinc g

@app.route('/')
def index():

    # if no user, display home page
    if not g.user:
        return render_template( 'hero.html' )

    # if there is a user, then display dashboard
    plates = query_db('''select * from plate where owner = ?''', (g.user['user_id'],) )
    sequencing = query_db('''select * from sequencing where owner = ?''', (g.user['user_id'],) )
    return render_template('dash.html', plates=plates, sequencing=sequencing)

@app.route('/add_plate', methods=['POST'])
def add_plate():

    # abort if no user
    if 'user_id' not in session:
        abort(401)

    # # adds a set of plates to the user
    db = get_db()
    plates_requested = int( request.form[ 'plate_number_select' ].split()[0] )
    for pt in range( plates_requested ):
        db.execute('''insert into plate(owner,status,issue,date_ordered) values (?,?,?,?)''', (g.user['user_id'],0,0,int(time.time())))
        db.commit()
    flash( 'Order was sign_uped' )
    return redirect( url_for('index') )

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
        f_str = request.files[ 'file'].read().decode( 'utf-8' )
        df = pandas.read_csv( StringIO(f_str), index_col=0 )

    n_samples = len( df )

    db = get_db()
    db.execute(
        '''insert into sequencing(owner, plate_map, status, issue, reference_text) values (?,?,?,?,?)''',
        [g.user['user_id'], df.to_string(), 0, 0, request.form['reference_text'] ]
    )
    db.commit()
    flash( 'Plate was sign_uped' )
    return redirect( url_for( 'index' ) )


#################### admin dashboard

@app.route('/orders')
def orders():
    plates = query_db('select * from plate')
    sequencing = query_db('select * from sequencing')
    users = query_db('select * from user')
    return render_template( 'orders.html', plates=plates, sequencing=sequencing, users=users )


def html_status_codes( status_code ):
    st_code = str(status_code)
    codes = [
        ('0','●<span style="color:#aaa">●●●</span> <small>Order placed</small>'),
        ('1','<span style="color:#aaa">●</span>●<span style="color:#aaa;">●●</span> <small>Order placed</small>'),
        ('',''),
        ('',''),
    ]
    codes = dict(codes)
    if st_code in codes.keys():
        return Markup(codes[ st_code ])


# add some filters to jinja
app.jinja_env.filters['datetimeformat'] = format_datetime
app.jinja_env.filters['status'] = html_status_codes
