# Axiom AI — matematik yadro (brauzerda Pyodide ichida ishlaydi). axiom.py dan avtomatik ajratib olingan.
import re, ast, random, datetime, math, json
import difflib
from fractions import Fraction
from decimal import Decimal, getcontext
import sympy as sp
from sympy.parsing.sympy_parser import (parse_expr, standard_transformations, implicit_multiplication_application)
getcontext().prec = 50

VERSIYA = "1.0"
YARATUVCHI = "Sarvar Karimov"
SW, SH = 460, 270
TR = standard_transformations + (implicit_multiplication_application,)
def oqi(s):
    return parse_expr(s.strip().replace("^", "**"), transformations=TR)

fullscreen = False
grad_id = None
grad_rasm = None
grad_olcham = (0, 0)
pufaklar = []
wrap_hozirgi = 600
CHET = 18
ORALIQ = 10
shrift_olchami = 12
_olcham_taymer = None
tanlangan_matn = [""]
_USTKI_MAP = str.maketrans("0123456789-", "\u2070\u00b9\u00b2\u00b3\u2074\u2075\u2076\u2077\u2078\u2079\u207b")
def chiroyli(matn, toliq=False):
    t = matn.replace("**", "^")
    if toliq:
        t = re.sub(r"\bsqrt\(([A-Za-z0-9.]+)\)", "\u221a\\1", t)
        t = t.replace("sqrt(", "\u221a(")
        t = re.sub(r"\bexp\(([A-Za-z0-9.]+)\)", r"e^\1", t)
        t = t.replace("exp(", "e^(")
        t = re.sub(r"\bAbs\(([^()]*)\)", r"|\1|", t)
        for a, b in (("asin", "arcsin"), ("acos", "arccos"), ("atan", "arctan"), ("acot", "arccot")):
            t = re.sub(r"\b" + a + r"\(", b + "(", t)
        t = re.sub(r"\blog\(", "ln(", t)
        t = re.sub(r"\bpi\b", "\u03c0", t)
        t = re.sub(r"\boo\b", "\u221e", t)
        t = re.sub(r"(?<![\w.])I(?!\w)", "i", t)
        t = re.sub(r"(?<![\w.^])(\d+(?:\.\d+)?)\*(?=[A-Za-z(\u221a\u03c0])", r"\1", t)
        t = re.sub(r"\^(-?\d+)(?![\d.(])", lambda mm: mm.group(1).translate(_USTKI_MAP), t)
    return t.replace("*", "\u00b7")

def grafik_ajrat(matn):
    """'grafik x^2; sin(x) -5 dan 5 gacha' -> ([ifodalar], a, b). Grafik so'rovi bo'lmasa None."""
    kichik = matn.lower().strip()
    if not re.search(r"\b(grafik|chiz|plot)", kichik):
        return None
    a, b = -10.0, 10.0
    m = re.search(r"(-?\d+(?:[.,]\d+)?)\s*(?:dan|\.\.\.?)\s*(-?\d+(?:[.,]\d+)?)\s*(?:gacha|gach)?", kichik)
    if m:
        try:
            a = float(m.group(1).replace(",", "."))
            b = float(m.group(2).replace(",", "."))
        except ValueError:
            a, b = -10.0, 10.0
        kichik = kichik.replace(m.group(0), " ")
        if a > b:
            a, b = b, a
        if a == b:
            a, b = -10.0, 10.0
    qolgan = re.sub(r"\b(grafigini|grafigi|grafik|chizib|chiz|plot|ber|ning|uchun|funksiyaning|funksiya)\b", " ", kichik)
    ifodalar = []
    for q in re.split(r";|\bva\b", qolgan):
        q = q.strip(" :,")
        q = re.sub(r"^(y|f\s*\(\s*x\s*\))\s*=\s*", "", q).strip()
        if q:
            ifodalar.append(q)
    return ifodalar[:4], a, b

def grafik_kes(x1, y1, x2, y2, past, yuqori):
    """Kesmaning faqat [past, yuqori] oralig'idagi qismini qaytaradi."""
    if (y1 < past and y2 < past) or (y1 > yuqori and y2 > yuqori):
        return None
    dy = y2 - y1
    t0, t1 = 0.0, 1.0
    if dy != 0:
        ta = (past - y1) / dy
        tb = (yuqori - y1) / dy
        if ta > tb:
            ta, tb = tb, ta
        t0 = max(t0, ta)
        t1 = min(t1, tb)
        if t0 > t1:
            return None
    return (x1 + (x2 - x1) * t0, y1 + dy * t0, x1 + (x2 - x1) * t1, y1 + dy * t1, t0, t1)

def grafik_malumot(matnlar, a, b):
    """Nuqtalarni hisoblaydi. Xato bo'lsa ValueError ko'taradi."""
    x = sp.Symbol("x")
    funksiyalar = []
    for m in matnlar:
        ifoda = oqi(m).subs(sp.Symbol("e"), sp.E)
        if ifoda.free_symbols - {x}:
            raise ValueError("faqat x ishlatiladi")
        funksiyalar.append(sp.lambdify(x, ifoda, modules=["math"]))
    N = 500
    egri = []
    hammasi = []
    for f in funksiyalar:
        nuqtalar = []
        for i in range(N + 1):
            xv = a + (b - a) * i / N
            try:
                yv = float(f(xv))
                if yv != yv or yv in (float("inf"), float("-inf")):
                    yv = None
            except Exception:
                yv = None
            nuqtalar.append((xv, yv))
            if yv is not None:
                hammasi.append(yv)
        egri.append(nuqtalar)
    if len(hammasi) < 2:
        raise ValueError("qiymat topilmadi")
    hammasi.sort()
    n = len(hammasi)
    kam, kop = hammasi[int(0.02 * (n - 1))], hammasi[int(0.98 * (n - 1))]
    if hammasi[-1] - hammasi[0] <= 4 * (kop - kam) + 1e-9:
        past, yuqori = hammasi[0], hammasi[-1]
    else:
        past, yuqori = kam, kop          # asimptotali funksiyalar (1/x, tan(x)...)
    if yuqori - past < 1e-9:
        past, yuqori = past - 1, yuqori + 1
    chet = (yuqori - past) * 0.06
    return egri, past - chet, yuqori + chet

def grafik_belgilar(past, yuqori):
    """Chiroyli o'q belgilari: 1, 2, 5 qadamlar."""
    xom = (yuqori - past) / 6.0
    if xom <= 0:
        return [past]
    daraja = 10 ** math.floor(math.log10(xom))
    qadam = daraja
    for k in (1, 2, 5, 10):
        if xom <= k * daraja:
            qadam = k * daraja
            break
    t = math.ceil(past / qadam) * qadam
    natija = []
    while t <= yuqori + qadam * 1e-9:
        natija.append(round(t, 10))
        t += qadam
    return natija

def grafik_son(v):
    s = f"{v:.4g}"
    return "0" if s in ("-0", "0") else s

amallar_ochiqmi = False
tarix_ochiqmi = False
tarix_malumot = []
QOLLANMA = [
    ("Qanday ishlatiladi\n", "b"),
    ("Savolni pastdagi maydonga yozing va Enter bosing. Tayyor namunalarni \"Amallar\" tugmasidan olishingiz mumkin.\n\n", "n"),
    ("Tenglama\n", "b"), ("x^2-5x+6=0\n\n", "k"),
    ("Hosila\n", "b"), ("hosila x^3+2x\n\n", "k"),
    ("Integral\n", "b"), ("integral 2x\n\n", "k"),
    ("Limit\n", "b"), ("limit x->0 sin(x)/x\n\n", "k"),
    ("Matritsa (determinant va teskari matritsa)\n", "b"),
    ("det [[1,2],[3,4]]\nteskari matritsa [[1,2],[3,4]]\n\n", "k"),
    ("Tenglamalar tizimi\n", "b"), ("tizim: x+y=5, x-y=1\n\n", "k"),
    ("Grafik chizish\n", "b"),
    ("grafik x^2\ngrafik sin(x); cos(x)\ngrafik x^2 -5 dan 5 gacha\n\n", "k"),
    ("Yechim bosqichlari\n", "b"),
    ("bosqich x^2-5x+6=0\nbosqich hosila x^3+2x\nbosqich integral 3x^2+2x\nbosqich limit x->1 (x^2-1)/(x-1)\nbosqich tizim: x+y=5, x-y=1\nbosqich det [[1,2],[3,4]]\nbosqich teskari matritsa [[1,2],[3,4]]\n\n", "k"),
    ("Ko'paytuvchilarga ajratish va qavs ochish\n", "b"),
    ("ajrat x^2-5x+6\nko'paytuvchilarga ajrat x^3-8\najrat 360\noch (x+2)^3\noch (x+1)(x-3)\n\n", "k"),
    ("EKUB va EKUK\n", "b"),
    ("ekub 12 18\nekuk 12 18 30\nekub va ekuk 48 36\n\n", "k"),
    ("Kasrlar\n", "b"),
    ("1/2 + 3/4\n2 1/3 - 1/2\n2/3 : 4/5\nqisqartir 12/18\naralash 7/3\n2 1/3\n3/4 o'nli\n0.75 kasr\n\n", "k"),
    ("Foizlar\n", "b"),
    ("200 ning 15%\n50 soni 200 ning necha foizi\n200 ni 20% ga oshir\n200 ni 20% ga kamaytir\n15% i 30 bo'lgan son\n\n", "k"),
    ("Birliklar konvertori\n", "b"),
    ("5 km necha metr\n3 soat necha daqiqa\n100 f necha c\n1 gb necha mb\n36 km/soat necha m/s\n\n", "k"),
    ("Geometriya formulalari\n", "b"),
    ("doira yuzi r=5\nsilindr hajmi r=3 h=10\nuchburchak a=3 b=4 c=5\ngipotenuza a=3 b=4\nkub hajmi a=4\n\n", "k"),
    ("Sanoq sistemalari\n", "b"),
    ("25 ikkilik\n1011 ikkilikdan o'nlikka\n255 o'n oltilik\nff o'n oltilikdan o'nlikka\n\n", "k"),
    ("Fikrni to'g'rilash\n", "b"),
    ("Kalit so'zlardagi arzimas xatolar (hosla, integal, grafk...) o'zi to'g'rilanadi. "
     "Misol tushunilmasa, dastur \"buni nazarda tutdingizmi\" deb taklif qiladi.\n\n", "n"),
    ("Soddalashtirish\n", "b"), ("soddalashtir (x^2-1)/(x-1)\n\n", "k"),
    ("Oddiy hisob-kitob\n", "b"),
    ("6:3     8\\2     864 \u00f7 12     10 ni 2 ga bo'l     sin(pi/6)     sqrt(144)\n\n", "k"),
    ("Yozish qoidalari\n", "b"),
    ("Daraja uchun ^ belgisi ishlatiladi (x^2). Ko'paytirish: 2x yoki 2*x. Kasr: (x+1)/(x-1).\n\n", "n"),
    ("Klaviatura\n", "b"),
    ("\u2191 / \u2193 \u2014 oldingi savollar\nF11 \u2014 to'liq ekran\nESC \u2014 to'liq ekrandan chiqish\n\n", "n"),
    ("Tugmalar\n", "b"),
    ("Amallar \u2014 tayyor namunalar\nTarix \u2014 yechilgan misollar ro'yxati\nA- / A+ \u2014 yozuv kattaligini o'zgartirish\n\u2600 / \u263e \u2014 yorug' va qorong'u mavzu\n"
     "Tozalash \u2014 chatni tozalash\n\n", "n"),
    ("Xabarni nusxalash\n", "b"),
    ("Xabar ustida sichqonchaning o'ng tugmasini bosing va \"Nusxalash\" ni tanlang.\n", "n"),
]
IMKONIYATLAR = [
    ("Axiom nimalarni qila oladi\n", "b"),
    ("\u2022 Tenglamalarni yechish\n\u2022 Hosila va integral (aniqmas) hisoblash\n\u2022 Limit hisoblash\n"
     "\u2022 Determinant va teskari matritsa\n\u2022 Ikki noma'lumli tenglamalar tizimi\n\u2022 Funksiya grafigini chizish (bir nechtasini birga ham)\n"
     "\u2022 sin, cos, tan, log, sqrt bilan hisob-kitob\n\u2022 Ifodalarni soddalashtirish\n"
     "\u2022 Yechim bosqichlarini ko'rsatish (tenglama, hosila, integral, limit, tizim, matritsa)\n"
     "\u2022 Ko'paytuvchilarga ajratish va qavs ochish\n\u2022 EKUB va EKUK (tub ko'paytuvchilarga ajratib)\n"
     "\u2022 Kasrlar, foizlar va birliklar konvertori\n"
     "\u2022 Geometriya formulalari (yuza, perimetr, hajm, Pifagor)\n"
     "\u2022 Sanoq sistemalari (ikkilik, sakkizlik, o'n oltilik)\n"
     "\u2022 Kiritishdagi arzimas xatolarni o'zi to'g'rilash\n"
     "\u2022 Yorug' va qorong'u mavzu\n"
     "\u2022 Oddiy suhbat: salomlashish, ismi, yaratuvchisi haqidagi savollar, qisqa javoblar (ha, yo'q, mayli)\n\n", "n"),
    ("Hozircha nimalarni qila olmaydi\n", "b"),
    ("\u2022 So'z bilan yozilgan masalalarni (matnli masalalarni) tushunish\n"
     "\u2022 Matematikadan tashqari erkin mavzularda suhbatlashish\n\n", "n"),
    ("Qanday ishlaydi\n", "b"),
    ("Axiom internetga ulanmasdan, kompyuterning o'zida ishlaydi. U SymPy matematik kutubxonasi va "
     "oldindan yozilgan qoidalar asosida ishlaydigan matematik yordamchi dastur.\n", "n"),
]
DASTUR_HAQIDA = [
    ("Axiom AI\n", "b"),
    ("Oflayn matematik yordamchi\n\n", "n"),
    ("Versiya: ", "b"), (f"{VERSIYA}\n", "n"),
    ("Yaratuvchi: ", "b"), (f"{YARATUVCHI}\n", "n"),
    ("Texnologiyalar: ", "b"), ("Python, Tkinter, SymPy\n", "n"),
    ("Ishlash rejimi: ", "b"), ("oflayn (internet shart emas)\n", "n"),
]
malumot_oynasi = None
foydalanuvchi_ismi = None
def ism_bilan(matn_variantlari):
    shablon = random.choice(matn_variantlari)
    if foydalanuvchi_ismi:
        return f"{foydalanuvchi_ismi}, " + shablon[0].lower() + shablon[1:]
    return shablon

