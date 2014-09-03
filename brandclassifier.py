#encoding: utf-8

import re
import pymongo

class ProductMatch(object):
    brand = ""
    product = ""
    sentiment = None
    brand_matched_word = ""
    brand_matched_pos = (-1, -1)
    product_matched_word = ""
    product_matched_pos = (-1, -1)
    source = ""
    patten = ""
    
    def __unicode__(self):
        return u"<Brand: %s, Product: %s>" % (self.brand, self.product)
    
    def getDetail(self):
        ctx = 10
        res  = u"Brand: %s, match: %s, context: %s" % (self.brand, self.brand_matched_word, self.source[(self.brand_matched_pos[0]-ctx):(self.brand_matched_pos[1]+ctx)])
        res = res + "\nProduct: %s, match: %s, context: %s" % (self.product, self.product_matched_word, self.source[(self.product_matched_pos[0]-ctx):(self.product_matched_pos[1]+ctx)])
        return res


JUGO_CONFIDENCE_CLUES = [(5, "juguito", "juguitos", "jugo", "jugos", "tomas", u"tomás", u"tomá", "toma", "tomando", "tomar", "tome", u"tomé", "tomen", "beber", "vaso", "jarra")]
FUTBOL_CONFIDENCE_CLUES = [(100, "club", "plantilla", "torneo", "torneos", "campeonato" "campeonatos", "campeon", u"campeón", "campeones", "local", "visitante", "locales", "visitantes", "contra", "vs", "entrada", "entradas",  "ganarle", "ganamos", "dirigente", "dirigentes", "ganaron", "perdieron", "empataron", "empate", "empaten", "empatamos", "hincha", "hinchas", "jugar", "futbol", u"fútbol", "jugador", "jugadores", "ganando", "perdiendo", "perder","titular", "titulares", "suplente", "suplentes", "tecnico", u"técnico", "dt", "plantel", "enfrentamiento", "enfrentamientos", "equipo", "equipos", "partido", "cancha", "estadio", "derrota", "derrotas", "victoria", "victorias","ganar", "previa")]
AVION_CONFIDENCE_CLUES = [(5, "air", u"avión", "aviones","aerolinea", u"aerolínea", "aerolineas", u"aerolíneas", "vuelo", "vuelos", "vuelen", "vuela", "volar", "volara", "volare", u"volaré", u"volará", "volaran", u"volarán", "aeropuerto", "pasaje", "pasajes", "ticket", "tickets", "aereo", "@iberia")]
                          
