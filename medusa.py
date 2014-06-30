#!/usr/bin/env python

import os
from flask import Flask, request, session, g, redirect, url_for, abort, \
     render_template, flash
from werkzeug.utils import secure_filename

from utils import generate_hash
from utils import generate_time_hash

from worker import make_celery
from worker import is_task_ready

from store import add_job
from store import retrieve_job

import settings

app = Flask(__name__)

# App config from settings.py
app.config.from_object(settings)

# Init celery
celery = make_celery(app)

# Later import after celery has been set up
from tasks import run_medusa

@app.route('/')
def index():
    # TODO: Here add sessions to rember past entries in the form?
    return render_template('index.html')

@app.route('/run', methods=['GET', 'POST'])
def run():
    # Here handle submissions and run the analysis
    # Send emails on failures, success
    # Use redis to store user stats (hashed for privacy)
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
        #if draft and allowed_file(draft.filename):
        if draft:
            filename = secure_filename(draft.filename)
            draft.save(os.path.join(wdir, filename))
            dname = filename
        else:
            flash(u'Something went wrong with your draft genome', 'error')
            return redirect(url_for('index'))
       
        # Save the genomes files
        genomes = set()
        try:
            for genome in request.files.getlist('genomes'):
                filename = secure_filename(genome.filename)
                genome.save(os.path.join(wdir, filename))
                genomes.add(filename)
        except:
            flash(u'Something went wrong with your target genome', 'error')
            return redirect(url_for('index'))
                
        # Check email, hash it
        email = request.form['email']
        if email:
            hemail = generate_hash(email)
        else:
            flash(u'Something went wrong with your email', 'error')
            return redirect(url_for('index'))
        
        # Notify me?
        if 'notify' in request.form:
            notify = True
        else:
            notify = False

        # Secure my results?
        passphrase = request.form['passphrase']
        if passphrase:
            hpass = generate_hash(passphrase)
        else:
            hpass = None
        
        # Submit the job
        # Then redirect to the waiting pagei
        try:
            result = run_medusa.delay(wdir, dname, genomes)
        except:
            flash(u'Could not submit your job', 'error')
            return redirect(url_for('index'))
            
        try:
            # Send details to redis
            add_job(req_id, request.host, hemail, result.task_id, hpass)
        except:
            flash(u'Could not save your job details', 'error')
            return redirect(url_for('index')) 

        return redirect(url_for('results',
                        req_id_id=req_id))

    # No POST, return to start
    flash(u'No job details given, would you like to start a new one?', 'warning')
    return redirect(url_for('index'))

@app.route('/results/<req_id>')
def results(req_id):
    # Here show the results or the wait page
    # Get the right job using the session or the hash key, a la contiguator
    # TODO: get details from redis
    # TODO: check passphrase
    if is_task_ready(run_medusa, task_id):
        return str(run_medusa.AsyncResult(task_id).get())
    else:
        return render_template('waiting.html')

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