def matematik_savolmi(matn):
    m = matn.lower()
    raqam_bor = any(c.isdigit() for c in m)
    ozgaruvchi_bor = bool(re.search(r"(?<![a-zA-Z\u02bb'])[xy](?![a-zA-Z\u02bb'])", m))
    kalit_sozlar = ["integral", "hosila", "limit", "soddalashtir", "det", "matritsa", "tizim", "yech", "sin", "cos", "tan", "log", "sqrt"]
    kalit_bor = any(k in m for k in kalit_sozlar)
    amal_belgisi_bor = any(b in m for b in ["+", "-", "*", "/", "^", "=", ":", "\u00f7", "\\"]) or "bo'l" in m or "ko'paytir" in m
    return (raqam_bor or ozgaruvchi_bor or kalit_bor) and (amal_belgisi_bor or kalit_bor or raqam_bor)

def matematikani_yech(matn):
    matn = matn.lower().strip()
    x, y = sp.symbols('x y')
    try:
        if matn.startswith("tizim"):
            qism = matn.replace("tizim", "", 1).strip(" :")
            tenglamalar = []
            for t in re.split(r"[;,]", qism):
                if "=" in t:
                    chap, ong = t.split("=")
                    tenglamalar.append(sp.Eq(oqi(chap), oqi(ong)))
            return "tizim", str(sp.solve(tenglamalar, [x, y], dict=True))

        if "det" in matn or "matritsa" in matn:
            M = sp.Matrix(ast.literal_eval(matn[matn.index("[["):]))
            if "teskari" in matn:
                return "teskari", str(M.inv().tolist())
            return "determinant", str(M.det())

        matn = matn.replace("\u00f7", "/").replace(":", "/").replace("\\", "/")
        m = re.search(r"(\d+)\s*ni\s*(\d+)\s*ga\s*bo'?l", matn)
        if m:
            matn = f"{m.group(1)}/{m.group(2)}"
        m = re.search(r"(\d+)\s*ni\s*(\d+)\s*ga\s*ko'?paytir", matn)
        if m:
            matn = f"{m.group(1)}*{m.group(2)}"

        if "limit" in matn:
            m = re.search(r"(\w+)\s*->\s*(-?[\w\.]+)", matn)
            ifoda = re.sub(r"limit|(\w+)\s*->\s*(-?[\w\.]+)", "", matn).strip()
            nuqta_matn = m.group(2).replace("cheksiz", "oo")
            nuqta = sp.oo if nuqta_matn == "oo" else (-sp.oo if nuqta_matn == "-oo" else oqi(nuqta_matn))
            return "limit", str(sp.limit(oqi(ifoda), sp.Symbol(m.group(1)), nuqta))
        elif "hosila" in matn:
            ifoda = re.sub(r"\b(hosila|ol|dan|ning)\b", "", matn).strip()
            return "hosila", str(sp.diff(oqi(ifoda), x))
        elif "integral" in matn:
            ifoda = re.sub(r"\b(integral|ol|dan|ning)\b", "", matn).strip()
            return "integral", str(sp.integrate(oqi(ifoda), x))
        elif "soddalashtir" in matn:
            ifoda = matn.replace("soddalashtir", "").strip()
            return "soddalashtir", str(sp.simplify(oqi(ifoda)))
        elif "=" in matn:
            chap, ong = matn.split("=")
            L, R = oqi(chap), oqi(ong)
            if not (L.free_symbols or R.free_symbols):
                lv, rv = sp.simplify(L), sp.simplify(R)
                if sp.simplify(lv - rv) == 0:
                    return "tenglik", f"{lv} = {rv}: bu to'g'ri tenglik"
                return "tenglik", f"{lv} \u2260 {rv}: bu noto'g'ri tenglik"
            natija = sp.solve(sp.Eq(L, R), x)
            return "tenglama", str(natija)
        else:
            s = sp.simplify(oqi(matn))
            if not s.free_symbols and not s.is_Integer:
                return "hisob_taqribiy", (str(s), str(sp.N(s, 8)))
            return "hisob", str(s)
    except Exception:
        return "xato", None

_USTKI = "\u2070\u00b9\u00b2\u00b3\u2074\u2075\u2076\u2077\u2078\u2079\u207b"
_ODDIY = "0123456789-"
def kirishni_normallashtir(matn):
    t = matn
    for ch in "\u02bb\u02bc\u2019\u2018`":
        t = t.replace(ch, "'")
    t = re.sub("[" + _USTKI + "]+", lambda m: "^" + m.group().translate(str.maketrans(_USTKI, _ODDIY)), t)
    t = t.replace("\u00b7", "*").replace("\u00d7", "*").replace("\u2212", "-")
    t = t.replace("\u03c0", "pi").replace("\u221e", "oo")
    t = re.sub(r"\u221a\(", "sqrt(", t)
    t = re.sub(r"\u221a(\w+)", r"sqrt(\1)", t)
    t = re.sub(r"\bln\(", "log(", t)
    for a, b in (("arcsin", "asin"), ("arccos", "acos"), ("arctan", "atan")):
        t = re.sub(r"\b" + a + r"\(", b + "(", t)
    if re.fullmatch(r"[\d\s+\-*/().^%,:\u00f7\u00d7]+=\s*\??", t.strip()):
        t = re.sub(r"=\s*\??\s*$", "", t.strip())
    return t

AJRAT_SOZLAR = r"\b(ko'?paytuvchilarga|ko'?paytuvchilar|ko'?paytuvchi|ajratib|ajratish|ajrat|faktorlarga|faktor|factor|ber|ni)\b"
def ajrat_och_javob(m):
    """'ajrat x^2-5x+6' yoki 'och (x+2)^3'. Boshqa so'rov bo'lsa None."""
    och_m = re.match(r"^(qavsni?\s+och(ib)?(\s+ber)?|och(ib)?(\s+ber)?|yoy(ib)?(\s+ber)?|expand)\b[\s:]*", m)
    ajr = re.search(r"\b(ajrat\w*|ko'?paytuvchi\w*|faktor\w*|factor)\b", m)
    if not och_m and not ajr:
        return None
    try:
        if och_m:
            e = m[och_m.end():].strip()
        else:
            e = re.sub(AJRAT_SOZLAR, " ", m).strip(" :,")
        if not e:
            return ("Qaysi ifodani? Masalan: ajrat x^2-5x+6 yoki och (x+2)^3"), "suhbat"
        if "=" in e:
            return "Tenglama emas, ifoda yozing. Masalan: ajrat x^2-5x+6", "xato"
        ifoda = oqi(e)
        if och_m:
            natija = sp.expand(ifoda)
            if natija == ifoda and "(" not in e:
                return f"{e} \u2014 bu ifodada ochiladigan qavs yo'q.", "natija"
            return f"{e} = {natija}", "natija"
        if ifoda.is_Integer and ifoda > 1:
            f = sp.factorint(int(ifoda))
            kop = "\u00b7".join(f"{p}^{k}" if k > 1 else str(p) for p, k in sorted(f.items()))
            return f"{e} = {kop}", "natija"
        f = sp.factor(ifoda)
        if f == ifoda:
            return f"{e} ifodasi butun koeffitsiyentlar bilan ko'paytuvchilarga ajralmaydi.", "natija"
        return f"{e} = {f}\nTekshiruv: qavslarni ochsak, {sp.expand(f)} hosil bo'ladi.", "natija"
    except Exception:
        return "Bu ifodani o'qiy olmadim. Masalan: ajrat x^2-5x+6 yoki och (x+2)^3", "xato"

def _kop_yoz(f):
    return "\u00b7".join(f"{p}^{k}" if k > 1 else str(p) for p, k in sorted(f.items())) or "1"

def ekub_ekuk_javob(m):
    sonlar = [int(s) for s in re.findall(r"\d+", m)]
    if len(sonlar) < 2:
        return "EKUB yoki EKUK uchun kamida ikkita son yozing. Masalan: ekub 12 18", "xato"
    if len(sonlar) > 6 or any(s < 1 or s > 10 ** 12 for s in sonlar):
        return "Bir vaqtda 6 tagacha, 1 dan 10^12 gacha sonlarni yozing.", "xato"
    ekub_kerak = "ekub" in m
    ekuk_kerak = "ekuk" in m
    ayr = [sp.factorint(s) for s in sonlar]
    tub = sorted(set().union(*[set(f) for f in ayr]))
    ro = ", ".join(str(s) for s in sonlar)
    q = [f"{s} = {_kop_yoz(f)}" for s, f in zip(sonlar, ayr)]
    if ekub_kerak:
        umumiy = {p: min(f.get(p, 0) for f in ayr) for p in tub}
        umumiy = {p: k for p, k in umumiy.items() if k > 0}
        qiymat = sonlar[0]
        for s in sonlar[1:]:
            qiymat = math.gcd(qiymat, s)
        if umumiy:
            q.append(f"EKUB: umumiy tub ko'paytuvchilarni eng kichik daraja bilan olamiz: {_kop_yoz(umumiy)} = {qiymat}")
        else:
            q.append("Umumiy tub ko'paytuvchi yo'q (sonlar o'zaro tub).")
        q.append(f"EKUB({ro}) = {qiymat}")
    if ekuk_kerak:
        katta = {p: max(f.get(p, 0) for f in ayr) for p in tub}
        qiymat = sonlar[0]
        for s in sonlar[1:]:
            qiymat = qiymat * s // math.gcd(qiymat, s)
        q.append(f"EKUK: barcha tub ko'paytuvchilarni eng katta daraja bilan olamiz: {_kop_yoz(katta)} = {qiymat}")
        q.append(f"EKUK({ro}) = {qiymat}")
    return "\n".join(q), "natija"

def bosqich_tizim(m):
    x, y = sp.symbols("x y")
    qism = m.replace("tizim", "", 1).strip(" :")
    tn = []
    for t in re.split(r"[;,]", qism):
        if "=" in t:
            chap, ong = t.split("=")
            tn.append((oqi(chap), oqi(ong)))
    if len(tn) != 2:
        raise ValueError("ikki tenglama kerak")
    (L1, R1), (L2, R2) = tn
    q = ["Tizim:", f"  (1) {L1} = {R1}", f"  (2) {L2} = {R2}"]
    e1 = sp.expand(L1 - R1)
    for v1, v2 in ((x, y), (y, x)):
        if e1.has(v1) and sp.Poly(e1, v1).degree() == 1:
            break
    else:
        raise ValueError("almashtirish uchun noma'lum topilmadi")
    ifoda1 = sp.solve(sp.Eq(L1, R1), v1)[0]
    q.append(f"1) (1)-tenglamadan {v1} ni ifodalaymiz: {v1} = {ifoda1}")
    q.append(f"2) Buni (2)-tenglamaga qo'yamiz: {L2.subs(v1, ifoda1)} = {R2.subs(v1, ifoda1)}")
    sub2 = sp.expand((L2 - R2).subs(v1, ifoda1))
    q.append(f"3) Soddalashtiramiz: {sub2} = 0")
    if not sub2.has(v2):
        if sub2 == 0:
            q.append("4) Bu har doim to'g'ri, demak tizimda cheksiz ko'p yechim bor.")
        else:
            q.append("4) Bu ziddiyat, demak tizimning yechimi yo'q.")
        return q
    qiym2 = sp.solve(sub2, v2)
    if len(qiym2) != 1:
        q.append(f"4) Hosil bo'lgan tenglamani yechamiz: {v2} = {qiym2}")
        q.append(f"Javob: {sp.solve([sp.Eq(L1, R1), sp.Eq(L2, R2)], [x, y], dict=True)}")
        return q
    qiym2 = qiym2[0]
    qiym1 = sp.simplify(ifoda1.subs(v2, qiym2))
    q.append(f"4) {v2} ni topamiz: {v2} = {qiym2}")
    q.append(f"5) {v1} ni topamiz: {v1} = {ifoda1} = {str(ifoda1).replace(str(v2), '(' + str(qiym2) + ')')} = {qiym1}")
    ans = {v1: qiym1, v2: qiym2}
    q.append(f"Javob: x = {ans[x]}, y = {ans[y]}")
    return q