class BrandClassifier(object):

    #name = "Brand"
    #brands= ["Brand"]
    #products = ["Product 1", "Product 2", {u"Product 3": ["prod3", u"producto 3"]}]
    
    def __str__(self):
        return ""
    
    def __init__(self):
        self.brand_regexps = []  #lista de tuplas (regexp, rule)
        self.product_regexps = {} #diccionario: producto->lista de tuplas (regexp,rule)
        self.name = ""
        self.products = {}
        self.product_list = []
    
        self.brand_confidence_clues = []
        self.product_confidence_clues = {}
        
        self.pld_counter = 1
        self.bld_counter = 1
        self.brandLookupDict = {}
        self.rule = ""
    

    def getProductLookupWords(self):
        self.productLookupDict = {}
        res = []
        for p in self.products:
            if isinstance(p, basestring): 
                res.append("(?P<PLD_%s>%s+)" % (self.pld_counter,p))
                self.productLookupDict["PLD_%s"%self.pld_counter] = p
                self.pld_counter += 1
            elif isinstance(p, dict):
                for k,v in p.items():
                    res.append("(?P<PLD_%s>%s+)" % (self.pld_counter, k))
                    self.productLookupDict["PLD_%s"%self.pld_counter] = k
                    self.pld_counter += 1                    
                    if isinstance(v, basestring): 
                        res.append("(?P<PLD_%s>%s+)" % (self.pld_counter,v))
                        self.productLookupDict["PLD_%s"%self.pld_counter] = k
                        self.pld_counter += 1                    
                    elif isinstance(v, list): 
                        for w in v:
                            res.append("(?P<PLD_%s>%s+)" % (self.pld_counter,w))            
                            self.productLookupDict["PLD_%s"%self.pld_counter] = k
                            self.pld_counter += 1                                                            
        return res

    def getBrandLookupWords(self):
        res = []
        p = self.name
        if isinstance(p, basestring): 
            res.append("(?P<BLD_%s>%s+)" % (self.bld_counter,p))
            self.brandLookupDict["BLD_%s"%self.bld_counter] = p
            self.bld_counter += 1
        elif isinstance(p, dict):
            for k,v in p.items():
                res.append("(?P<BLD_%s>%s+)" % (self.bld_counter, k))
                self.brandLookupDict["BLD_%s"%self.bld_counter] = k
                self.bld_counter += 1                    
                if isinstance(v, basestring): 
                    res.append("(?P<BLD_%s>%s+)" % (self.bld_counter,v))
                    self.brandLookupDict["BLD_%s"%self.bld_counter] = k
                    self.bld_counter += 1                    
                elif isinstance(v, list): 
                    for w in v:
                        res.append("(?P<BLD_%s>%s+)" % (self.bld_counter,w))            
                        self.brandLookupDict["BLD_%s"%self.bld_counter] = k
                        self.bld_counter += 1       
        return res
    
    
    @classmethod
    def getProductNormalizationDict(cls):
        res = {}
        for p in cls.products:
            if isinstance(p, basestring):
                res[p.lower()] = p
            elif isinstance(p, dict):
                for k,v in p.items():
                    res[k.lower()] = k
                    if isinstance(v, basestring):
                        res[v] = k
                    elif isinstance(v, list):
                        for vv in v:
                            res[vv] = k
        return res

    @classmethod
    def getBrandNormalizationDict(cls):
        res = {}
        for p in cls.brands:
            if isinstance(p, basestring):
                res[p.lower()] = p
            elif isinstance(p, dict):
                for k,v in p.items():
                    res[k.lower()] = k
                    if isinstance(v, basestring):
                        res[v] = k
                    elif isinstance(v, list):
                        for vv in v:
                            res[vv] = k
        return res

    @classmethod
    def normalizeBrand(cls, b):
        if not b: return ""
        return cls.getBrandNormalizationDict().get(b.lower(), "")

    @classmethod    
    def normalizeProduct(cls, p):
        if not p: return ""
        return cls.getProductNormalizationDict().get(p.lower(), "")

    
    def getPatterns(self):
        regexps = ["(" + r % {"BRANDS": '|'.join(self.getBrandLookupWords()), "PRODUCTS": '|'.join(self.getProductLookupWords())} + ")" for r in self.brand_regexps]
        pattern = "(" + '|'.join(regexps) + ")"
        #print pattern
        patterns = [re.compile(pattern, re.I|re.U)]
        return patterns

    
    def calculateConfidence(self, pm, text):
        def processClues(cluelist):
            res = 0
            wdict = {}
            for clue in cluelist:
                if isinstance(clue, tuple):
                    for w in clue[1:]:
                        wdict[w] = clue[0]
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
        
        confidence = 0
        if pm.brand: confidence += 5
        if pm.product: 
            confidence += 5
            if pm.product in self.product_confidence_clues: confidence += processClues(self.product_confidence_clues[pm.product])
        confidence += processClues(self.brand_confidence_clues)
        return confidence
    
    def extract_old(self, text):
        res = []   
        for pattern in self.getPatterns():
            matches = pattern.finditer(text)
            for m in matches:
                pm = ProductMatch()
                #print self.getBrandNormalizationDict()
                #print 1,m.group("brand1"), m.group("product1")
                #print 2,m.group("brand2"), m.group("product2")
                for k in m.groupdict():
                    if k.startswith("BLD_") and m.group(k): 
                        pm.brand = self.brandLookupDict[k]
                        pm.brand_matched_word = m.group(k)
                        pm.brand_matched_pos = (m.start(k), m.end(k))
                        pm.source = text
                    elif k.startswith("PLD_") and m.group(k): 
                        #print k, m.group(k)
                        pm.product = self.getProductLookupDict[k]
                        pm.product_matched_word = m.group(k)
                        pm.product_matched_pos = (m.start(k), m.end(k))
                        pm.source = text
                pm.confidence = self.calculateConfidence(pm, text)
                res.append(pm)
        return res

    def extract(self, text):
        res = []   
        for pattern, rule in self.brand_regexps:
            matches = pattern.finditer(text)
            for m in matches:
                pm = ProductMatch()
                #print self.getBrandNormalizationDict()
                #print 1,m.group("brand1"), m.group("product1")
                #print 2,m.group("brand2"), m.group("product2")
                pm.pattern = pattern.pattern
                for k in m.groupdict():
                    if k.startswith("BLD_") and m.group(k): 
                        pm.brand = self.name.keys()[0]
                        pm.brand_matched_word = m.group(k)
                        pm.brand_matched_pos = (m.start(k), m.end(k))
                        pm.source = text
                    elif k.startswith("PLD_") and m.group(k): 
                        pm.product = self.product_list[int(k.split("_")[1])]
                        pm.product_matched_word = m.group(k)
                        pm.product_matched_pos = (m.start(k), m.end(k))
                        pm.source = text                        
                pm.confidence = self.calculateConfidence(pm, text)
                pm.rule = rule
                res.append(pm)
        for prod_name in self.products.keys():
            for pattern,rule in self.product_regexps[prod_name]:
                matches = pattern.finditer(text)
                #print pattern.pattern, text
                for m in matches:
                    #print "MATCHSS"
                    pm = ProductMatch()
                    pm.pattern = pattern.pattern
                    for k in m.groupdict():
                        if k.startswith("BLD_") and m.group(k): 
                            pm.brand = self.name.keys()[0]
                            pm.brand_matched_word = m.group(k)
                            pm.brand_matched_pos = (m.start(k), m.end(k))
                            pm.source = text
                        elif k.startswith("PLD_") and m.group(k): 
                            pm.product = self.product_list[int(k.split("_")[1])]
                            pm.product_matched_word = m.group(k)
                            pm.product_matched_pos = (m.start(k), m.end(k))
                            pm.source = text
                    pm.confidence = self.calculateConfidence(pm, text)
                    pm.rule = rule
                    res.append(pm)
                
        return res

