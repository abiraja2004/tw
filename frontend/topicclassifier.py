#encoding: utf-8

import re
import pymongo

class TopicMatch(object):
    
    def __init__(self):
        self.topic_name = ""
        self.topic_id = ""
        self.confidence = 0
    

    def __repr__(self):
        return repr(u"<Topic: %s, Score: %s>" % (self.topic_name, self.confidence))
    
    def __unicode__(self):
        return u"<Topic: %s, Score: %s>" % (self.topic_name, self.confidence)
    
    def getDetail(self):
        return "DETAIL"

    def getDictionary(self):
        res = {}
        for k in ("topic_name","topic_id", "confidence"):
            res[k] = self.__getattribute__(k)
        return res
                          
class TopicClassifier(object):

    def __str__(self):
        return ""
    
    def __init__(self):
        self.topic_name = ""
        self.topic_id = ""
        self.topic_confidence_clues = []
    
    def calculateConfidence(self, text):
        def processClues(cluelist):
            res = 0
            wdict = {}
            for clue in cluelist:
                if isinstance(clue, tuple):
                    for w in clue[1:]:
                        wdict[w.lower()] = clue[0]
                else:
                    raise Exception("invalid clue: %s" % clue)
            if wdict:
                regexps = []
                kc = len(wdict.keys())
                kp = 0
                while kp < kc:                    
                    keys = wdict.keys()[kp:kp+25]
                    kp += 25
                    regexp = "(" + "|".join(["(?:(?<=\W)|^)(?P<CONFIDENCE_%s>%s)(?=\W|$)" % (c,k) for k,c in zip(keys, range(len(keys)))]) + ")"
                        #"\\b(?P<CONFIDENCE_%s>%s)\\b" % (c,k) for k,c in zip(keys, range(len(keys)))]) + ")"
                    #print regexp
                    pattern = re.compile(regexp, re.I|re.U)
                    for mo in pattern.finditer(text):
                        for k in mo.groupdict():
                            if mo.group(k) and k.startswith("CONFIDENCE"):
                                #print mo.group(k), wdict[mo.group(k).lower()]
                                res += wdict[mo.group(k).lower()]
            return res
        confidence = processClues(self.topic_confidence_clues)
        return confidence
    
    def extract(self, text):
        tm = None
        confidence = self.calculateConfidence(text)
        if confidence > 0: #se podria configurar para cada topic
            tm = TopicMatch()
            tm.topic_name = self.topic_name
            tm.topic_id = self.topic_id
            tm.confidence = confidence
        return tm


    
if __name__ == '__main__':
    pass