def bosqich_limit(m):
    mm = re.search(r"(\w+)\s*->\s*(-?[\w\.]+)", m)
    ifoda = re.sub(r"limit|(\w+)\s*->\s*(-?[\w\.]+)", "", m).strip()
    nm = mm.group(2).replace("cheksiz", "oo")
    nuqta = sp.oo if nm == "oo" else (-sp.oo if nm == "-oo" else oqi(nm))
    var = sp.Symbol(mm.group(1))
    f = oqi(ifoda)
    javob = sp.limit(f, var, nuqta)
    q = [f"Limit: {var} \u2192 {nuqta} da {f}"]
    if nuqta in (sp.oo, -sp.oo):
        q.append(f"1) {var} cheksizlikka intilganda eng yuqori darajali hadlar hal qiluvchi bo'ladi. Ifodani shu nuqtai nazardan tahlil qilamiz.")
        q.append(f"Natija: {javob}")
        return q
    qiymat = f.subs(var, nuqta)
    if qiymat.is_finite is True:
        q.append(f"1) To'g'ridan-to'g'ri {var} = {nuqta} ni qo'yamiz: {qiymat}")
        q.append("2) Aniqmaslik chiqmadi, shuning uchun shu qiymat limit bo'ladi.")
        q.append(f"Natija: {javob}")
        return q
    n, d = sp.fraction(sp.together(f))
    nv, dv = n.subs(var, nuqta), d.subs(var, nuqta)
    if nv == 0 and dv == 0:
        q.append(f"1) {var} = {nuqta} ni qo'ysak, surat ham, maxraj ham 0 bo'ladi: 0/0 aniqmaslik.")
    else:
        q.append(f"1) {var} = {nuqta} ni to'g'ridan-to'g'ri qo'yib bo'lmaydi (aniqmaslik yoki 0 ga bo'lish chiqadi).")
    c = sp.cancel(f)
    if c != f:
        q.append(f"2) Surat va maxrajni ko'paytuvchilarga ajratib qisqartiramiz: {c}")
        v = sp.simplify(c.subs(var, nuqta))
        q.append(f"3) Endi {var} = {nuqta} ni qo'yamiz: {v}")
    elif nv == 0 and dv == 0:
        d1, d2 = sp.diff(n, var), sp.diff(d, var)
        q.append(f"2) Lopital qoidasi: surat va maxrajning hosilasini olamiz: ({d1}) / ({d2})")
        v = sp.simplify((d1 / d2).subs(var, nuqta))
        if sp.simplify(v - javob) == 0:
            q.append(f"3) Endi {var} = {nuqta} ni qo'yamiz: {v}")
        else:
            q.append("3) Bu holda qo'shimcha usul kerak (masalan, Lopital qoidasini yana qo'llash).")
    q.append(f"Natija: {javob}")
    return q

def bosqich_matritsa(m):
    M = sp.Matrix(ast.literal_eval(m[m.index("[["):]))
    if M.rows != M.cols:
        raise ValueError("kvadrat matritsa kerak")
    n = M.rows
    d = M.det()
    q = [f"Matritsa: {M.tolist()}"]
    if n == 2:
        a, b, c, dd = M[0, 0], M[0, 1], M[1, 0], M[1, 1]
        q.append(f"1) 2x2 matritsada determinant: det = a\u00b7d - b\u00b7c = ({a})\u00b7({dd}) - ({b})\u00b7({c}) = {a * dd} - {b * c} = {d}")
    else:
        q.append("1) Determinantni 1-qator bo'yicha yoyamiz: det = a11\u00b7M11 - a12\u00b7M12 + a13\u00b7M13 - ... (Mij \u2014 mos minor).")
        qismlar = []
        for j in range(n):
            minor = M.minor_submatrix(0, j)
            mv = minor.det()
            q.append(f"   a1{j + 1} = {M[0, j]}, M1{j + 1} = det {minor.tolist()} = {mv}")
            qismlar.append(("+ " if j % 2 == 0 else "- ") + f"({M[0, j]})\u00b7({mv})")
        s = " ".join(qismlar)
        if s.startswith("+ "):
            s = s[2:]
        q.append(f"2) det = {s} = {d}")
    if "teskari" in m:
        if d == 0:
            q.append("Determinant 0, shuning uchun teskari matritsa mavjud emas.")
        else:
            if n == 2:
                q.append(f"2) Formula: A^-1 = 1/det \u00b7 [[d, -b], [-c, a]] = 1/({d}) \u00b7 {[[dd, -b], [-c, a]]}")
            else:
                q.append(f"2) Formula: A^-1 = (1/det)\u00b7adj(A). Qo'shma matritsa adj(A) = {M.adjugate().tolist()}")
            q.append(f"Natija: A^-1 = {M.inv().tolist()}")
    else:
        q.append(f"Natija: det = {d}")
    return q

getcontext().prec = 50
SON = r"(\d+(?:[.,]\d+)?)"
_SUB = str.maketrans("0123456789", "\u2080\u2081\u2082\u2083\u2084\u2085\u2086\u2087\u2088\u2089")
_SUP = str.maketrans("0123456789", "\u2070\u00b9\u00b2\u00b3\u2074\u2075\u2076\u2077\u2078\u2079")
def _fr(s):
    return Fraction(str(s).replace(",", "."))

def _o(fr):
    """Fraction -> o'nli yoki butun son matni (8 xonagacha)."""
    if fr.denominator == 1:
        return str(fr.numerator)
    d = (Decimal(fr.numerator) / Decimal(fr.denominator)).quantize(Decimal("1e-8"))
    t = format(d.normalize(), "f")
    if "." in t:
        t = t.rstrip("0").rstrip(".")
    return t or "0"

def _taqribiy(fr):
    d = fr.denominator
    while d % 2 == 0:
        d //= 2
    while d % 5 == 0:
        d //= 5
    return d != 1 or abs(fr.denominator) > 10 ** 8

def _teng(fr):
    return (" \u2248 " if _taqribiy(fr) else " = ") + _o(fr)

def _k(fr):
    return str(fr.numerator) if fr.denominator == 1 else f"{fr.numerator}/{fr.denominator}"

def _aralash_yoz(fr):
    if fr.denominator == 1 or abs(fr) < 1:
        return None
    ishora = "-" if fr < 0 else ""
    a = abs(fr)
    w, r = divmod(a.numerator, a.denominator)
    return f"{ishora}{w} {r}/{a.denominator}"

KASR_OP = r"(\d+\s+\d+\s*/\s*\d+|\d+\s*/\s*\d+|\d+)"
def _operand(t):
    t = t.strip()
    m1 = re.fullmatch(r"(\d+)\s+(\d+)\s*/\s*(\d+)", t)
    if m1:
        w, a, b = map(int, m1.groups())
        if b == 0:
            raise ZeroDivisionError
        return Fraction(w * b + a, b), f"{w} {a}/{b}", ("aralash", w, a, b)
    m2 = re.fullmatch(r"(\d+)\s*/\s*(\d+)", t)
    if m2:
        a, b = map(int, m2.groups())
        if b == 0:
            raise ZeroDivisionError
        return Fraction(a, b), f"{a}/{b}", ("kasr", a, b)
    return Fraction(int(t)), t, ("butun", int(t))

def _qisqartirish_qatori(n, d):
    g = math.gcd(abs(n), d)
    if g > 1:
        if d // g == 1:
            return f"Qisqartiramiz: {n}/{d} = {n // g} (surat va maxrajni {g} ga bo'ldik)"
        return f"Qisqartiramiz: {n}/{d} = {n // g}/{d // g} (surat va maxrajni {g} ga bo'ldik)"
    return None

def kasr_javob(m):
    try:
        # o'nli kasr -> oddiy kasr
        if "kasr" in m and "/" not in m and re.search(r"\d+[.,]\d+", m):
            s = re.search(r"\d+[.,]\d+", m).group().replace(",", ".")
            x = Fraction(s)
            xona = len(s.split(".")[1])
            n0, d0 = int(s.replace(".", "")), 10 ** xona
            q = [f"{s} = {n0}/{d0}"]
            sq = _qisqartirish_qatori(n0, d0)
            if sq:
                q.append(sq)
            q.append(f"Javob: {s} = {_k(x)}")
            return "\n".join(q), "natija"
        if not re.search(r"\d+\s*/\s*\d+", m):
            return None
        # arifmetik amal
        am = re.fullmatch(r"\s*(?:kasr\w*\s*:?\s*)?" + KASR_OP + r"\s*([+\-*:\u00f7\u00d7])\s*" + KASR_OP + r"\s*=?\s*\??\s*", m)
        if am:
            x1, raw1, t1 = _operand(am.group(1))
            op = am.group(2)
            x2, raw2, t2 = _operand(am.group(3))
            if t1[0] == "butun" and t2[0] == "butun":
                return None
            return _kasr_amal(x1, raw1, t1, op, x2, raw2, t2)
        # aralash son -> oddiy kasr (yoki aksincha)
        mm = re.search(r"(\d+)\s+(\d+)\s*/\s*(\d+)", m)
        qolgan = re.sub(r"(\d+)\s+(\d+)\s*/\s*(\d+)", " ", m)
        so_zlar = set(re.findall(r"[a-z']+", qolgan))
        ruxsat = {"aralash", "son", "sonni", "oddiy", "kasr", "kasrga", "o'tkaz", "o'tkazing", "aylantir", "aylantiring", "ni"}
        if mm and so_zlar <= ruxsat:
            w, a, b = map(int, mm.groups())
            if b == 0:
                return "Maxraj 0 bo'lishi mumkin emas.", "xato"
            n = w * b + a
            q = [f"{w} {a}/{b} = ({w}\u00b7{b} + {a})/{b} = {n}/{b}"]
            sq = _qisqartirish_qatori(n, b)
            if sq:
                q.append(sq)
            q.append(f"Javob: {w} {a}/{b} = {_k(Fraction(n, b))}")
            return "\n".join(q), "natija"
        f = re.search(r"(\d+)\s*/\s*(\d+)", m)
        a, b = int(f.group(1)), int(f.group(2))
        if re.search(r"qisqartir", m):
            if b == 0:
                return "Maxraj 0 bo'lishi mumkin emas.", "xato"
            g = math.gcd(a, b)
            if g == 1:
                return f"{a}/{b} kasri qisqarmaydi: EKUB({a}, {b}) = 1.", "natija"
            return (f"EKUB({a}, {b}) = {g}\nSurat va maxrajni {g} ga bo'lamiz: ({a} : {g})/({b} : {g}) = {a // g}/{b // g}\n"
                    f"Javob: {a}/{b} = {a // g}/{b // g}"), "natija"
        if re.search(r"aralash", m):
            if b == 0:
                return "Maxraj 0 bo'lishi mumkin emas.", "xato"
            if a < b:
                return f"{a}/{b} to'g'ri kasr (surat maxrajdan kichik), uni aralash songa o'tkazib bo'lmaydi.", "natija"
            w, r = divmod(a, b)
            if r == 0:
                return f"{a} : {b} = {w} (qoldiqsiz bo'linadi)\nJavob: {a}/{b} = {w}", "natija"
            return (f"{a} ni {b} ga bo'lamiz: {a} = {w}\u00b7{b} + {r}\nButun qismi {w}, qoldiq {r}.\n"
                    f"Javob: {a}/{b} = {w} {r}/{b}"), "natija"
        if re.search(r"o'?nli", m):
            if b == 0:
                return "Maxraj 0 bo'lishi mumkin emas.", "xato"
            x = Fraction(a, b)
            return f"{a} : {b} = {_o(x)}\nJavob: {a}/{b}{_teng(x)}", "natija"
        return None
    except ZeroDivisionError:
        return "0 ga bo'lib bo'lmaydi (maxraj yoki bo'luvchi 0 bo'lib qoldi).", "xato"