class AdesClassifier(BrandClassifier):

    def __init__(self):
        BrandClassifier.__init__(self)
        self.brand_regexps = [u'(?:\\A|\\Z|\\W)(?P<brand1>%(BRANDS)s)(\\A|\\Z|\\W+)(?:(?:(?:en|de|(?:con )?(?:sabor|gusto)(?: a)?)\\W+)?(?P<product1>%(PRODUCTS)s)(?:\\A|\\Z|\\W))?']
        self.name = {"Ades": []}
        self.products = ["Manzana", "Durazno", "Naranja", {u"Ananá": ["anana", u"piña"]}, "Natural", {"Frutas Tropicales": "frutos tropicales"}, "Kids", "Free", "multifruta"]
        self.confidence_increasing_clues = ["juguito", "juguitos", "jugo", "jugos", "tomas", u"tomás", u"tomá", "toma", "tomando", "tomar", "tome", u"tomé", "tomen", "beber", "vaso", "jarra"]


class KnorrClassifier(BrandClassifier):
    def __init__(self):
        BrandClassifier.__init__(self)

        self.brand_regexps = [u'(?:\\A|\\Z|\\W)(?P<brand1>%(BRANDS)s)(\\A|\\Z|\\W+)(?:(?:(?:en)\\W+)?(?P<product1>%(PRODUCTS)s)(?:\\A|\\Z|\\W))?', \
               u'(?:(?:\\A|\\Z|\\W)(?P<product2>%(PRODUCTS)s)(\\W+?:de)?)?(?:\\A|\\Z|\\W+)(?P<brand2>%(BRANDS)s)(?:\\A|\\Z|\\W)']
        self.name = {"Knorr": [u"knorr®", "knorr suiza"]}
        self.products = ["Salsa", "Arroz", {"Tomate Cubos": ["tomate en cubos"]}, "Tomate", {"Sopa": ["sopas", "sopita", "sopitas"]}, {"Caldo": ["caldos", "caldito", "calditos", "cubito", "cubos", "cubitos"]}]
        self.product_confidence_incr_clues = {}
        self.product_confidence_incr_clues['Caldo'] = ["carne", "gallina", "verdura"]    
    
