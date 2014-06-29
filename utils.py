#!/usr/bin/env python

def generate_time_hash(data):
    '''Return a sha256 hash
    
    Salted hash including the client data
    and date/time
    '''
    import hashlib
    from datetime import datetime
    from time import strftime
    
    return hashlib.sha256("salegrosso" +
             data +
             datetime.now().strftime("%Y%m%d%H%M%S%f")).hexdigest()

def generate_hash(data):
    '''Return a sha256 hash
    
    Salted hash including only the client data
    '''
    import hashlib
    
    return hashlib.sha256("salegrosso" +
             data).hexdigest()

# TODO: add credits
def N50(numlist):
    """
    Abstract: Returns the N50 value of the passed list of numbers.
    Usage:    N50(numlist)

    Based on the Broad Institute definition:
    https://www.broad.harvard.edu/crd/wiki/index.php/N50
    """
    numlist.sort()
    newlist = []
    for x in numlist :
        newlist += [x]*x
        # take the mean of the two middle elements af there are an even number
        # of elements.  otherwise, take the middle element
    if len(newlist) % 2 == 0:
        medianpos = len(newlist)/2
        return float(newlist[medianpos] + newlist[medianpos-1]) /2
    else:
        medianpos = len(newlist)/2
        return newlist[medianpos]