def _kasr_amal(x1, raw1, t1, op, x2, raw2, t2):
    opb = {"\u00d7": "*", "\u00f7": ":"}.get(op, op)
    q = [f"Misol: {raw1} {opb} {raw2}"]
    juft = []
    for x, raw, t in ((x1, raw1, t1), (x2, raw2, t2)):
        if t[0] == "aralash":
            _, w, a, b = t
            q.append(f"Aralash sonni oddiy kasrga o'tkazamiz: {raw} = ({w}\u00b7{b} + {a})/{b} = {x.numerator}/{x.denominator}")
        juft.append((x.numerator, x.denominator))
    (n1, d1), (n2, d2) = juft
    if opb in ("+", "-"):
        belgi = "+" if opb == "+" else "-"
        if d1 != d2:
            L = d1 * d2 // math.gcd(d1, d2)
            q.append(f"Umumiy maxraj: EKUK({d1}, {d2}) = {L}")
            m1, m2 = L // d1, L // d2
            if m1 != 1:
                q.append(f"{n1}/{d1} = ({n1}\u00b7{m1})/({d1}\u00b7{m1}) = {n1 * m1}/{L}")
            if m2 != 1:
                q.append(f"{n2}/{d2} = ({n2}\u00b7{m2})/({d2}\u00b7{m2}) = {n2 * m2}/{L}")
            n1, n2, D = n1 * m1, n2 * m2, L
        else:
            D = d1
        rn = n1 + n2 if opb == "+" else n1 - n2
        q.append(f"{n1}/{D} {belgi} {n2}/{D} = ({n1} {belgi} {n2})/{D} = {rn}/{D}")
        natija = Fraction(rn, D)
        sq = _qisqartirish_qatori(rn, D)
    elif opb == "*":
        rn, D = n1 * n2, d1 * d2
        q.append(f"Suratni suratga, maxrajni maxrajga ko'paytiramiz: ({n1}\u00b7{n2})/({d1}\u00b7{d2}) = {rn}/{D}")
        natija = Fraction(rn, D)
        sq = _qisqartirish_qatori(rn, D)
    else:
        if n2 == 0:
            raise ZeroDivisionError
        rn, D = n1 * d2, d1 * n2
        if D < 0:
            rn, D = -rn, -D
        q.append(f"Bo'lishda ikkinchi kasrni ag'daramiz: {n1}/{d1} : {n2}/{d2} = {n1}/{d1} \u00b7 {d2}/{n2} = {rn}/{D}")
        natija = Fraction(rn, D)
        sq = _qisqartirish_qatori(rn, D)
    if sq:
        q.append(sq)
    s = _k(natija)
    ar = _aralash_yoz(natija)
    if ar:
        s += f" = {ar}"
    if natija.denominator != 1:
        s += _teng(natija)
    q.append(f"Javob: {s}")
    return "\n".join(q), "natija"

def foiz_javob(m):
    if "%" not in m and "foiz" not in m:
        return None
    try:
        P_m = re.search(SON + r"\s*(?:%|foiz\w*)", m)
        ratio = re.search(r"necha\s*foiz", m)
        if ratio:
            sonlar = [(mm.group(1), mm.start()) for mm in re.finditer(SON, m)]
            if len(sonlar) < 2:
                return "Ikkita son yozing. Masalan: 50 soni 200 ning necha foizi", "xato"
            a, b = sonlar[0][0], sonlar[1][0]
            dan = re.search(SON + r"\s*dan\b", m)
            if dan and dan.group(1) == a:
                qism, butun = b, a
            else:
                qism, butun = a, b
            Q, B = _fr(qism), _fr(butun)
            if B == 0:
                return "Butun 0 bo'lishi mumkin emas.", "xato"
            r = Q / B * 100
            return (f"Foiz = (qism : butun) \u00b7 100% = ({qism} : {butun}) \u00b7 100% = {_o(Q / B)} \u00b7 100% = {_o(r)}%\n"
                    f"Javob: {qism} soni {butun} ning {_o(r)}% i"), "natija"
        if not P_m:
            return ("Foiz misollari: '200 ning 15%', '50 soni 200 ning necha foizi', "
                    "'200 ni 20% ga oshir', '15% i 30 bo'lgan son'"), "suhbat"
        P = _fr(P_m.group(1))
        ps = P_m.group(1)
        teng_m = re.search(r"(?:%|foiz\w*)\s*i?\s*" + SON + r"\s*(?:ga teng|bo'lgan|bo'lsa|ga)", m)
        if teng_m:
            V = _fr(teng_m.group(1))
            if P == 0:
                return "Foiz 0 bo'lishi mumkin emas.", "xato"
            butun = V * 100 / P
            return (f"{ps}% = {ps}/100 = {_o(P / 100)}\nButun = qism : (foiz/100) = {teng_m.group(1)} : {_o(P / 100)} = {_o(butun)}\n"
                    f"Javob: {_o(butun)}"), "natija"
        qolgan = m[:P_m.start()] + " " + m[P_m.end():]
        xm = re.search(SON, qolgan)
        if not xm:
            return f"{ps}% = {ps}/100 = {_k(P / 100)}{_teng(P / 100) if (P / 100).denominator != 1 else ''}", "natija"
        xs = xm.group(1)
        X = _fr(xs)
        oshdi = re.search(r"oshir|oshdi|ort\w*|qimmat|ko'pay|ustama|qo'sh", m)
        kamaydi = re.search(r"kamay|kamaytir|arzon|chegirma|tushir|tushdi|pasay|ayir", m)
        qism = X * P / 100
        if oshdi or kamaydi:
            if oshdi:
                yangi = X + qism
                return (f"{ps}% = {ps}/100 = {_o(P / 100)}\nOshgan qism: {xs} \u00b7 {ps}/100 = {_o(qism)}\n"
                        f"Yangi qiymat: {xs} + {_o(qism)} = {_o(yangi)}\n(yoki bevosita: {xs} \u00b7 {_o(1 + P / 100)} = {_o(yangi)})\n"
                        f"Javob: {_o(yangi)}"), "natija"
            yangi = X - qism
            return (f"{ps}% = {ps}/100 = {_o(P / 100)}\nKamaygan qism: {xs} \u00b7 {ps}/100 = {_o(qism)}\n"
                    f"Yangi qiymat: {xs} - {_o(qism)} = {_o(yangi)}\n(yoki bevosita: {xs} \u00b7 {_o(1 - P / 100)} = {_o(yangi)})\n"
                    f"Javob: {_o(yangi)}"), "natija"
        return (f"{ps}% = {ps}/100 = {_o(P / 100)}\n{xs} \u00b7 {ps}/100 = {_o(X * P)}/100 = {_o(qism)}\n"
                f"Javob: {xs} ning {ps}% i = {_o(qism)}"), "natija"
    except Exception:
        return "Foiz misolini tushunmadim. Masalan: 200 ning 15% yoki 50 soni 200 ning necha foizi", "xato"

def _jadval(**kat):
    return {k: {a: Fraction(v) for a, v in d.items()} for k, d in kat.items()}

BIRLIKLAR = _jadval(
    uzunlik={"mm": "0.001", "millimetr": "0.001", "sm": "0.01", "cm": "0.01", "santimetr": "0.01", "dm": "0.1",
             "detsimetr": "0.1", "m": "1", "metr": "1", "km": "1000", "kilometr": "1000", "mil": "1609.344",
             "fut": "0.3048", "ft": "0.3048", "dyum": "0.0254", "inch": "0.0254", "yard": "0.9144", "yd": "0.9144"},
    massa={"mg": "0.000001", "milligramm": "0.000001", "g": "0.001", "gr": "0.001", "gramm": "0.001", "kg": "1",
           "kilogramm": "1", "t": "1000", "tonna": "1000", "sentner": "100", "funt": "0.45359237",
           "lb": "0.45359237", "unsiya": "0.028349523125", "oz": "0.028349523125"},
    vaqt={"s": "1", "sek": "1", "sekund": "1", "min": "60", "daqiqa": "60", "soat": "3600", "h": "3600",
          "kun": "86400", "hafta": "604800", "oy": "2592000", "yil": "31536000"},
    hajm={"ml": "0.001", "millilitr": "0.001", "l": "1", "litr": "1", "m3": "1000", "gallon": "3.785411784"},
    yuza={"mm2": "0.000001", "sm2": "0.0001", "cm2": "0.0001", "dm2": "0.01", "m2": "1", "ar": "100",
          "sotix": "100", "ga": "10000", "gektar": "10000", "km2": "1000000"},
    tezlik={"m/s": "1", "km/soat": "5/18", "km/h": "5/18", "kmh": "5/18", "mil/soat": "0.44704", "mph": "0.44704"},
    malumot={"bayt": "1", "byte": "1", "kb": "1024", "kilobayt": "1024", "mb": "1048576", "megabayt": "1048576",
             "gb": "1073741824", "gigabayt": "1073741824", "tb": "1099511627776", "terabayt": "1099511627776"},
)
HARORAT = {"c": "C", "\u00b0c": "C", "\u00bac": "C", "celsiy": "C", "f": "F", "\u00b0f": "F", "\u00baf": "F",
           "farengeyt": "F", "k": "K", "kelvin": "K"}
BIRLIK_NOMI = {"C": "\u00b0C", "F": "\u00b0F", "K": "K"}
BIRLIK_ULANISH = {"necha", "qancha", "ni", "dan", "to", "=", "?", "->", "bo'ladi", "teng", "da", "ning",
                  "o'tkaz", "o'tkazing", "aylantir", "aylantiring"}
BIRLIK_QO_SHIMCHA = ("ga", "ka", "ni", "dan", "da", "ning")
def _birlik_top(t):
    if t in HARORAT:
        return ("harorat", HARORAT[t], t)
    for kat, d in BIRLIKLAR.items():
        if t in d:
            return (kat, d[t], t)
    return None

def _birlikni_ajrat(t):
    r = _birlik_top(t)
    if r:
        return r
    for q in BIRLIK_QO_SHIMCHA:
        if t.endswith(q) and len(t) > len(q) + 1:
            r = _birlik_top(t[:-len(q)])
            if r:
                return r
    return None

def _harorat_yoz(x, a, b):
    q = []
    C = x
    if a == "C":
        pass
    elif a == "F":
        C = (x - 32) * Fraction(5, 9)
        q.append(f"{BIRLIK_NOMI['F']} \u2192 {BIRLIK_NOMI['C']}: C = (F - 32) \u00b7 5/9 = ({_o(x)} - 32) \u00b7 5/9 = {_o(C)}")
    elif a == "K":
        C = x - Fraction("273.15")
        q.append(f"K \u2192 {BIRLIK_NOMI['C']}: C = K - 273.15 = {_o(x)} - 273.15 = {_o(C)}")
    if b == "C":
        R = C
    elif b == "F":
        R = C * Fraction(9, 5) + 32
        q.append(f"{BIRLIK_NOMI['C']} \u2192 {BIRLIK_NOMI['F']}: F = C \u00b7 9/5 + 32 = {_o(C)} \u00b7 9/5 + 32 = {_o(R)}")
    else:
        R = C + Fraction("273.15")
        q.append(f"{BIRLIK_NOMI['C']} \u2192 K: K = C + 273.15 = {_o(C)} + 273.15 = {_o(R)}")
    return q, R

def birlik_javob(m):
    mm = re.match(r"^\s*(-?\d+(?:[.,]\d+)?)\s*(.*)$", m)
    if not mm:
        return None
    sonmatn = mm.group(1).replace(",", ".")
    belgilar = re.findall(r"[a-z\u00b0\u00ba'/0-9\^]+|=|\?|->", mm.group(2))
    birliklar = [t for t in belgilar if t not in BIRLIK_ULANISH]
    if len(birliklar) == 3 and birliklar[-1] == "ga":
        birliklar = birliklar[:2]
    if len(birliklar) != 2:
        return None
    r1, r2 = _birlikni_ajrat(birliklar[0]), _birlikni_ajrat(birliklar[1])
    if not r1 or not r2:
        return None
    x = Fraction(sonmatn)
    if r1[0] != r2[0]:
        return (f"'{birliklar[0]}' va '{birliklar[1]}' turli kattaliklar ({r1[0]} va {r2[0]}), "
                f"ularni bir-biriga o'tkazib bo'lmaydi."), "xato"
    u1, u2 = r1[2], r2[2]
    if r1[0] == "harorat":
        a, b = r1[1], r2[1]
        if a == b:
            return f"Bir xil birlik: {sonmatn} {u1} = {sonmatn} {u2}", "natija"
        q, R = _harorat_yoz(x, a, b)
        q.append(f"Javob: {sonmatn} {BIRLIK_NOMI[a]} = {_o(R)} {BIRLIK_NOMI[b]}")
        return "\n".join(q), "natija"
    f1, f2 = r1[1], r2[1]
    faktor = f1 / f2
    R = x * faktor
    q = [f"1 {u1} = {_o(faktor)} {u2}", f"{sonmatn} {u1} = {sonmatn} \u00b7 {_o(faktor)} = {_o(R)} {u2}",
         f"Javob: {sonmatn} {u1}{_teng(R)} {u2}"]
    if "oy" in (u1, u2):
        q.append("(1 oy = 30 kun deb olindi)")
    return "\n".join(q), "natija"

