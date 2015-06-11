import threading
from datetime import datetime, timedelta
import time

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


class cached(object):
    def __init__(self, *args, **kwargs):
        self.cached_function_responses = {}
        self.default_max_age = kwargs.get("default_cache_max_age", timedelta(seconds=0))

    def __call__(self, func):
        def inner(*args, **kwargs):
            max_age = kwargs.get('max_age', self.default_max_age)
            if not max_age or func not in self.cached_function_responses or (datetime.now() - self.cached_function_responses[func]['fetch_time'] > max_age):
                if 'max_age' in kwargs: del kwargs['max_age']
                res = func(*args, **kwargs)
                self.cached_function_responses[func] = {'data': res, 'fetch_time': datetime.now()}
            return self.cached_function_responses[func]['data']
        return inner




if __name__ == "__main__":

    @cached(default_max_age = timedelta(seconds=6))
    def cacheable_test(a,**kwargs):
        print "in cacheable test: ", kwargs
        return (a, datetime.now())

    print cacheable_test(1,max_age=timedelta(seconds=5))
    print cacheable_test(2,max_age=timedelta(seconds=5))
    time.sleep(7)
    print cacheable_test(3,max_age=timedelta(seconds=5))
