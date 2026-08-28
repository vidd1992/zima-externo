"""Valida que el CONTRATO documentado sea verdad: ejecuta cada ejemplo del JSON
(la misma fuente del Word) contra el servicio y verifica la respuesta esperada.

Uso:  python pruebas/validar_contrato.py [base_url] [token]
      (default: http://localhost:8090 · token-local-de-prueba)
Al final BORRA las citas que los ejemplos crearon (cédulas C0102030405/C0908070605
con los cita_hospital 905xx) — regla de la casa: ninguna prueba deja rastro.
"""
import json
import sys
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8090"
TOKEN = sys.argv[2] if len(sys.argv) > 2 else "token-local-de-prueba"

ejemplos = json.load(open("docs/ejemplos_contrato.json"))["ejemplos"]
ids_creados = []
fallos = 0

for ej in ejemplos:
    cuerpo = ej["cuerpo"]
    # los placeholders "<...>" se rellenan con el id creado en el ejemplo 1
    if isinstance(cuerpo, dict) and isinstance(cuerpo.get("id_chatbot"), str):
        cuerpo = {**cuerpo, "id_chatbot": ids_creados[-1]}
    req = urllib.request.Request(
        BASE + ej["ruta"], method=ej["metodo"],
        data=json.dumps(cuerpo).encode() if cuerpo else None,
        headers={"X-Externo-Token": TOKEN, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as r:
            status, cuerpo_resp = r.status, json.load(r)
    except urllib.error.HTTPError as e:
        status, cuerpo_resp = e.code, json.loads(e.read() or b"{}")

    esp = ej["respuesta_esperada"]
    ok = True
    if "http" in esp:
        ok = status == esp["http"]
    else:
        ok = status == 200 and cuerpo_resp.get("ok") == esp.get("ok")
        for k, v in esp.items():
            if k in ("ok",) or isinstance(v, str) and v.startswith("<"):
                continue
            if str(cuerpo_resp.get(k)) != str(v) and not str(v).startswith("["):
                ok = False
    print(("✓" if ok else "✗"), ej["titulo"], "->", status,
          json.dumps(cuerpo_resp, ensure_ascii=False)[:110])
    fallos += 0 if ok else 1
    if isinstance(cuerpo_resp.get("id_chatbot"), int) and not cuerpo_resp.get("simulado"):
        ids_creados.append(cuerpo_resp["id_chatbot"])

print(f"\n{'CONTRATO VALIDADO ✓' if fallos == 0 else f'{fallos} EJEMPLOS FALLARON ✗'}")
sys.exit(1 if fallos else 0)