def _s(v):
    return str(v)

def _heron_p(P):
    return (P["a"] + P["b"] + P["c"]) / 2

def _heron_sub(P):
    p = _heron_p(P)
    return f"\u221a({p}\u00b7({p}-{P['a']})\u00b7({p}-{P['b']})\u00b7({p}-{P['c']}))"

def _heron_val(P):
    p = _heron_p(P)
    if p - P["a"] <= 0 or p - P["b"] <= 0 or p - P["c"] <= 0:
        raise ValueError("uchburchak mavjud emas")
    return sp.sqrt(sp.simplify(p * (p - P["a"]) * (p - P["b"]) * (p - P["c"])))

GEO_SHAPES = [
    ("doira", r"\b(?:doira|aylana)\w*", "Doira", ["r"], [
        ("yuza", "Yuza", "S = \u03c0\u00b7r\u00b2", lambda P: f"\u03c0\u00b7{_s(P['r'])}\u00b2", lambda P: sp.pi * P["r"] ** 2, ["r"]),
        ("perimetr", "Aylana uzunligi", "l = 2\u00b7\u03c0\u00b7r", lambda P: f"2\u00b7\u03c0\u00b7{_s(P['r'])}", lambda P: 2 * sp.pi * P["r"], ["r"])]),
    ("kvadrat", r"\bkvadrat\w*", "Kvadrat", ["a"], [
        ("yuza", "Yuza", "S = a\u00b2", lambda P: f"{_s(P['a'])}\u00b2", lambda P: P["a"] ** 2, ["a"]),
        ("perimetr", "Perimetr", "P = 4\u00b7a", lambda P: f"4\u00b7{_s(P['a'])}", lambda P: 4 * P["a"], ["a"]),
        ("diagonal", "Diagonal", "d = a\u00b7\u221a2", lambda P: f"{_s(P['a'])}\u00b7\u221a2", lambda P: P["a"] * sp.sqrt(2), ["a"])]),
    ("tortburchak", r"\bto'?g'?ri\s+to'?rtburchak\w*|\bto'?rtburchak\w*", "To'g'ri to'rtburchak", ["a", "b"], [
        ("yuza", "Yuza", "S = a\u00b7b", lambda P: f"{_s(P['a'])}\u00b7{_s(P['b'])}", lambda P: P["a"] * P["b"], ["a", "b"]),
        ("perimetr", "Perimetr", "P = 2\u00b7(a + b)", lambda P: f"2\u00b7({_s(P['a'])} + {_s(P['b'])})", lambda P: 2 * (P["a"] + P["b"]), ["a", "b"]),
        ("diagonal", "Diagonal", "d = \u221a(a\u00b2 + b\u00b2)", lambda P: f"\u221a({_s(P['a'])}\u00b2 + {_s(P['b'])}\u00b2)", lambda P: sp.sqrt(P["a"] ** 2 + P["b"] ** 2), ["a", "b"])]),
    ("uchburchak", r"\buchburchak\w*", "Uchburchak", ["a", "b", "c"], [
        ("perimetr", "Perimetr", "P = a + b + c", lambda P: f"{_s(P['a'])} + {_s(P['b'])} + {_s(P['c'])}", lambda P: P["a"] + P["b"] + P["c"], ["a", "b", "c"]),
        ("yuza", "Yuza (Geron formulasi, p \u2014 yarim perimetr)", "S = \u221a(p\u00b7(p-a)\u00b7(p-b)\u00b7(p-c))", lambda P: _heron_sub(P), lambda P: _heron_val(P), ["a", "b", "c"]),
        ("yuza", "Yuza", "S = a\u00b7h/2", lambda P: f"{_s(P['a'])}\u00b7{_s(P['h'])}/2", lambda P: P["a"] * P["h"] / 2, ["a", "h"])]),
    ("parallelogram", r"\bparallelogram\w*", "Parallelogram", ["a", "h"], [
        ("yuza", "Yuza", "S = a\u00b7h", lambda P: f"{_s(P['a'])}\u00b7{_s(P['h'])}", lambda P: P["a"] * P["h"], ["a", "h"]),
        ("perimetr", "Perimetr", "P = 2\u00b7(a + b)", lambda P: f"2\u00b7({_s(P['a'])} + {_s(P['b'])})", lambda P: 2 * (P["a"] + P["b"]), ["a", "b"])]),
    ("trapetsiya", r"\btrapetsiya\w*", "Trapetsiya", ["a", "b", "h"], [
        ("yuza", "Yuza", "S = (a + b)/2 \u00b7 h", lambda P: f"({_s(P['a'])} + {_s(P['b'])})/2 \u00b7 {_s(P['h'])}", lambda P: (P["a"] + P["b"]) / 2 * P["h"], ["a", "b", "h"])]),
    ("romb", r"\bromb\w*", "Romb", ["d1", "d2"], [
        ("yuza", "Yuza", "S = d\u2081\u00b7d\u2082/2", lambda P: f"{_s(P['d1'])}\u00b7{_s(P['d2'])}/2", lambda P: P["d1"] * P["d2"] / 2, ["d1", "d2"]),
        ("perimetr", "Perimetr", "P = 4\u00b7a", lambda P: f"4\u00b7{_s(P['a'])}", lambda P: 4 * P["a"], ["a"])]),
    ("kub", r"\bkub\w*", "Kub", ["a"], [
        ("hajm", "Hajm", "V = a\u00b3", lambda P: f"{_s(P['a'])}\u00b3", lambda P: P["a"] ** 3, ["a"]),
        ("sirt", "To'liq sirt yuzi", "S = 6\u00b7a\u00b2", lambda P: f"6\u00b7{_s(P['a'])}\u00b2", lambda P: 6 * P["a"] ** 2, ["a"])]),
    ("parallelepiped", r"\bparallelepiped\w*", "To'g'ri burchakli parallelepiped", ["a", "b", "c"], [
        ("hajm", "Hajm", "V = a\u00b7b\u00b7c", lambda P: f"{_s(P['a'])}\u00b7{_s(P['b'])}\u00b7{_s(P['c'])}", lambda P: P["a"] * P["b"] * P["c"], ["a", "b", "c"]),
        ("sirt", "To'liq sirt yuzi", "S = 2\u00b7(ab + bc + ac)", lambda P: f"2\u00b7({_s(P['a'])}\u00b7{_s(P['b'])} + {_s(P['b'])}\u00b7{_s(P['c'])} + {_s(P['a'])}\u00b7{_s(P['c'])})", lambda P: 2 * (P["a"] * P["b"] + P["b"] * P["c"] + P["a"] * P["c"]), ["a", "b", "c"])]),
    ("silindr", r"\bsilindr\w*", "Silindr", ["r", "h"], [
        ("hajm", "Hajm", "V = \u03c0\u00b7r\u00b2\u00b7h", lambda P: f"\u03c0\u00b7{_s(P['r'])}\u00b2\u00b7{_s(P['h'])}", lambda P: sp.pi * P["r"] ** 2 * P["h"], ["r", "h"]),
        ("yon", "Yon sirt yuzi", "S = 2\u00b7\u03c0\u00b7r\u00b7h", lambda P: f"2\u00b7\u03c0\u00b7{_s(P['r'])}\u00b7{_s(P['h'])}", lambda P: 2 * sp.pi * P["r"] * P["h"], ["r", "h"]),
        ("sirt", "To'liq sirt yuzi", "S = 2\u00b7\u03c0\u00b7r\u00b7(r + h)", lambda P: f"2\u00b7\u03c0\u00b7{_s(P['r'])}\u00b7({_s(P['r'])} + {_s(P['h'])})", lambda P: 2 * sp.pi * P["r"] * (P["r"] + P["h"]), ["r", "h"])]),
    ("konus", r"\bkonus\w*", "Konus", ["r", "h"], [
        ("yasovchi", "Yasovchi", "l = \u221a(r\u00b2 + h\u00b2)", lambda P: f"\u221a({_s(P['r'])}\u00b2 + {_s(P['h'])}\u00b2)", lambda P: sp.sqrt(P["r"] ** 2 + P["h"] ** 2), ["r", "h"]),
        ("hajm", "Hajm", "V = \u03c0\u00b7r\u00b2\u00b7h/3", lambda P: f"\u03c0\u00b7{_s(P['r'])}\u00b2\u00b7{_s(P['h'])}/3", lambda P: sp.pi * P["r"] ** 2 * P["h"] / 3, ["r", "h"]),
        ("yon", "Yon sirt yuzi", "S = \u03c0\u00b7r\u00b7l", lambda P: f"\u03c0\u00b7{_s(P['r'])}\u00b7\u221a({_s(P['r'])}\u00b2 + {_s(P['h'])}\u00b2)", lambda P: sp.pi * P["r"] * sp.sqrt(P["r"] ** 2 + P["h"] ** 2), ["r", "h"]),
        ("sirt", "To'liq sirt yuzi", "S = \u03c0\u00b7r\u00b7(r + l)", lambda P: f"\u03c0\u00b7{_s(P['r'])}\u00b7({_s(P['r'])} + \u221a({_s(P['r'])}\u00b2 + {_s(P['h'])}\u00b2))", lambda P: sp.pi * P["r"] * (P["r"] + sp.sqrt(P["r"] ** 2 + P["h"] ** 2)), ["r", "h"])]),
    ("shar", r"\bshar(?:ning|ni|dan|\b)\w*", "Shar", ["r"], [
        ("hajm", "Hajm", "V = 4/3\u00b7\u03c0\u00b7r\u00b3", lambda P: f"4/3\u00b7\u03c0\u00b7{_s(P['r'])}\u00b3", lambda P: sp.Rational(4, 3) * sp.pi * P["r"] ** 3, ["r"]),
        ("sirt", "Sirt yuzi", "S = 4\u00b7\u03c0\u00b7r\u00b2", lambda P: f"4\u00b7\u03c0\u00b7{_s(P['r'])}\u00b2", lambda P: 4 * sp.pi * P["r"] ** 2, ["r"])]),
]
def _geo_qiymat(v):
    ifoda = sp.nsimplify(v) if not isinstance(v, sp.Basic) else v
    s = str(sp.simplify(ifoda))
    if ifoda.has(sp.pi) or ifoda.has(sp.sqrt(2)) or any(isinstance(a, sp.Pow) and a.exp.is_Rational and not a.exp.is_Integer for a in sp.preorder_traversal(ifoda)):
        return f"{s} \u2248 {sp.N(ifoda, 6)}"
    return s