class AXEClassifier(BrandClassifier):

    def __init__(self):
        BrandClassifier.__init__(self)

        self.brand_regexps = [u'(?:\\A|\\Z|\\W)(?P<brand>%(BRANDS)s)(?:\\A|\\Z|\\W+)((?:de\\W+)?(?P<product>%(PRODUCTS)s)(?:\\A|\\Z|\\W))?']

        self.name = {"AXE": []}
        self.products = ["Marine", {u"Dark Temptation": ["chocolate"]}]
    
        self.brand_confidence_clues = [(5, "rociar", "rociarse", "rociado", "rociandose", u"rociándose", "rociados", u"loción", "locion", "desodorante", "desodorantes", "olor", "huele", "sobaco", "baranda", "perfume", "fragancia", "aroma", "feromonas")]
        self.brand_confidence_clues.extend([(-100, "@iberia", "golden axe", "axe bahia", u"axe bahía"), (-5,"danza", "danzar"), (-7, "cancion", u"canción", "canciones", "baile","bailando", "bailaba", "bailabas", "bailar", "bailen", "musica", u"música")])


class JumexClassifier(BrandClassifier):
    
    def __init__(self):
        BrandClassifier.__init__(self)
        self.brand_confidence_clues = [(-100, "museo"), (-10, u"colección", "coleccion")]
    
    def extract(self, text):
        res = []
        res.extend(BrandClassifier.extract(JumexAmiClassifier(), text))
        res.extend(BrandClassifier.extract(JumexPauPauClassifier(), text))
        res.extend(BrandClassifier.extract(JumexBidaClassifier(), text))
        res.extend(BrandClassifier.extract(JumexVigorClassifier(), text))
        return res

    def extract_old(self, text):
        res = []
        res.extend(BrandClassifier.extract_old(JumexAmiClassifier(), text))
        res.extend(BrandClassifier.extract_old(JumexPauPauClassifier(), text))
        res.extend(BrandClassifier.extract_old(JumexBidaClassifier(), text))
        res.extend(BrandClassifier.extract_old(JumexVigorClassifier(), text))
        return res                   

class JumexAmiClassifier(JumexClassifier):

    def __init__(self):
        JumexClassifier.__init__(self)

        self.brand_regexps = [u'(?:\\A|\\Z|\\W)(?P<brand1>%(BRANDS)s)(\\A|\\Z|\\W+)(?:(?:(?:en|de|(?:con )?(?:sabor|gusto)(?: a)?)\\W+)?(?P<product1>%(PRODUCTS)s)(?:\\A|\\Z|\\W))?']

        self.name = {u"Jumex Amí": [u"Jumex Amí", "jumex", "ami", u"amí"]}
        self.products = [{u"Citrus punch":["citrus", "punch"]} , "Manzana", {"Naranjada": ["naranja"]}, "Mango", "Uva", {u"Piña": ["anana", u"ananá"]}]
    
        self.brand_confidence_clues = JUGO_CONFIDENCE_CLUES

class JumexPauPauClassifier(JumexClassifier):

    def __init__(self):
        JumexClassifier.__init__(self)

        self.brand_regexps = [u'(?:\\A|\\Z|\\W)(?P<brand1>%(BRANDS)s)(\\A|\\Z|\\W+)(?:(?:(?:en|de|(?:con )?(?:sabor|gusto)(?: a)?)\\W+)?(?P<product1>%(PRODUCTS)s)(?:\\A|\\Z|\\W))?']

        self.name = {"Jumex Pau Pau!": [u"Jumex Pau Pau", "jumex", "pau", "pau!"]}
        self.products = ["Cereza", "Guayaba", "Mango", {u"Limón": "limon"}, "Manzana", "Naranja", "Tamarindo", "Uva"]
    
        self.brand_confidence_clues = JUGO_CONFIDENCE_CLUES

