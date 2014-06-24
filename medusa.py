#!/usr/bin/env python

import os
from flask import Flask, request, session, g, redirect, url_for, abort, \
     render_template, flash
from werkzeug.utils import secure_filename

from utils import generate_hash
from utils import generate_time_hash

from worker import make_celery
from worker import is_task_ready


app = Flask(__name__)

# App config - empty?
app.config.from_object(__name__)
app.config.update(dict(
    DEBUG=True,
    SECRET_KEY='development key',
    CELERY_BROKER_URL='redis://localhost:6379',
    CELERY_RESULT_BACKEND='redis://localhost:6379',
))
app.config.from_envvar('FLASKR_SETTINGS', silent=True)

celery = make_celery(app)

# Later import after celery has been set up
from tasks import run_medusa

UPLOAD_FOLDER = 'uploads'
# Here how do we handle fasta extensions?
ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'])
#

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    # Here add sessions to rember past entries in the form?
    # Sessions may be used also to grant access only to the submitter
    return render_template('index.html')

@app.route('/run', methods=['GET', 'POST'])
def run():
    # Here handle submissions and run the analysis
    # Send emails on failures, success
    # Use redis or sqlite to store user stats (hashed for privacy)
    if request.method == 'POST':
        # First things first, compute user hash

        req_id = generate_time_hash(request.host)

        # To avoid slow-downs in the running directory
        # create subdirs w/ the first 2 chars of the hash
        h2c = req_id[:2]
        try:
            os.mkdir(os.path.join(app.config['UPLOAD_FOLDER'],
                                  h2c))
        except:
            pass

        # Prepare the working directory
        # Our hash scheme ensures that it should be unique
        wdir = os.path.join(app.config['UPLOAD_FOLDER'],
                            h2c, req_id)
        wdir = os.path.abspath(wdir)
        os.mkdir(wdir)

        # Save input files
        draft = request.files['draft']
        if draft and allowed_file(draft.filename):
            filename = secure_filename(draft.filename)
            draft.save(os.path.join(wdir, filename))
            dname = filename
        else:
            # TODO: something wrong here
            # return an error message
            pass
       
        # Save the genomes files
        genomes = set()
        for genome in request.files.getlist('genomes'):
            filename = secure_filename(genome.filename)
            genome.save(os.path.join(wdir, filename))
            genomes.add(filename)
        else:
            # TODO: something wrong here
            # return an error message
            pass
                
        # Check email, hash it
        email = request.form['email']
        if email:
            hemail = generate_hash(email)
        else:
            # TODO: something wrong here
            # return an error message
            pass
        
        # Notify me?
        if 'notify' in request.form:
            notify = True
        else:
            notify = False

        # Secure my results?
        passphrase = request.form['passphrase']
        hpass = generate_hash(passphrase)
        
        # TODO: check my inputs
        # TODO: FASTA checker

        # TODO: send details to redis
        # Mostly to check if the job is ready

        # Submit the job
        # Then redirect to the waiting page
        result = run_medusa.delay(wdir, dname, genomes)        
 
        print req_id        

        return redirect(url_for('results',
                        task_id=result.task_id))
    # No POST, check job status
    # redirect if finished
    # show a waiting page otherwise
    return redirect(url_for('index'))

@app.route('/results/<task_id>')
def results(task_id):
    # Here show the results or the wait page
    # Get the right job using the session or the hash key, a la contiguator
    if is_task_ready(run_medusa, task_id):
        return str(run_medusa.AsyncResult(task_id).get())
    else:
        return '<html><head><meta HTTP-EQUIV="REFRESH" content="10"></head></html>'

@app.route('/stats')
def stats():
    # Here show the server statistics, using redis as datastore
    # Generate plots on the fly using d3.js?
    # Another function may be needed then to get jsons
    from time import asctime
    if 'time' not in session:
        session['time'] = asctime()
    return render_template('index.html', time=session['time']) # Here some data

@app.route('/admin')
def admin():
    # Here admin section: upload a new medusa
    # Clean manually the jobs
    from time import asctime
    if 'time' not in session:
        session['time'] = asctime()
    return render_template('index.html', time=session['time']) # Here some data

if __name__ == '__main__':
    app.run()