def geometriya_javob(m):
    pyth = re.search(r"\b(gipotenuza\w*|katet\w*|pifagor\w*)", m)
    shakl = None
    for kalit, rg, nom, tartib, elementlar in GEO_SHAPES:
        if re.search(rg, m):
            shakl = (kalit, nom, tartib, elementlar)
            break
    if not shakl and not pyth:
        return None
    # parametrlarni o'qish
    P = {}
    nom_p = {}
    for pm in re.finditer(r"\b(d1|d2|r|a|b|c|h|d)\s*=\s*" + SON, m):
        P[pm.group(1)] = sp.Rational(str(_fr(pm.group(2))))
    for so_z, k in ((r"radius\w*", "r"), (r"balandlik\w*", "h"), (r"diametr\w*", "d"), (r"(?:tomon\w*|asos\w*)", "a")):
        pm = re.search(so_z + r"\s*[=:]?\s*" + SON, m)
        if pm and k not in P:
            P[k] = sp.Rational(str(_fr(pm.group(1))))
    if "d" in P and "r" not in P and shakl and "r" in shakl[2]:
        P["r"] = P["d"] / 2
        nom_p["r"] = f"Diametr d = {P['d']} bo'lgani uchun radius r = d/2 = {P['r']}"
    if not P:
        sonlar = [sp.Rational(str(_fr(x))) for x in re.findall(SON, m)]
        if pyth:
            tartib = ["c", "a"] if re.search(r"katet", m) else ["a", "b"]
        elif shakl:
            tartib = shakl[2]
        else:
            tartib = []
        for k, v in zip(tartib, sonlar):
            P[k] = v
    # Pifagor
    if pyth or (shakl and shakl[0] == "uchburchak" and re.search(r"burchakli", m) and "a" in P and "b" in P and "c" not in P):
        if re.search(r"katet", m) and "c" in P and ("a" in P or "b" in P):
            k = "a" if "a" in P else "b"
            n = "b" if k == "a" else "a"
            if P["c"] <= P[k]:
                return "Gipotenuza katetdan katta bo'lishi kerak.", "xato"
            val = sp.sqrt(P["c"] ** 2 - P[k] ** 2)
            return (f"Pifagor teoremasi: c\u00b2 = a\u00b2 + b\u00b2, demak {n} = \u221a(c\u00b2 - {k}\u00b2)\n"
                    f"{n} = \u221a({P['c']}\u00b2 - {P[k]}\u00b2) = {_geo_qiymat(val)}"), "natija"
        if "a" in P and "b" in P:
            c = sp.sqrt(P["a"] ** 2 + P["b"] ** 2)
            q = [f"Pifagor teoremasi: c\u00b2 = a\u00b2 + b\u00b2",
                 f"c = \u221a({P['a']}\u00b2 + {P['b']}\u00b2) = \u221a{P['a'] ** 2 + P['b'] ** 2} = {_geo_qiymat(c)}"]
            if shakl and shakl[0] == "uchburchak":
                q.append(f"Yuza: S = a\u00b7b/2 = {P['a']}\u00b7{P['b']}/2 = {P['a'] * P['b'] / 2}")
                q.append(f"Perimetr: P = a + b + c = {P['a']} + {P['b']} + {sp.simplify(c)} = {_geo_qiymat(P['a'] + P['b'] + c)}")
            return "\n".join(q), "natija"
        return "Pifagor uchun ikki tomonni yozing. Masalan: gipotenuza a=3 b=4 yoki katet c=5 a=3", "xato"
    kalit, nom, tartib, elementlar = shakl
    # so'ralgan kattalik
    qk = None
    if re.search(r"\bsirt", m):
        qk = "yon" if re.search(r"\byon\b", m) else "sirt"
    elif re.search(r"\byuz\w*", m):
        qk = "yuza"
    elif re.search(r"perimetr|uzunlig|atrof", m):
        qk = "perimetr"
    elif re.search(r"hajm", m):
        qk = "hajm"
    elif re.search(r"diagonal", m):
        qk = "diagonal"
    elif re.search(r"yasovchi", m):
        qk = "yasovchi"
    if not P and qk is None:
        return None
    tanlangan = [e for e in elementlar if (qk is None or e[0] == qk) and all(n in P for n in e[5])]
    if not tanlangan:
        mumkin = [e for e in elementlar if qk is None or e[0] == qk]
        kerak = mumkin[0][5] if mumkin else tartib
        yoq = [n for n in kerak if n not in P]
        yoz = {"r": "r (radius)", "a": "a", "b": "b", "c": "c", "h": "h (balandlik)", "d1": "d1", "d2": "d2"}
        return (f"{nom} uchun yetishmayapti: {', '.join(yoz.get(n, n) for n in yoq)}. "
                f"Masalan: {kalit.replace('tortburchak', 'to`g`ri tortburchak')} yuzi " +
                " ".join(f"{n}=5" for n in kerak)), "xato"
    if qk is None:
        korilgan = set()
        yangi = []
        for e in tanlangan:
            if e[0] in korilgan and kalit == "uchburchak":
                continue
            korilgan.add(e[0])
            yangi.append(e)
        tanlangan = yangi
    sarlavha = f"{nom}: " + ", ".join(f"{k} = {v}" for k, v in P.items() if k != "d" or "r" not in P)
    q = [sarlavha]
    q.extend(nom_p.values())
    try:
        for e in tanlangan:
            q.append(f"{e[1]}: {e[2]} = {e[3](P)} = {_geo_qiymat(e[4](P))}")
    except ValueError:
        return "Bunday uchburchak mavjud emas: tomonlar uchburchak tengsizligini qanoatlantirmaydi.", "xato"
    return "\n".join(q), "natija"

BAZA_REGEXLAR = [
    (16, r"o'?n\s*oltilik\w*|oltilik\w*|heksa\w*|\bhex\w*"),
    (2, r"ikkilik\w*|binar\w*"),
    (8, r"sakkizlik\w*|oktal\w*"),
    (10, r"o'nlik\w*|decimal"),
]
RAQAMLAR = "0123456789ABCDEF"
def _raqam_qiymati(ch):
    return RAQAMLAR.index(ch.upper())

def _ondan(n, b):
    if n == 0:
        return "0", ["0 : %d = 0 (qoldiq 0)" % b]
    q, qoldiqlar, n0 = [], [], n
    while n0 > 0:
        d, r = divmod(n0, b)
        belgi = RAQAMLAR[r]
        q.append(f"{n0} : {b} = {d} (qoldiq {r}" + (f" = {belgi}" if r > 9 else "") + ")")
        qoldiqlar.append(belgi)
        n0 = d
    return "".join(reversed(qoldiqlar)), q

def _ongacha(tok, b):
    t = tok.upper()
    n = int(t, b)
    if b == 10:
        return n, []
    qismlar, qiymatlar = [], []
    for i, ch in enumerate(t):
        p = len(t) - 1 - i
        d = _raqam_qiymati(ch)
        belgi = ch if d < 10 else f"{ch}({d})"
        qismlar.append(f"{belgi}\u00b7{b}{str(p).translate(_SUP)}")
        qiymatlar.append(str(d * b ** p))
    return n, [f"{t}{str(b).translate(_SUB)} = " + " + ".join(qismlar) + " = " + " + ".join(qiymatlar) + f" = {n}"]

def sanoq_javob(m):
    if "/" in m:
        return None
    belgi = re.search(r"\b([0-9a-f]+)\s*\((2|8|10|16)\)", m)
    mentions = []
    for baza, rg in BAZA_REGEXLAR:
        for mt in re.finditer(rg, m):
            mentions.append((mt.start(), mt.end(), baza, mt.group()))
    # ichma-ich bo'lganlarini olib tashlaymiz
    mentions = [x for x in mentions if not any(y is not x and y[0] <= x[0] and x[1] <= y[1] and (y[1] - y[0]) > (x[1] - x[0]) for y in mentions)]
    mentions.sort()
    if not mentions:
        return None
    try:
        if belgi:
            src = int(belgi.group(2))
            tok = belgi.group(1)
            dst = mentions[0][2] if mentions else 10
        elif len(mentions) == 1:
            baza, soz = mentions[0][2], mentions[0][3]
            if soz.endswith("dan"):
                src, dst = baza, 10
            else:
                src, dst = 10, baza
            tok = None
        else:
            src, dst = mentions[0][2], mentions[1][2]
            tok = None
        if tok is None:
            qolgan = m
            for st, en, _, _ in reversed(mentions):
                qolgan = qolgan[:st] + " " + qolgan[en:]
            toklar = re.findall(r"\b[0-9a-f]+\b", qolgan)
            raqamlilar = [t for t in toklar if any(c.isdigit() for c in t)]
            if raqamlilar:
                tok = raqamlilar[0]
            elif src == 16:
                harfli = [t for t in toklar if len(t) >= 2 and t not in ("da", "ba", "fa", "ab")]
                tok = harfli[0] if harfli else None
        if tok is None:
            return "Qaysi sonni o'tkazay? Masalan: 25 ikkilik yoki 1011 ikkilikdan o'nlikka", "suhbat"
        if src == dst:
            return "Sonlar bir xil sistemada, o'tkazish shart emas.", "natija"
        if len(tok) > 24:
            return "Son juda uzun, 24 raqamgacha yozing.", "xato"
        for ch in tok:
            if _raqam_qiymati(ch) >= src:
                return f"{tok} soni {src} lik sistemada bo'lishi mumkin emas ('{ch.upper()}' raqami katta).", "xato"
        n, qadamlar = _ongacha(tok, src)
        sub = lambda b: str(b).translate(_SUB)
        q = []
        if src != 10:
            q.append(f"{tok.upper()}{sub(src)} ni o'nlik sistemaga o'tkazamiz:")
            q.extend(qadamlar)
        if dst != 10:
            if n > 10 ** 18:
                return "Son juda katta, 10^18 gacha yozing.", "xato"
            if src != 10:
                q.append(f"Endi {n} ni {dst} lik sistemaga o'tkazamiz (bo'lib, qoldiqlarni yozamiz):")
            else:
                q.append(f"{n} ni {dst} ga bo'lib, qoldiqlarni yozamiz:")
            natija, bol = _ondan(n, dst)
            q.extend(bol)
            q.append("Qoldiqlarni pastdan yuqoriga o'qiymiz: " + natija)
        else:
            natija = str(n)
        q.append(f"Javob: {tok.upper()}{sub(src)} = {natija}{sub(dst)}")
        return "\n".join(q), "natija"
    except Exception:
        return "Sanoq sistemasi misolini tushunmadim. Masalan: 25 ikkilik yoki ff o'n oltilikdan o'nlikka", "xato"

TUZATISH_SOZLARI = ["hosila", "integral", "limit", "grafik", "bosqich", "soddalashtir", "determinant", "matritsa",
                    "teskari", "tizim", "ajrat", "ekub", "ekuk", "qisqartir", "aralash", "foiz", "necha", "kvadrat",
                    "uchburchak", "doira", "aylana", "silindr", "konus", "trapetsiya", "parallelogram", "yuzi",
                    "hajm", "perimetr", "diagonal", "gipotenuza", "ikkilik", "sakkizlik", "kasr", "radius"]
BILINADIGAN_SOZLAR = {"sin", "cos", "tan", "cot", "log", "exp", "abs", "sqrt", "det", "och", "ning", "dan", "ni", "ga",
                      "bir", "ikki", "uch", "to'rt", "besh", "olti", "yetti", "sakkiz", "to'qqiz", "ming", "yuz",
                      "kub", "shar", "romb", "yuza", "nechta", "tomon", "asos", "soni", "sonni", "ayir", "qo'sh", "bo'l", "oshir", "kamay", "arzon", "metr", "gramm", "litr"}
def matnni_tuzat(matn):
    """Kalit so'zlardagi arzimas xatolarni to'g'rilaydi: 'hosla x^3' -> 'hosila x^3'."""
    if len(matn) > 120:
        return matn, []
    kichik = matn.lower()
    mathy = bool(re.search(r"[\d\^=\(\)\[\]/%]|->", kichik)) or bool(re.search(r"(?<![a-z'])[xyz](?![a-z'])", kichik))
    if not mathy:
        return matn, []
    natija, oxirgi, tuzatishlar = [], 0, []
    birinchi = True
    for mt in re.finditer(r"[a-zA-Z']+", matn):
        w = mt.group().lower().strip("'")
        boshlandi = birinchi
        birinchi = False
        if len(w) < 4 or w in BILINADIGAN_SOZLAR or w in TUZATISH_SOZLARI:
            continue
        if any(w.startswith(k) for k in TUZATISH_SOZLARI if len(k) >= 4):
            continue
        if len(w) == 3 and not boshlandi:
            continue
        cutoff = 0.85 if len(w) == 3 else (0.86 if len(w) == 4 else 0.84)
        c = difflib.get_close_matches(w, TUZATISH_SOZLARI, n=1, cutoff=cutoff)
        if c:
            natija.append(matn[oxirgi:mt.start()])
            natija.append(c[0])
            oxirgi = mt.end()
            tuzatishlar.append((mt.group(), c[0]))
    natija.append(matn[oxirgi:])
    return "".join(natija), tuzatishlar

def taklif_top(m):
    """Tushunilmagan misol uchun arzimas tuzatishlar bilan ishlaydigan variantni topadi."""
    if "tizim" in m:
        return None
    variantlar = []
    def v1(t):
        d = t.count("(") - t.count(")")
        if d > 0:
            return t + ")" * d
        while d < 0 and t.endswith(")"):
            t, d = t[:-1], d + 1
        return t
    def v2(t):
        return re.sub(r"(?<![a-z\d])([xy])(\d+)", r"\1^\2", t)
    def v3(t):
        return re.sub(r"(\d),(\d)", r"\1.\2", t)
    def v4(t):
        t = t.strip()
        t = re.sub(r"[?\s]+$", "", t)
        if t.endswith("="):
            t += "0"
        t = re.sub(r"[+\-*/^\s]+$", "", t)
        return t
    def v5(t):
        return t.replace("==", "=").replace("++", "+").replace("**", "^")
    funksiyalar = [v1, v2, v3, v4, v5]
    hammasi = m
    for f in funksiyalar:
        variantlar.append(f(m))
        hammasi = f(hammasi)
    variantlar.append(hammasi)
    korilgan = {m}
    for v in variantlar:
        if v in korilgan or not v:
            continue
        korilgan.add(v)
        try:
            turi, _ = matematikani_yech(v)
        except Exception:
            continue
        if turi != "xato":
            return v
    return None

BOSQICH_BOSHI = r"^(bosqichma-bosqich|bosqichlar|bosqich|qadam-baqadam|qadamlar|qadam)\b[\s:]*"
def bosqich_soraldimi(matn):
    return re.match(BOSQICH_BOSHI, matn.lower().strip()) is not None

