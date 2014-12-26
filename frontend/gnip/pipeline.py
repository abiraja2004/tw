from utils import MyThread
from Queue import Queue, Empty
import traceback

class Pipeline(object):
    REGISTERED_STAGES = []
    
    class Stage(object):
        def processItem(self, item):
            return item

    class DummyTimedStage(object):
        def __init__(self, t):
            self.t=t
        def processItem(self, item):
            time.sleep(self.t)
            
            return item
        
    class StageThread(MyThread):
        def __init__(self, stage, queues):
            MyThread.__init__(self)
            self.stage = stage
            self.source_queue = queues[0]
            self.next_queue = queues[1]
            self.errors_queue = queues[2]
            self.finish_flag = False

        def stopWorking(self):
            self.source_queue.join()
            self.finish_flag = True
            
        def run(self):
            while not self.finish_flag:
                try:
                    item = self.source_queue.get(True, 1)
                    try:
                        item = self.stage.processItem(item)
                    except Exception, e:
                        error_string = traceback.format_exc()
                        self.errors_queue.put({"item": item, "error": error_string, "stage": self.__class__.__name__})
                        item = None
                        print error_string
                    self.source_queue.task_done()
                    if item: self.next_queue.put(item)
                except Empty, e:
                    pass
            
    def __init__(self):
        self.source_queue = Queue()
        self.output_queue = self.source_queue
        self.errors_queue = Queue()
        self.stages = []
        self.stage_queues = {}
        self.stage_threads = {}
        
    def getSourceQueue(self):
        return self.source_queue
    
    def appendStage(self, stage):
        self.stages.append(stage)
        if len(self.stages) > 1: #no es el primer stage
            self.stage_queues[stage] = (self.stage_queues[self.stages[-2]][1], Queue(), self.errors_queue)
        else:
            self.stage_queues[stage] = (self.source_queue, Queue(), self.errors_queue)
        self.output_queue = self.stage_queues[stage][1]
        self.stage_threads[stage] = Pipeline.StageThread(stage, self.stage_queues[stage])
        self.stage_threads[stage].setName(stage.__class__.__name__)
        
    def startWorking(self):
        for stage in self.stages:
            self.stage_threads[stage].start()

    def stopWorking(self):
        for stage in self.stages:
            self.stage_threads[stage].stopWorking()
            self.stage_threads[stage].join()
            
    """
    def join(self):
        self.source_queue.join()
        for stage in self.stages:
            self.stage_queues[stage][1].join()
    """
            
    def getStats(self):
        res = {}
        res['Stage Count'] = len(self.stages)
        res['Errors Queue Count'] = self.errors_queue.qsize()
        res['Stages'] = []
        for stage in self.stages:
            d = {}
            d['Stage Class'] = stage.__class__.__name__
            d['Source Queue count'] = self.stage_queues[stage][0].qsize()
            d['Output Queue count'] = self.stage_queues[stage][1].qsize()
            res['Stages'].append(d)
        res['Output Queue Size'] = self.output_queue.qsize()
        return res
