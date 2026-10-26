// Axiom AI: Python (Pyodide) fon oqimida ishlaydi, shunda hisoblash vaqtida ekran qotib qolmaydi.
const PYODIDE = "https://cdn.jsdelivr.net/pyodide/v0.26.4/full/";
importScripts(PYODIDE + "pyodide.js");

let core = null;

function holat(matn, foiz) {
  postMessage({ tur: "holat", matn: matn, foiz: foiz });
}

async function boshla() {
  try {
    holat("Python yuklanmoqda…", 10);
    const pyodide = await loadPyodide({ indexURL: PYODIDE });
    holat("Matematik kutubxona (SymPy) yuklanmoqda…", 40);
    await pyodide.loadPackage("sympy");
    holat("Axiom yadrosi yuklanmoqda…", 70);
    const resp = await fetch("axiom_core.py", { cache: "no-cache" });
    if (!resp.ok) throw new Error("axiom_core.py topilmadi");
    pyodide.FS.writeFile("axiom_core.py", await resp.text());
    holat("SymPy ishga tushmoqda (birinchi marta biroz vaqt oladi)…", 85);
    core = pyodide.pyimport("axiom_core");
    postMessage({ tur: "tayyor" });
  } catch (e) {
    postMessage({ tur: "boshlash_xatosi", matn: String(e && e.message ? e.message : e) });
  }
}

onmessage = function (ev) {
  const d = ev.data;
  if (!core) {
    postMessage({ tur: "javob", id: d.id, hato: "Axiom hali tayyor emas" });
    return;
  }
  try {
    let natija;
    if (d.op === "javob") natija = core.javob_ber(d.matn);
    else if (d.op === "salom") natija = core.salom_ber(d.soat);
    else if (d.op === "malumot") natija = core.malumot_ber();
    else throw new Error("noma'lum amal");
    postMessage({ tur: "javob", id: d.id, natija: natija });
  } catch (e) {
    postMessage({ tur: "javob", id: d.id, hato: String(e && e.message ? e.message : e) });
  }
};

boshla();
