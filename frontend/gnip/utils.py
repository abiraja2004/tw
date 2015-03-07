import threading

class MyThread(threading.Thread):
    #instances = []
    def __init__(self):
        threading.Thread.__init__(self)
        #MyThread.instances.append(self)
        self.setName(self.__class__.__name__)
        
    @classmethod
    def checkFinalization(clsobj):
        for t in threading.enumerate():
            if isinstance(t, MyThread):
                print "Thread Alive: %s " % t.getName()
