"""Clasificador de decretos por subtema (bayes ingenuo sobre el visto), entrenado con el registro existente."""
import math, re, unicodedata, collections

STOP = set('de la el los las del y a en que por con para se su al lo un una es o como sus este esta dicho dicha mismo misma'.split())


def tokens(s):
    s = unicodedata.normalize('NFD', (s or '').lower())
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    w = [t for t in re.findall(r'[a-zñ]{3,}', s) if t not in STOP]
    return w + [a + '_' + b for a, b in zip(w, w[1:])]


class NB:
    def __init__(self, docs, labels, alpha=0.3):
        self.cnt = collections.Counter(labels)
        self.tok = collections.defaultdict(collections.Counter)
        for d, l in zip(docs, labels):
            self.tok[l].update(set(tokens(d)))
        self.V = len({t for c in self.tok.values() for t in c})
        self.tot = {l: sum(c.values()) for l, c in self.tok.items()}
        self.N = len(labels); self.a = alpha

    def predecir(self, doc):
        ts = set(tokens(doc)); best, bs = None, -1e18
        for l, n in self.cnt.items():
            c = self.tok[l]; den = math.log(self.tot[l] + self.a * self.V)
            sc = math.log(n / self.N) + sum(math.log(c.get(t, 0) + self.a) - den for t in ts)
            if sc > bs: best, bs = l, sc
        return best


def entrenar(R):
    """R: filas del registro [n,y,f,tema,sub,tag,visto,...]; devuelve modelo de subtema."""
    return NB([r[6] for r in R], [r[4] for r in R])
