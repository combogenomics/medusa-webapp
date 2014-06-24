#!/usr/bin/env python

import celery
import os
import shutil

@celery.task(name='tasks.run_medusa')
def run_medusa(wdir, draft, targets):
    sdir = os.getcwd()

    # Move all the medusa files
    shutil.copy(os.path.join(sdir, 'medusa', 'medusa.jar'), wdir)
    os.mkdir(os.path.join(wdir, 'medusa_scripts'))
    for f in os.listdir(os.path.join(sdir, 'medusa', 'medusa_scripts')):
        shutil.copy(os.path.join(sdir, 'medusa', 'medusa_scripts', f),
                    os.path.join(wdir, 'medusa_scripts'))
   
    # Rename the target genomes
    for g in targets:
        shutil.move(os.path.join(wdir, g),
                    '%s.inp'%os.path.join(wdir, g))
 
    # Move to working directory
    os.chdir(wdir)

    # TODO: Run Medusa

    # TODO: Compute results, prepare JSON

    return draft, targets