class JumexBidaClassifier(JumexClassifier):

    def __init__(self):
        JumexClassifier.__init__(self)

        self.brand_regexps = [u'(?:\\A|\\Z|\\W)(?P<brand1>%(BRANDS)s)(\\A|\\Z|\\W+)(?:(?:(?:en|de|(?:con )?(?:sabor|gusto)(?: a)?)\\W+)?(?P<product1>%(PRODUCTS)s)(?:\\A|\\Z|\\W))?']

        self.name = {"Jumex Bida": ["jumex", "bida"]}
        self.products = ["Tamarindo", "Uva", "Fresa", "Guayaba", "Mango", "Manzana", "Naranja", {u"Piña": ["anana", u"ananá"]}]
    
        self.brand_confidence_clues = JUGO_CONFIDENCE_CLUES

class JumexVigorClassifier(JumexClassifier):

    def __init__(self):
        JumexClassifier.__init__(self)
        self.brand_regexps = [u'(?:\\A|\\Z|\\W)(?P<brand1>%(BRANDS)s)(\\A|\\Z|\\W+)(?:(?:(?:en|de|(?:con )?(?:sabor|gusto)(?: a)?)\\W+)?(?P<product1>%(PRODUCTS)s)(?:\\A|\\Z|\\W))?']

        self.name = {"Jumex Vigor Pet": ["Jumex Vigor","jumex", "vigor", "pet"]}
        self.products = [{u"Citrus punch":["citrus", "punch"]} , {u"Fruit punch":["fruit", "punch"]}, "Manzana", "Uva"]
    
        self.brand_confidence_clues = JUGO_CONFIDENCE_CLUES


class DelValleClassifier(BrandClassifier):

    def __init__(self):
        BrandClassifier.__init__(self)
        self.brand_regexps = [u'(?:\\A|\\Z|\\W)(?P<brand1>%(BRANDS)s)(\\A|\\Z|\\W+)(?:(?:(?:en|de|(?:con )?(?:sabor|gusto)(?: a)?)\\W+)?(?P<product1>%(PRODUCTS)s)(?:\\A|\\Z|\\W))?']

        self.name = {"Del Valle": []}
        self.products = [u"Durazno", "Manzana", {u"Açaí": [u"açai"]}, {u"Arándano": ["arandano"]}, "Granada"]
    
        self.brand_confidence_clues = JUGO_CONFIDENCE_CLUES + [(5, "nectar", u"néctar")]
    
class IberiaClassifier(BrandClassifier):

    def __init__(self):
        BrandClassifier.__init__(self)
        self.brand_regexps = [u'(?:\\A|\\Z|\\W)(?P<brand>%(BRANDS)s)(?:\\A|\\Z|\\W)?']

        self.name = "Iberia"
        self.products = ["90g", "225g", "500g", "1kg"]
    
        self.brand_confidence_clues = [(5,u"margarina", "untar", "freir", "hornear", "guisar", "cocinar")]
        self.brand_confidence_clues.extend(FUTBOL_CONFIDENCE_CLUES + AVION_CONFIDENCE_CLUES)  ##HAY QUE HACERLO NEGATIVO

class VeetClassifier(BrandClassifier):

    def __init__(self):
        BrandClassifier.__init__(self)
    
        self.brand_regexps = [u'(?:\\A|\\Z|\\W)(?P<brand1>%(BRANDS)s)(\\A|\\Z|\\W+)(?:(?:(?:en)\\W+)?(?P<product1>%(PRODUCTS)s)(?:\\A|\\Z|\\W))?', \
               u'(?:(?:\\A|\\Z|\\W)(?P<product2>%(PRODUCTS)s)(\\W+?:de)?)?(?:\\A|\\Z|\\W+)(?P<brand2>%(BRANDS)s)(?:\\A|\\Z|\\W)']

        self.name = "Veet"
        self.products = [{"Crema": "cremas"}, {"Cera": "ceras"}, {"Banda": "bandas"}]
    
        self.brand_confidence_clues = [(-5, u"depilar", "depilatoria", "depilatorias", "facial", "piel", "navaja", "sensible", "ducha", "rasera")]

