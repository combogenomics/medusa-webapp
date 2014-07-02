Medusa-webapp
=============

Scaffold the contigs!

Test the server
---------------

Please make sure that redis is up and running.
Also, put in the "static" directory a 3.x version of bootstrap and jquery.min.js in the static/js directory.

    virtualenv venv
    source venv/bin/activate
    pip install -r requirements.txt
    python medusa.py

In another terminal:
    
    source venv/bin/activate
    celery -A medusa.celery worker

That's it! Open a browser on the same machine and got to 127.0.0.1:5000
