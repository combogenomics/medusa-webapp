#!/usr/bin/env python

import os
import shutil
import subprocess
import sys
import json

from Bio import SeqIO

from utils import N50

from store import update_job

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

def medusa_version():
    cmd = 'java -jar medusa.jar -h'
    proc = subprocess.Popen(cmd,shell=(sys.platform!="win32"),
                    stdin=subprocess.PIPE,stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE)
    out = proc.communicate()
    
    try:
        return out[0].split('\n')[0].split()[-1]
    except:
        return None

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

def run_medusa(req_id, wdir, draft, targets):
    sdir = os.getcwd()

    update_job(req_id, 'status', 'Copying Medusa files')
    # Move all the medusa files
    shutil.copy(os.path.join(sdir, 'medusa-app', 'medusa.jar'), wdir)
    os.mkdir(os.path.join(wdir, 'medusa_scripts'))
    for f in os.listdir(os.path.join(sdir, 'medusa-app', 'medusa_scripts')):
        shutil.copy(os.path.join(sdir, 'medusa-app', 'medusa_scripts', f),
                    os.path.join(wdir, 'medusa_scripts'))

    # Before moving the genomes, calculte some stats
    # Length
    # Number of molecules
    # N50
    
    update_job(req_id, 'status', 'Computing initial statistics')
    # Catch errors, may be due to incorrect format
    try:
        d = genome_stats(os.path.join(wdir,draft),
                         [os.path.join(wdir, x) for x in targets])
    except Exception as e:
        raise Exception('Something is wrong with the input files (%s)' % e)

    update_job(req_id, 'status', 'Copying genome files')
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
    
    update_job(req_id, 'status', 'Getting Medusa version')
    d['version'] = medusa_version()

    update_job(req_id, 'status', 'Running Medusa')
    # Run Medusa
    cmd = 'java -jar medusa.jar -i %s -random 5 -f drafts -o %s'%(draft,
                                                          'scaffold.fasta')
    if not run_cmd(cmd):
        raise Exception('Medusa execution halted!')

    update_job(req_id, 'status', 'Computing final statistics')
    # Compute results
    d['scaffold'] = single_genome_stats('scaffold.fasta')
    
    update_job(req_id, 'status', 'Cleaning up')
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

    return d

if __name__ == "__main__":
    req_id = sys.argv[1]
    wdir = sys.argv[2]
    dname = sys.argv[3]
    genomes = sys.argv[4:]

    update_job(req_id, 'status', 'Job starting')
    try:
        result = run_medusa(req_id, wdir, dname, genomes)
        json.dump(result, open(os.path.join(wdir, 'result.json'), 'w'))
        update_job(req_id, 'status', 'Job done')
    except Exception as e:
        update_job(req_id, 'status', 'Job failed')
        update_job(req_id, 'error', str(e))
