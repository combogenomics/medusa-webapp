#!/usr/bin/env python

import celery
import os
import shutil
import subprocess
import sys

from Bio import SeqIO

from utils import N50

def run_cmd(cmd, ignore_error=False):
    """
    Run a command line command
    Returns True or False based on the exit code
    """
    proc = subprocess.Popen(cmd,shell=(sys.platform!="win32"),
                    stdin=subprocess.PIPE,stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE)
    out = proc.communicate()
    return_code = proc.returncode

    t = open('log.txt', 'w')
    e = open('log.err', 'w')

    t.write('%s\n'%str(out[0]))
    if return_code != 0 and not ignore_error:
        e.write('Command (%s) failed w/ error %d\n'
                        %(cmd, return_code))
        e.write('%s\n'%str(out[1]))
        e.write('\n')

    return bool(not return_code)

def single_genome_stats(fname):
    d = {}

    lseqs = []
    for s in SeqIO.parse(fname, 'fasta'):
        lseqs.append(len(s))

    d['name'] = os.path.split(fname)[-1]
    d['length'] = sum(lseqs)
    d['contigs'] = len(lseqs)
    d['N50'] = N50(lseqs)
    
    return d

def genome_stats(draft, genomes):
    """
    Calculate general stats on the input genomes
    The data is returned back as a serializible dictionary
    """
    d = {}
    
    d['draft'] = single_genome_stats(draft)
    
    d['targets'] = []
    for g in genomes:
        d['targets'].append( single_genome_stats(g) )

    return d

@celery.task(name='tasks.run_medusa')
def run_medusa(wdir, draft, targets):
    sdir = os.getcwd()

    # Move all the medusa files
    shutil.copy(os.path.join(sdir, 'medusa', 'medusa.jar'), wdir)
    os.mkdir(os.path.join(wdir, 'medusa_scripts'))
    for f in os.listdir(os.path.join(sdir, 'medusa', 'medusa_scripts')):
        shutil.copy(os.path.join(sdir, 'medusa', 'medusa_scripts', f),
                    os.path.join(wdir, 'medusa_scripts'))

    # Before moving the genomes, calculte some stats
    # Length
    # Number of molecules
    # N50
    
    # Catch errors, may be due to incorrect format
    try:
        d = genome_stats(os.path.join(wdir,draft),
                        [os.path.join(wdir, x) for x in targets])
    except:
        return (False, {})

    # Create he drafts directory, move the genomes there
    try:
        os.mkdir(os.path.join(wdir, 'drafts'))
    except:pass
   
    # Rename the target genomes
    for g in targets:
        shutil.move(os.path.join(wdir, g),
                    os.path.join(wdir, 'drafts', g))
 
    # Move to working directory
    os.chdir(wdir)

    # Run Medusa
    cmd = 'java -jar medusa.jar -i %s -random 5 -f drafts -o %s'%(draft,
                                                          'scaffold.fasta')
    if not run_cmd(cmd):
        return (False, d)

    # Compute results
    try:
        d['scaffold'] = single_genome_stats('scaffold.fasta')
    except:
        return (False, d)

    try:
        # Be kind, remove the original files...
        shutil.rmtree('drafts')
        os.remove(draft)

        # ...and the medusa bundle
        shutil.rmtree('medusa_scripts')
        os.remove('medusa.jar')
    except:pass
    
    # Return back to the original directory
    os.chdir(sdir)

    return True, d
