#!/usr/bin/env python2

from multiprocessing import Process, current_process
import subprocess
import time
import signal
import fcntl
import sys
import os

logdir = '/var/log/satellite-metrics/'

def signal_handler_main(signal, frame):
    global interrupted
    interrupted = True
    print("Exit criteria received. Waiting for subprocess.")
    for p in startedp:
        p.terminate()
    print("Terminating " + current_process().name)

def signal_handler_child(signal, frame):
    global interrupted
    interrupted = True
    print("Terminating " + current_process().name)


def ensure_dir(f):
    d = os.path.dirname(f)
    if not os.path.exists(d):
        os.makedirs(d)
        print("Created directory " + f)

def run_child(childinfo):
    signal.signal(signal.SIGINT, signal_handler_child)
    signal.signal(signal.SIGTERM, signal_handler_child)
    global interrupted
    try:
        logfile = open(logdir + childinfo["name"] + ".log", "a+")
        fcntl.flock(logfile, fcntl.LOCK_EX | fcntl.LOCK_NB)
        while ( interrupted == False ):
            subprocess.call(childinfo["command"], shell=True, stderr=subprocess.STDOUT, stdout=logfile)
            # after ctrl+c sleep will immediately return, but cycle will continue
            time.sleep(float(childinfo["sleep"]))
        fcntl.flock(logfile, fcntl.LOCK_UN)
    except IOError as e:
        print("IOError " + str(e) + " on " + childinfo["name"] + ". Exiting")

if __name__ == '__main__':
    global interrupted
    interrupted = False
    global startedp
    startedp = []
    signal.signal(signal.SIGINT, signal_handler_main)
    signal.signal(signal.SIGTERM, signal_handler_main)

    ensure_dir(logdir)

    monitoritem = []
    monitoritem.append({'name':'qpid_stat','sleep':'60','command':'date ; qpid-stat --ssl-certificate /etc/pki/katello/certs/java-client.crt --ssl-key /etc/pki/katello/private/java-client.key -b "amqps://localhost:5671" -q'})
    monitoritem.append({'name':'ps_rss','sleep':'2','command':'date ; ps aux --sort -rss | head -n20'})
    monitoritem.append({'name':'tasks_running_count','sleep':'10','command':'echo "$(  hammer -r --output=csv task list --search "state != stopped"|wc -l ) $(date)"'})

    for child in monitoritem:
        try:
            pchild = Process(target=run_child, name=child["name"], args=(child,))
            pchild.start()
            startedp.append(pchild)
            print("Monitor for " + child["name"] + " started")
        except e:
            print("Error received while starting " + child["name"] + ": " + e)
    print("Sleeping while processes are running")
    sys.exit(0)