class AmericaClassifier(BrandClassifier):

    def __init__(self):
        BrandClassifier.__init__(self)

        self.brand_regexps = [u'(?:\\A|\\Z|\\W)(?P<brand>%(BRANDS)s)(?:\\A|\\Z|\\W)?']

        self.name = "America"
        self.products = []
    
        self.confidence_increasing_clues = FUTBOL_CONFIDENCE_CLUES


def highlightText(text, pm, d):
    res = text
    dd = d
    if min({-1: 99999}.get(pm.brand_matched_pos[0],pm.brand_matched_pos[0]), {-1: 99999}.get(pm.product_matched_pos[0],pm.product_matched_pos[0])) == pm.brand_matched_pos[0]:
        bl = len(res)
        res = res[:pm.brand_matched_pos[0]+dd] + "<B>" + pm.brand_matched_word + "</B>" + res[dd+pm.brand_matched_pos[1]:]
        dd = dd + len(res) - bl
        if pm.product:
            bl = len(res)
            res = res[:pm.product_matched_pos[0]+dd] + "<B>" + pm.product_matched_word + "</B>" + res[dd+pm.product_matched_pos[1]:]
            dd = dd + len(res) - bl            
    else:
        bl = len(res)
        res = res[:pm.product_matched_pos[0]+dd] + "<B>" + pm.product_matched_word + "</B>" + res[dd+pm.product_matched_pos[1]:]
        dd = dd + len(res) - bl
        if pm.brand:
            bl = len(res)
            res = res[:pm.brand_matched_pos[0]+dd] + "<B>" + pm.brand_matched_word + "</B>" + res[dd+pm.brand_matched_pos[1]:]
            dd = dd + len(res) - bl            
    return res

    
if __name__ == '__main__':
    text = u'Erevank Fundacion/Coleccion Jumex ami de citrus  - Destello El mural Sin título (2011) refleja el interés del artista... http://t.co/1I7GKmiRw7'
    pms = JumexClassifier().extract_old(text)
    for pm in pms:
        print pm.getDetail()
        print pm.confidence
        print
        
    """
    regexp2 = u"(\\b|\\W|\\A)(?P<A>@Iberia)(\\b|\\W)"
    print regexp2
    for mo in re.compile(regexp2, re.I| re.U | re.L).finditer(u"ahora estoy en @Iberia"):
        print mo.group("A")
        print "found!"
    """
    exit(0)
    usedb = True
    if not usedb:
        texts = ["re piola escabiar ades de manzana para matar las penas",\
            "Amo tomar Ades",\
            "no hay mejor combinacion que ades y chocolinas",\
            'le dije a mi hermana que me sirva un vaso de ades y me dijo "no tenes empleada levántate nena" jojo que rataaaaa',\
            "Ades me dijo que soy lo mas. :')",
            "pelades del sol",
            "ades! carajo!",
            "que mierda que es ades por dios!",\
            "como me gusta el ades de naranja che!",\
            u"las 2:04.. si ahora me dices Ven y añades Nena... voy", \
            u"como le voy a entrar a ese ades con sabor a manzana",\
            u"Genial el Ades gusto a frutos tropicales !",\
            u"Un pollito lleva un cubito Knorr Suiza debajo de su alita y un pato le pregunta:",\
            u"sopita knorr light de cena...divino todo!",\
            u"un caldito knorr de cena y una knorr sopita de almuerzo"]
    else:
        db = pymongo.MongoClient()['unilever']
        tweets = db.tweets.find({}).limit(500)
        texts = [t['text'] for t in tweets]
    ades = AdesClassifier()
    knorr = KnorrClassifier()
    for t in texts:
        matches = None
        matches = ades.extract_old(t)
        if matches:
            for m in matches:
                print t
                print m.getDetail()
                print
        matches = knorr.extract_old(t)
        if matches:
            for m in matches:
                print t
                print m.getDetail()
                print
        elif t.lower().find("knorr") >= 0:
                print "NOT FOUND:", t