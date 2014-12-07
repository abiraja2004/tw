import subprocess
from subprocess import PIPE
import time
import os


def check_processes():
    r = subprocess.Popen('ps ax | grep python', shell=True, stdout=PIPE).stdout.read()
    print r
    
    r2 =  """337 ?        Sl   223:46 python twfetch.py --auth
    11893 ?        S      2:12 python datacollection.py --auth
    24057 pts/1    S      0:00 python application.py --auth
    24065 pts/1    Sl     0:14 /usr/bin/python application.py --auth
    25372 pts/1    S+     0:00 grep --color=auto python"""

    processes = [("twfetch", None),
                ("datacollection", "gnip"),
                ("application", "frontend"),
                #("geocoding", None)
                ]

    for p in processes:
        if r.find("python %s.py" % p[0]) < 0:
            start_process(p)
    


def start_process(p):
    oldcwd = os.getcwd()
    print "iniciando proceso:", p[0]
    back = ""
    if p[1]:
        os.chdir(p[1])
        back = "."
    subprocess.Popen(["%s./run_in_background.sh %s --auth" % (back,p[0])], shell=True)
    os.chdir(oldcwd)


if __name__ == "__main__":
    os.chdir("/home/pablo/tw")
    check_processes()
    