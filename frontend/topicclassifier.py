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
        self.patterns = None
        self.wdict = None

    def getAllWords(self):
        res = set()
        for clue in self.topic_confidence_clues:
            if isinstance(clue, tuple):
                for w in clue[1:]:
                    res.add(w.lower())
            else:
                raise Exception("invalid clue: %s" % clue)
        return res

    def getPatterns(self):
        if self.patterns is None or self.wdict is None:
            self.patterns = []
            self.wdict = {}
            for clue in self.topic_confidence_clues:
                if isinstance(clue, tuple):
                    for w in clue[1:]:
                        self.wdict[w.lower()] = clue[0]
                else:
                    raise Exception("invalid clue: %s" % clue)
            if self.wdict:
                regexps = []
                kc = len(self.wdict.keys())
                kp = 0
                while kp < kc:
                    keys = self.wdict.keys()[kp:kp+25]
                    kp += 25
                    regexp = "(" + "|".join(["(?:(?<=\W)|^)(?P<CONFIDENCE_%s>%s)(?=\W|$)" % (c,k) for k,c in zip(keys, range(len(keys)))]) + ")"
                        #"\\b(?P<CONFIDENCE_%s>%s)\\b" % (c,k) for k,c in zip(keys, range(len(keys)))]) + ")"
                    #print regexp
                    self.patterns.append(re.compile(regexp, re.I|re.U))
        return self.patterns, self.wdict

    def __eq__(self, o):
        return self.topic_name == o.topic_name and self.topic_id == o.topic_id and self.topic_confidence_clues == o.topic_confidence_clues
    
    
    def calculateConfidence(self, text):
        patterns, wdict = self.getPatterns()
        confidence = 0
        for pattern in patterns:
            for mo in pattern.finditer(text):
                for k in mo.groupdict():
                    if mo.group(k) and k.startswith("CONFIDENCE"):
                        #print mo.group(k), wdict[mo.group(k).lower()]
                        confidence += self.wdict[mo.group(k).lower()]
        return confidence
    
    def extract(self, text):
        tm = None
        confidence = self.calculateConfidence(text)
        #confidence = 0
        if confidence > 0: #se podria configurar para cada topic
            tm = TopicMatch()
            tm.topic_name = self.topic_name
            tm.topic_id = self.topic_id
            tm.confidence = confidence
        return tm



if __name__ == '__main__':
    pass