def had_qoidasi_hosila(t, x):
    if not t.has(x):
        return "o'zgarmasning hosilasi 0"
    if t == x:
        return "x' = 1"
    if t.is_Pow and t.base == x and t.exp.is_number:
        return "daraja qoidasi: (x^n)' = n\u00b7x^(n-1)"
    if t.is_Mul:
        son, qolgan = t.as_independent(x)
        if son != 1:
            return "o'zgarmas ko'paytuvchi tashqariga chiqadi"
        return "ko'paytma qoidasi: (u\u00b7v)' = u'\u00b7v + u\u00b7v'"
    if t.is_Pow:
        return "murakkab funksiya (zanjir) qoidasi"
    return "murakkab funksiya yoki jadvaldagi hosila"

def had_qoidasi_integral(t, x):
    if not t.has(x):
        return "o'zgarmasning integrali: c\u00b7x"
    if t == x:
        return "x ning integrali: x^2/2"
    if t.is_Pow and t.base == x and t.exp.is_number:
        if t.exp == -1:
            return "1/x ning integrali: ln|x|"
        return "daraja qoidasi: x^n ning integrali x^(n+1)/(n+1)"
    if t.is_Mul:
        son, qolgan = t.as_independent(x)
        if son != 1:
            return "o'zgarmas ko'paytuvchi tashqariga chiqadi"
    return "jadvaldagi yoki almashtirish usuli bilan integral"

def bosqichlarni_top(matn):
    m = re.sub(BOSQICH_BOSHI, "", matn.lower().strip()).strip()
    if not m:
        return "Qaysi misolning yechimini ko'rsatay? Masalan: bosqich x^2-5x+6=0", \
               "suhbat"
    x = sp.symbols('x')
    q = []
    try:
        if m.startswith("tizim"):
            q = bosqich_tizim(m)
        elif "limit" in m:
            q = bosqich_limit(m)
        elif ("det" in m or "matritsa" in m) and "[[" in m:
            q = bosqich_matritsa(m)
        elif re.search(r"\bek(ub|uk)", m):
            return ekub_ekuk_javob(m)
        elif "hosila" in m:
            ifoda = re.sub(r"\b(hosila|ol|dan|ning)\b", "", m).strip()
            f = oqi(ifoda)
            q.append(f"Funksiya: f(x) = {f}")
            hadlar = sp.Add.make_args(f)
            if len(hadlar) > 1:
                q.append("Yig'indining hosilasi \u2014 har bir had hosilasining yig'indisi. Hadlarni alohida olamiz:")
            for i, t in enumerate(hadlar, 1):
                q.append(f"{i}) ({t})' = {sp.diff(t, x)}   [{had_qoidasi_hosila(t, x)}]")
            q.append(f"Natija: f'(x) = {sp.diff(f, x)}")
        elif "integral" in m:
            ifoda = re.sub(r"\b(integral|ol|dan|ning)\b", "", m).strip()
            f = oqi(ifoda)
            q.append(f"Funksiya: f(x) = {f}")
            hadlar = sp.Add.make_args(sp.expand(f) if f.is_polynomial(x) else f)
            if len(hadlar) > 1:
                q.append("Yig'indining integrali \u2014 har bir had integralining yig'indisi. Hadlarni alohida olamiz:")
            for i, t in enumerate(hadlar, 1):
                q.append(f"{i}) integral ({t}) dx = {sp.integrate(t, x)}   [{had_qoidasi_integral(t, x)}]")
            q.append(f"Natija: {sp.integrate(f, x)} + C")
        elif "=" in m and "tizim" not in m:
            chap, ong = m.split("=")
            L, R = oqi(chap), oqi(ong)
            q.append(f"Tenglama: {L} = {R}")
            f = sp.expand(L - R)
            if R != 0 or f != L:
                q.append(f"1) Hammasini chap tomonga o'tkazib, soddalashtiramiz: {f} = 0")
            p = sp.Poly(f, x)
            d = p.degree()
            if d == 1:
                a, b = p.all_coeffs()
                q.append(f"2) Bu chiziqli tenglama: a\u00b7x + b = 0, bunda a = {a}, b = {b}")
                q.append(f"3) Ozod hadni o'ng tomonga o'tkazamiz: {a}\u00b7x = {-b}")
                q.append(f"4) {a} ga bo'lamiz: x = {sp.nsimplify(-b / a)}")
            elif d == 2:
                a, b, c = p.all_coeffs()
                D = sp.simplify(b**2 - 4 * a * c)
                q.append(f"2) Bu kvadrat tenglama: a\u00b7x^2 + b\u00b7x + c = 0, bunda a = {a}, b = {b}, c = {c}")
                q.append(f"3) Diskriminant: D = b^2 - 4\u00b7a\u00b7c = ({b})^2 - 4\u00b7({a})\u00b7({c}) = {D}")
                if D > 0:
                    q.append("4) D > 0, demak ikkita turli ildiz bor: x = (-b \u00b1 \u221aD) / (2a)")
                    r = sp.solve(f, x)
                    q.append("5) " + ",  ".join(f"x{i} = {sp.simplify(v)}" for i, v in enumerate(r, 1)))
                elif D == 0:
                    q.append("4) D = 0, demak bitta ildiz bor: x = -b / (2a)")
                    q.append(f"5) x = {sp.solve(f, x)[0]}")
                else:
                    q.append("4) D < 0, demak haqiqiy ildiz yo'q.")
            elif d >= 3:
                q.append(f"2) Ko'paytuvchilarga ajratamiz: {sp.factor(f)} = 0")
                q.append("3) Har bir ko'paytuvchini nolga tenglaymiz va ildizlarni topamiz.")
                q.append("Ildizlar: " + ", ".join(str(v) for v in sp.solve(f, x)))
            else:
                return "Bu tenglamada x qatnashmagan, shuning uchun bosqichlar kerak emas.", "xato"
            if d == 2 and D < 0:
                q.append("Javob: haqiqiy ildiz yo'q.")
            else:
                q.append(f"Javob: x = {sp.solve(f, x)}")
        else:
            return "Bosqichlarni tenglama, hosila, integral, limit, tizim, matritsa va EKUB/EKUK uchun ko'rsata olaman. " \
                   "Masalan: bosqich x^2-5x+6=0 yoki bosqich hosila x^3+2x", "xato"
    except Exception:
        return "Bu misol uchun bosqichlarni hosil qila olmadim. Oddiy ko'rinishda yozib ko'ring.", "xato"
    return "\n".join(q), "natija"

QISQA_HA = {"ha", "xop", "xo'p", "mayli", "ok", "okay", "okey", "bo'pti", "bopti", "yaxshi", "mayli bo'ladi"}
QISQA_YOQ = {"yo'q", "yoq", "kerak emas", "kerakmas", "hech narsa", "bo'ldi", "boldi", "bas"}
QISQA_TUSHUNDIM = {"tushunarli", "tushundim", "tushunaman", "aniq", "tushunarli rahmat"}
QISQA_MAQTOV = {"zo'r", "zor", "ajoyib", "super", "a'lo", "alo", "barakalla"}
QISQA_HA_JAVOB = [
    "Yaxshi! Misolingizni yozing, yechamiz.",
    "Tayyorman. Qaysi misoldan boshlaymiz?",
    "Mayli, davom etamiz. Savolingizni yozing.",
]
QISQA_YOQ_JAVOB = [
    "Mayli. Kerak bo'lsa, yozavering.",
    "Tushunarli. Savol tug'ilsa, men shu yerdaman.",
    "Xo'p, shoshilmang. Tayyor bo'lganingizda yozing.",
]
QISQA_TUSHUNDIM_JAVOB = [
    "Zo'r! Yana bir misol yechamizmi?",
    "Ajoyib. Tushunmagan joyingiz bo'lsa, \"bosqich\" so'zi bilan yozing, qadamlarini ko'rsataman.",
    "Yaxshi! Davom etamizmi?",
]
def qisqa_javob(matn):
    s = matn.lower().strip()
    for ch in "\u02bb\u02bc\u2019`\u2018":
        s = s.replace(ch, "'")
    s = re.sub(r"[^\w' ]+", "", s).strip()
    if s in QISQA_HA:
        return ism_bilan(QISQA_HA_JAVOB)
    if s in QISQA_YOQ:
        return ism_bilan(QISQA_YOQ_JAVOB)
    if s in QISQA_TUSHUNDIM:
        return ism_bilan(QISQA_TUSHUNDIM_JAVOB)
    if s in QISQA_MAQTOV:
        return ism_bilan(MAQTOV_JAVOBLARI)
    return None

NATIJA_SHABLONLARI = {
    "tenglama": ["Yechim: x = {v}", "Tenglamani yechsam, x = {v} chiqdi", "x = {v} ekan"],
    "hosila": ["Hosilasi: {v}", "Hosilani topdim: {v}", "Hosila natijasi: {v}"],
    "integral": ["Integrali: {v} + C", "Integralni hisobladim: {v} + C", "Natija: {v} + C"],
    "limit": ["Limit: {v}", "Limitni hisobladim: {v}", "Chegaraviy qiymat: {v}"],
    "soddalashtir": ["Soddalashtirilgan: {v}", "Soddalashtirsam: {v} chiqadi"],
    "determinant": ["Determinant: {v}", "Determinantini hisobladim: {v}"],
    "teskari": ["Teskari matritsa: {v}", "Teskari matritsani topdim: {v}"],
    "tizim": ["Yechim: {v}", "Tizimni yechsam: {v}"],
    "hisob": ["Natija: {v}", "Hisoblasam: {v} chiqadi", "Javob: {v}"],
}
XATO_JAVOBLARI = [
    "Kechirasiz, bu ifodani tushunmadim. Masalan: 'x^2-5x+6=0' yoki 'hosila x^3' deb yozing.",
    "Buni to'liq tushunolmadim. Tepadagi \"Amallar\" tugmasidan namunalarni ko'rib, shunga o'xshab yozib ko'ring.",
]
FOLLOWUP_JAVOBLARI = [
    "Yana biror narsa kerakmi?",
    "Boshqa misol ham yechaylikmi?",
    "Davom etamizmi?",
    "Yana savolingiz bormi?",
]
def natija_matni(turi, qiymat):
    if turi == "xato":
        return random.choice(XATO_JAVOBLARI), "xato"
    if turi == "hisob_taqribiy":
        v, v2 = qiymat
        shablon = random.choice(["Natija: {v} \u2248 {v2}", "Hisoblasam: {v} \u2248 {v2} chiqadi"])
        return shablon.format(v=v, v2=v2), "natija"
    shablon = random.choice(NATIJA_SHABLONLARI.get(turi, ["Natija: {v}"]))
    return shablon.format(v=qiymat), "natija"

SALOM_JAVOBLARI = [
    "Salom! Qanday yordam bera olaman? Menga tenglama yoki ifoda yozishingiz mumkin \U0001f642",
    "Assalomu alaykum! Xush kelibsiz. Qaysi masalani yechamiz?",
    "Salom-salom! Tayyorman \u2014 nima ustida ishlaymiz?",
]
XAYR_JAVOBLARI = [
    "Xayr! Yana kerak bo'lsa, bemalol murojaat qiling \U0001f44b",
    "Ko'rishguncha! Omad tilayman.",
    "Xayr, yaxshi qoling! Savol tug'ilsa, kutib qolaman.",
]
RAHMAT_JAVOBLARI = [
    "Arzimaydi! Yana savolingiz bo'lsa, yozavering.",
    "Xizmatingizga tayyorman, yana so'rang \U0001f642",
    "Marhamat! Boshqa narsa kerak bo'lsa, aytavering.",
]
ISM_JAVOBLARI = [
    "Men Axiomman \u2014 matematik masalalar bo'yicha yordam beradigan yordamchiman. Tenglama, hosila, integral, limit, matritsa va tenglamalar tizimini yecha olaman.",
    "Ismim Axiom. Vazifam \u2014 matematik hisob-kitoblarda sizga yordam berish.",
]
KAYFIYAT_JAVOBLARI = [
    "Rahmat, yaxshiman! Siz-chi? Qaysi masalani birga yechamiz?",
    "Zo'rman, ishlashga tayyorman \U0001f642 Sizda qanday masala bor?",
]
QOBILIYAT_JAVOBLARI = [
    "Men quyidagilarni qila olaman: tenglama yechish, hosila va integral olish, limit hisoblash, matritsa bilan ishlash (determinant, teskari matritsa) va tenglamalar tizimini yechish. Namunalarni tepadagi \"Amallar\" tugmasidan ko'rishingiz mumkin.",
]
MAQTOV_JAVOBLARI = [
    "Rahmat, bu meni xursand qiladi \U0001f642 Yana qaysi masalani yechamiz?",
    "Mehringiz uchun rahmat! Davom etamizmi?",
]
KECHIRIM_JAVOBLARI = [
    "Hechqisi yo'q, davom etaveraylik \U0001f642",
    "Muammo emas! Boshqa savolingiz bormi?",
]
YOSH_JAVOBLARI = [
    "Aniq yoshim yo'q \u2014 men kodlarda yashayman \U0001f604 Lekin matematikada tajribam katta!",
    "Yoshni hisoblashdan ko'ra, keling biror tenglamani hisoblaylik \U0001f642",
]
INSON_JAVOBLARI = [
    "Yo'q, men odam emasman \u2014 matematik yordamchi dasturman. Lekin sizga chinakamiga yordam berishga harakat qilaman \U0001f642",
    "Men dasturman, lekin his-tuyg'u bilan yozishga harakat qilaman \U0001f642",
]
ZERIKISH_JAVOBLARI = [
    "Unda keling, qiziqarli bir tenglama bilan shug'ullanaylik \u2014 zerikish o'tib ketadi \U0001f642",
    "Biror qiziq masala yechaylikmi? Bu zerikishni unutishga yordam beradi.",
]
YARATUVCHI_JAVOBLARI = [
    "Meni Sarvar Karimov yaratgan \U0001f642",
    "Yaratuvchim \u2014 Sarvar Karimov.",
    "Men Sarvar Karimov tomonidan yasalganman.",
]
def soz_bormi(royxat, matn):
    for s in royxat:
        if len(s) <= 3:
            if re.search(r"\b" + re.escape(s) + r"\b", matn):
                return True
        elif s in matn:
            return True
    return False

