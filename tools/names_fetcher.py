import urllib2
import re
import pickle
from pprint import pprint

def doit(offset):
    url = "http://www.buenosaires.gob.ar/areas/registrocivil/nombres/busqueda/buscador_nombres.php?offset=%s&menu_id=16082"

    page = urllib2.urlopen(url % offset)
    html = page.read()
    #print html
    #html = "tbody pepito tbody"
    k = re.search('tbody(.*)tbody', html, re.DOTALL)
    res = []
    for tr in re.findall("<tr >(.*?)</tr>", k.group(0)):
        name, gender, description = [x.replace("/","").replace("<td>","") for x in tr.split("</td><td>")]
        if gender in ("M","F"):
            res.append(({"name": name.lower(), "gender": gender}))
    return res


def doitall():
    offset = 0
    pagenr = 1
    res = []
    while True:
        print "page: %s, offset: %s" % (pagenr, offset)
        pagenames = doit(offset)
        if len(pagenames) == 0: return res
        offset += len(pagenames)
        res.extend(pagenames)
        pagenr += 1


def fetch():
    names = doitall()
    for n in names:
        print n
    print "TOTAL:", len(names)

    pickle.dump(names, open("names.pickle", "wb"))


def show():
    print 1
    names = pickle.load(open("names.pickle", "rb"))
    for name in names:
        pprint(name['name'])

def save():
    import sys
    sys.path.append("../frontend")
    names = pickle.load(open("names.pickle", "rb"))
    from gnip.mongo import MongoManager
    for name in names:
        print name,
        try:
            r = MongoManager.saveDocument("gender_names", name)
            print r
        except Exception, e:
            print e


if __name__ == "__main__":

    #fecth()
    save()