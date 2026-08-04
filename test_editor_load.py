"""Test que verifica el fix del editor."""
import requests
from pathlib import Path

print("Verificando el fix del editor...")
print()

# HTML servido
r = requests.get("http://127.0.0.1:5050/editor", timeout=5)
html = r.text
print(f"Editor HTML: status={r.status_code}, size={len(html)} bytes")
checks_html = {
    "class='file-hidden' presente": 'class="file-hidden"' in html,
    "for='openInput' presente": 'for="openInput"' in html,
    "for='openInput2' presente": 'for="openInput2"' in html,
}
for name, ok in checks_html.items():
    print(f"  {'OK' if ok else 'FAIL'}  {name}")

# JS servido
js = requests.get("http://127.0.0.1:5050/static/js/editor.js", timeout=5).text
print(f"\nEditor JS: size={len(js)} bytes")
checks_js = {
    "openFile mejorada (toast Cargando)": "Cargando" in js and "Pdf Ninja.toast" in js,
    "Fallback click programático": "dom.openInput.click()" in js and "dom.openInput2.click()" in js,
    "Drop acepta .pdf en extension": "name.toLowerCase().endsWith('.pdf')" in js,
    "Toast en error": "No se pudo abrir el PDF" in js,
}
for name, ok in checks_js.items():
    print(f"  {'OK' if ok else 'FAIL'}  {name}")

# CSS servido
css = requests.get("http://127.0.0.1:5050/static/css/editor.css", timeout=5).text
print(f"\nEditor CSS: size={len(css)} bytes")
checks_css = {
    "Clase .file-hidden definida": ".file-hidden" in css,
}
for name, ok in checks_css.items():
    print(f"  {'OK' if ok else 'FAIL'}  {name}")

print()
print("Resumen: el bug del editor debería estar corregido.")
print("Para probarlo: abrir http://127.0.0.1:5050/editor y seleccionar un PDF.")