def guruh_mos(matn, guruhlar):
    # guruhlar: guruhlar ro'yxati, masalan [["yarat","yoz"], ["kim","sen"]].
    # Har bir guruhdan KAMIDA BITTA so'z topilishi kerak (guruhlar orasida VA,
    # guruh ichida YOKI). So'zlar tartibidan qat'i nazar ishlaydi.
    for guruh in guruhlar:
        if not any(s in matn for s in guruh):
            return False
    return True

def javob_top(matn):
    global foydalanuvchi_ismi
    kichik = matn.lower().strip()

    qisqa = qisqa_javob(matn)
    if qisqa is not None:
        return qisqa, "suhbat"

    if re.search(r"\bek(ub|uk)\w*", kichik):
        return ekub_ekuk_javob(kichik)
    ajr = ajrat_och_javob(kichik)
    if ajr is not None:
        return ajr
    for _yordamchi in (sanoq_javob, birlik_javob, geometriya_javob, foiz_javob, kasr_javob):
        _r = _yordamchi(kichik)
        if _r is not None:
            return _r

    ism_moslik = re.search(r"(mening ismim|ismim|men)\s+([a-zA-Z\u0400-\u04FFʻʼ'`]+)\s*(man|dir|\b)", kichik)
    if ism_moslik and ("ism" in kichik):
        topilgan_ism = ism_moslik.group(2).capitalize()
        foydalanuvchi_ismi = topilgan_ism
        return f"Tanishganimdan xursandman, {topilgan_ism}! Qaysi masalani birga yechamiz?", "suhbat"

    salomlar = ["salom", "assalomu alaykum", "hi", "hello", "hey"]
    xayr = ["xayr", "hayr", "bye", "koreshguncha", "ko'rishguncha"]
    rahmat = ["rahmat", "tashakkur", "minnatdorman"]
    kayfiyat = ["qalaysan", "qanaqasan", "ishlaring qalay", "kayfiyating qanday", "yahshimisan", "qalaysiz", "qanaqasiz"]
    maqtov = ["zo'rsan", "ajoyibsan", "rahmat zo'r", "yaxshi ishlading", "zor ekansan", "super"]
    kechirim = ["kechirasiz", "uzr", "xato qildim", "noto'g'ri yozdim"]
    yosh_savol = ["necha yoshdasan", "yoshing necha", "necha yoshsan"]
    inson_savol = ["sen odammisan", "sen robotmisan", "haqiqiy odammisan"]
    zerikish = ["zerikdim", "charchadim", "zerikarli"]

    # Quyidagilar so'z tartibidan qat'i nazar ishlaydi (guruh_mos):
    yaratuvchi_mos = guruh_mos(kichik, [["yarat", "yoz", "dastur", "muallif", "yasa"], ["kim", "sen"]])
    ism_mos = ("ism" in kichik) or ("kimsan" in kichik) or ("nima bu axiom" in kichik) \
        or ("o'zing haqingda" in kichik) or guruh_mos(kichik, [["kim"], ["sen", "o'zing"]])
    qobiliyat_mos = ("imkoniyat" in kichik) or guruh_mos(
        kichik, [["qila", "qodir", "ber"], ["nima", "qanday", "nimalar"]])

    if soz_bormi(salomlar, kichik):
        return ism_bilan(SALOM_JAVOBLARI), "suhbat"
    elif soz_bormi(xayr, kichik):
        return ism_bilan(XAYR_JAVOBLARI), "suhbat"
    elif soz_bormi(rahmat, kichik):
        return ism_bilan(RAHMAT_JAVOBLARI), "suhbat"
    elif yaratuvchi_mos:
        return random.choice(YARATUVCHI_JAVOBLARI), "suhbat"
    elif ism_mos:
        return random.choice(ISM_JAVOBLARI), "suhbat"
    elif soz_bormi(kayfiyat, kichik):
        return random.choice(KAYFIYAT_JAVOBLARI), "suhbat"
    elif qobiliyat_mos:
        return random.choice(QOBILIYAT_JAVOBLARI), "suhbat"
    elif soz_bormi(maqtov, kichik):
        return ism_bilan(MAQTOV_JAVOBLARI), "suhbat"
    elif soz_bormi(kechirim, kichik):
        return random.choice(KECHIRIM_JAVOBLARI), "suhbat"
    elif soz_bormi(yosh_savol, kichik):
        return random.choice(YOSH_JAVOBLARI), "suhbat"
    elif soz_bormi(inson_savol, kichik):
        return random.choice(INSON_JAVOBLARI), "suhbat"
    elif soz_bormi(zerikish, kichik):
        return random.choice(ZERIKISH_JAVOBLARI), "suhbat"
    elif matematik_savolmi(kichik):
        d_xato = re.search(r"(?<![a-z\d.])[xy]\d", kichik)
        if d_xato and "tizim" not in kichik:
            t = re.sub(r"(?<![a-z\d])([xy])(\d+)", r"\1^\2", kichik)
            tok = d_xato.group()
            return f"'{tok}' ko'rinishida yozilgan, daraja uchun ^ belgisi ishlatiladi. Buni nazarda tutdingizmi: \u00ab{t}\u00bb?", "xato"
        turi, qiymat = matematikani_yech(kichik)
        if turi == "xato":
            taklif = taklif_top(kichik)
            if taklif:
                return f"Tushunmadim, lekin buni nazarda tutdingizmi: \u00ab{taklif}\u00bb? Shunday yozib ko'ring.", "xato"
        return natija_matni(turi, qiymat)
    else:
        return random.choice(XATO_JAVOBLARI), "xato"

yuborilgan = []
yuborilgan_indeks = 0
TONG_SALOM = [
    "Xayrli tong! Bugun qanday misol yechamiz?",
    "Xayrli tong! Tayyorman, nimadan boshlaymiz?",
]
KUN_SALOM = [
    "Salom! Bugun qanday masalalar bor?",
    "Kun yaxshi o'tyaptimi? Keling, bir narsa yechamiz.",
    "Assalomu alaykum! Bugun qaysi mavzuni ko'ramiz?",
]
KECH_SALOM = [
    "Xayrli kech! Bugungi oxirgi masalani yechaylikmi?",
    "Kech bo'ldi, lekin matematika hech qachon tugamaydi \U0001f642",
]
TUN_SALOM = [
    "Tungi mashqlarga tayyormisiz? Nima yechamiz?",
    "Kech bo'lgan payt ham matematika uchun yaxshi vaqt \U0001f642",
]
MAVZU_KALITLAR = ["FON", "PANEL", "MATN", "KOK", "YASHIL", "SARIQ", "PEMBE", "QIZIL", "FIROZA",
                  "TOQ_KUL", "TOQ_KUL_HOVER", "KULRANG_MATN", "GRAD_TOP", "GRAD_BOTTOM",
                  "SIZ_FON", "AXIOM_FON", "PLOT_FON", "PLOT_TOR", "PLOT_OQ"]
joriy_mavzu = "qorong'u"
RANG_OPSIYALAR = ("bg", "fg", "activebackground", "activeforeground", "insertbackground",
                  "selectbackground", "selectforeground", "highlightbackground", "highlightcolor",
                  "disabledforeground")

# ====================== VEB-ILOVA UCHUN API ======================
def grafik_tayyorla(ifodalar, a, b):
    """Grafik chiziqlarini ma'lumot koordinatalarida tayyorlaydi (chizishni JavaScript qiladi)."""
    egri, past, yuqori = grafik_malumot(ifodalar, a, b)
    chiziqlar = []
    for nuqtalar in egri:
        segmentlar, cur, old = [], [], None
        for xv, yv in nuqtalar:
            if yv is None:
                if len(cur) >= 2:
                    segmentlar.append(cur)
                cur, old = [], None
                continue
            if old is not None:
                x0, y0 = old
                if y0 * yv < 0 and abs(yv - y0) > 1.5 * (yuqori - past):
                    if len(cur) >= 2:
                        segmentlar.append(cur)
                    cur = []
                else:
                    kesma = grafik_kes(x0, y0, xv, yv, past, yuqori)
                    if kesma is None:
                        if len(cur) >= 2:
                            segmentlar.append(cur)
                        cur = []
                    else:
                        sx0, sy0, sx1, sy1, t0, t1 = kesma
                        if not cur:
                            cur.append([sx0, sy0])
                        cur.append([sx1, sy1])
                        if t1 < 1.0:
                            if len(cur) >= 2:
                                segmentlar.append(cur)
                            cur = []
            old = (xv, yv)
        if len(cur) >= 2:
            segmentlar.append(cur)
        chiziqlar.append(segmentlar)
    return {
        "a": a, "b": b, "past": past, "yuqori": yuqori,
        "xt": [[t, grafik_son(t)] for t in grafik_belgilar(a, b)],
        "yt": [[t, grafik_son(t)] for t in grafik_belgilar(past, yuqori)],
        "chiziqlar": chiziqlar,
        "nomlar": ["y = " + chiroyli(m, True) for m in ifodalar],
    }

def javob_ber(matn):
    """Foydalanuvchi xabariga javob: xabarlar ro'yxatini JSON qilib qaytaradi.
    Har xabar: {tur, matn} yoki {tur, matn, grafik}. 'keyin': True bo'lsa biroz kechikib chiqadi."""
    xabarlar = []
    matn = kirishni_normallashtir(matn.strip())
    matn, tuzatishlar = matnni_tuzat(matn)
    if tuzatishlar:
        xabarlar.append({"tur": "suhbat", "matn": "Yozuvingizni to'g'riladim: " + ", ".join(f"\u00ab{a}\u00bb \u2192 \u00ab{b}\u00bb" for a, b in tuzatishlar)})
    if bosqich_soraldimi(matn):
        javob, tur = bosqichlarni_top(matn)
        xabarlar.append({"tur": tur, "matn": chiroyli(javob, tur == "natija")})
        return json.dumps(xabarlar)
    grafik = grafik_ajrat(matn)
    if grafik is not None:
        ifodalar, ga, gb = grafik
        if not ifodalar:
            xabarlar.append({"tur": "suhbat", "matn": "Qaysi funksiyaning grafigini chizay? Masalan: grafik x^2"})
        else:
            try:
                g = grafik_tayyorla(ifodalar, ga, gb)
                xabarlar.append({"tur": "suhbat", "matn": "Mana grafik:", "grafik": g})
            except Exception:
                xabarlar.append({"tur": "xato", "matn": "Bu funksiyani chiza olmadim. Faqat x ishlatilgan funksiyani yozing, masalan: grafik x^2 yoki grafik sin(x); cos(x)"})
        return json.dumps(xabarlar)
    javob, tur = javob_top(matn)
    xabarlar.append({"tur": tur, "matn": chiroyli(javob, tur == "natija")})
    if tur == "natija" and random.random() < 0.35:
        xabarlar.append({"tur": "suhbat", "matn": random.choice(FOLLOWUP_JAVOBLARI), "keyin": True})
    return json.dumps(xabarlar)

def salom_ber(soat):
    if 5 <= soat < 11:
        pool = TONG_SALOM
    elif 11 <= soat < 17:
        pool = KUN_SALOM
    elif 17 <= soat < 22:
        pool = KECH_SALOM
    else:
        pool = TUN_SALOM
    return random.choice(pool)

def malumot_ber():
    return json.dumps({"qollanma": QOLLANMA, "imkoniyatlar": IMKONIYATLAR, "haqida": DASTUR_HAQIDA, "versiya": VERSIYA})
