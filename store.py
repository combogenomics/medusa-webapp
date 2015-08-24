#!/usr/bin/env python

import redis
import time

def add_job(req_id, ip, email, task_id, passphrase=None):
    r = redis.Redis()
    
    jid = 'medusa_%s'%req_id

    r.zadd('medusajobs', jid, time.time())

    r.hset(jid, 'ip', ip)
    r.hset(jid, 'email', email)
    r.hset(jid, 'task_id', task_id)
    r.hset(jid, 'date', time.asctime())

    if passphrase is not None:
        r.hset(jid, 'passphrase', passphrase)

def retrieve_job(req_id):
    r = redis.Redis()

    return r.hgetall('medusa_%s'%req_id)

def cumulative_jobs():
    r = redis.Redis()

    i = 0

    for j in r.zrange('medusajobs', 0, -1):
        i += 1
        date = r.hget(j, 'date')
        yield (i, date)

def unique_emails():
    r = redis.Redis()

    ip = set()

    for j in r.zrange('medusajobs', 0, -1):
        i = r.hget(j, 'email')
        date = r.hget(j, 'date')
        if i not in ip:
            ip.add(i)
            yield (len(ip), date)

def unique_ips():
    r = redis.Redis()

    ip = set()

    for j in r.zrange('medusajobs', 0, -1):
        i = r.hget(j, 'ip')
        date = r.hget(j, 'date')
        if i not in ip:
            ip.add(i)
            yield (len(ip), date)

