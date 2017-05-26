from flask import Flask, request, session, url_for, redirect, render_template, abort, g, flash, _app_ctx_stack, Markup
from werkzeug import check_password_hash, generate_password_hash
import pandas
from bokeh.plotting import figure
from bokeh.models import FixedTicker, FuncTickFormatter
from bokeh.resources import CDN
from bokeh.embed import file_html
from itertools import product
from sqlite3 import dbapi2 as sqlite3
import random
from io import StringIO, BytesIO
import time
from datetime import datetime

from .display import html_status_codes, html_status_codes_human

######################################################
######################################################
# this for debug only
# need to find good settigns for deploy

DATABASE = 'neat.db'
PER_PAGE = 1000
DEBUG = True
SECRET_KEY = 'secret key!'

app = Flask( __name__ )
app.config.from_object( __name__ )

######################################################
######################################################
# database connections
# basically taken from flask example

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

def get_user_id(email):
    """Convenience method to look up the id for a user_name."""
    rv = query_db('select id from user where email = ?', [email], one=True)
    return rv[0] if rv else None

def format_datetime(timestamp):
    """Format a timestamp for display."""
    return datetime.utcfromtimestamp(timestamp).strftime('%Y-%m-%d at %H:%M')

@app.before_request
def before_request():
    g.user = None
    if 'user_id' in session:
        g.user = query_db('select * from user where id = ?', [session['user_id']], one=True)

###### sign in/out of users
######

@app.route('/sign_in', methods=['GET', 'POST'])
def sign_in():
    """Logs the user in."""
    if g.user:
        return redirect(url_for('index'))
    error = None
    if request.method == 'POST':
        user = query_db('''select * from user where
            email = ?''', [request.form['email']], one=True)
        if user is None:
            error = 'No record of email "{}". Try again?'.format(request.form['email'])
        elif not check_password_hash(user['pw_hash'],request.form['password']):
            error = 'Invalid password'
        else:
            flash('You were logged in')
            session['user_id'] = user['id']
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
            db.execute('''
                insert into user
                (email, pw_hash, date_joined)
                values (?, ?, ?)''',
                [
                    request.form['email'],
                    generate_password_hash(request.form['password']),
                    time.time(),
                ]
            ) # ends "execuate"
            db.commit()
            # now need to read this user out of the db
            # to AUTO LOG IN motherfuckers
            user = query_db('''select * from user where
                email = ?''', [request.form['email']], one=True)
            session['user_id'] = user['id']
            flash('Thanks for creating an account, and welcome to Neat!')
            return redirect(url_for('index'))

    # else, if this is a get request
    return render_template('sign_up.html', error=error)

@app.route('/logout')
def logout():
    """Logs the user out."""
    flash('You were logged out')
    session.pop('user_id', None)
    return redirect( url_for( 'sign_in') )

################# dashbaord, ordering plates, orderig sequeinc g
##############

@app.route('/')
def index():

    # if no user, display home page
    if not g.user:
        return render_template( 'hero.html' )

    # if there is a user, then display dashboard
    plates = query_db('''select * from plate where owner = ?''', (g.user['id'],) )
    sequencing = query_db('''select * from sequencing where owner = ?''', (g.user['id'],) )
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
        db.execute('''insert into plate(owner,status,issue,date_ordered) values (?,?,?,?)''', (g.user['id'],0,0,int(time.time())))
        db.commit()
    flash( 'Your order was recieved! Plates are immediately shown in the management console, and arrive in 2-3 days'.format(plates_requested) )
    return redirect( url_for('index') )

def map_well_to_coords(well):
    def map_letter_to_int(letter):
        d = dict(zip('ABCDEFGHIJKLMNOP',range(1,17)))
        return d[letter]
    letter = well[0]
    number = well[1:]
    x = int(number)
    y = map_letter_to_int(letter)
    return x, y

@app.route('/order_sequencing', methods=['POST'])
def order_sequencing():

    # abort if no user
    if 'user_id' not in session:
        abort(401)
    error = ''

    if 'file' not in request.files:
        flash( 'No file part' )
        return redirect( '/' )
    file_handle = request.files['file']
    if file_handle.filename == '':
        flash( 'No file selected' )
        return redirect( '/' )
    if file_handle:
        f_str = StringIO(request.files['file'].read().decode('utf-8'))

    try:
        df = pandas.read_csv(f_str, index_col=0).dropna()
    except Exception as e:
        flash( 'Could not parse plate map' )

    plot = figure(tools='', plot_width=480, plot_height=320,)
    plot = figure(tools='', plot_width=480, plot_height=320,)
    plot.xgrid.grid_line_color = None
    plot.ygrid.grid_line_color = None
    plot.xaxis[0].ticker=FixedTicker(ticks=list(range(0+1,24+1)))
    plot.yaxis[0].ticker=FixedTicker(ticks=list(range(0+1,16+1)))
    plot.logo=None

    xlabel = {i+1: s for i, s in enumerate('ABCDEFGHIJKLMNOPQRSTUVWX')}
    ylabel = {i+1: s for i, s in enumerate(list(range(1,17))[::-1])}
    plot.xaxis.formatter = FuncTickFormatter(code="""var labels = %s;return labels[tick];""" % xlabel)
    plo.tyaxis.formatter = FuncTickFormatter(code="""var labels = %s;return labels[tick];""" % ylabel)
    rt
    plot.outline_line_width = 1
    plot.outline_line_alpha = 1
    plot.outline_line_color = "black"
    plot.background_fill_color = "black"
    plot.background_fill_alpha = 0.05

    if df is not None:
        print(df)
        wells = [map_well_to_coords(n) for n in df.index]
        x, y = zip(*wells)
        x_empty, y_empty = zip(*product(range(1,25), range(1,17)))
        plot.scatter(x, y, size=12, color="blue", alpha=0.5)
        plot.scatter(x_empty, y_empty, size=10, color="black", alpha=0.1)
        session['dataframe_pkg'] = (wells, request.form['reference_text'])

    html = Markup(file_html(plot, CDN, "my plot"))

    # need to also collect the plate that will be used, and update its status
    plate_nominated = int(request.form['plate_id'].replace('Plate ID: ','').strip())
    session['plate_nominated'] = plate_nominated

    return render_template('order_seq.html',error=error,chart=html)


@app.route('/commit_seq', methods=['POST'])
def commit_seq():

    wells, reference_text = session['dataframe_pkg']
    plate_id = session['plate_nominated']

    # add the sequencing order to the database
    db = get_db()
    db.execute(
        '''insert into sequencing(owner, map, status, issue, reference_text) values (?,?,?,?,?)''',
        [g.user['id'], 'la', 0, 0, reference_text]
    )
    db.commit()

    # update plate status
    update_status(plate_id, 2)

    flash( 'Your order for sequencing {} samples was recieved'.format(len(wells)) )

    return redirect( url_for( 'index' ) )

######################################################
######################################################
#################### admin dashboard #################
######################################################
######################################################

def update_status( plate_id, new_status ):
    db = get_db()
    db.execute('update plate set status = ? where id = ?', (new_status, plate_id))
    db.commit()

def flag(plate_id):
    db = get_db()
    db.execute('update plate set issue = 1 where id = ?', (plate_id))
    db.commit()

result_pkg = {
    'sequencing_id': 1,
    'url': 'http://google.com',
    'heatmap_data': [ 0.1, 0.2, 0.3 ],
}

def update_url( result_pkg ):
    db = get_db()
    db.execute('update sequencing set url = ? where id = ?', (result_pkg['url'], result_pkg['sequencing_id']))
    db.commit()

@app.route('/orders', methods=['POST', 'GET'])
def orders():
    if request.method == 'POST':
        # we are updating something
        # but what?

        if request.form['form_tag'] == 'add_users':
            for n in range(25):
                un = 'user_{}@email.com'.format(int(random.random()*1e4))
                pw_hash = generate_password_hash('password')
                ex_str = 'insert into user (email,date_joined,pw_hash) values (?,?,?)'
                ex_iter = [un,datetime.now(),pw_hash]
                db = get_db()
                db.execute(ex_str, ex_iter)
                db.commit()
            print('Added 25 new users with {} new plates and {} new sequencing orders')

        elif request.form['form_tag'] == 'advance':
            pt_id = request.form['plate_id']
            update_status(pt_id, request.form['new_status'])

        elif request.form['form_tag'] == 'flag':
            pt_id = request.form['plate_id']
            flag(pt_id)

        return redirect( url_for( 'orders') )

    else:
        plates = query_db('select * from plate')
        sequencing = query_db('select * from sequencing')
        users = query_db('select * from user')


        #users is a list of dicts. let's update it a bit
        us = []
        for k in users:
            new_u = { 'id': k['id'], 'email': k['email'], 'date_joined': k['date_joined'], }
            plates = query_db('select * from plate where owner = ?', (new_u['id'],))
            seq = query_db('select * from sequencing where owner = ?', (new_u['id'],))
            us.append(new_u)
            new_u.update({'n_plates':len(plates)})
            new_u.update({'n_seq':len(seq)})

        return render_template( 'orders.html', plates=plates, sequencing=sequencing, users=us )


@app.route('/account', methods=['POST', 'GET'])
def account():
    '''
    For managing user accounts.

    Should only need to be one page.
    '''

    if request.method == 'POST':
        # we are changing some thing in the form!
        pass

    # else, is get request
    return render_template('account.html')

######################################################
######################################################
# add some filters to jinja
app.jinja_env.filters['datetimeformat'] = format_datetime
app.jinja_env.filters['status'] = html_status_codes
app.jinja_env.filters['status_human'] = html_status_codes_human
