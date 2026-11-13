"""
conectar_pedidos.py  -  pega "Confirmar pedido" con tu app `ventas`.
"""
import os, re, sys, shutil
from decimal import Decimal
from pathlib import Path

PRODUCTOS = [
    ('Intipalka Malbec', 'Vinos', 29.9, 'Per\u00fa \u00b7 Valle de Ica', 750),
    ('Santiago Queirolo Cabernet Sauvignon', 'Vinos', 34.9, 'Per\u00fa', 750),
    ('Tacama Selecci\u00f3n Especial Petit Verdot Tannat', 'Vinos', 46.99, 'Per\u00fa', 750),
    ('Tabernero Gran Tinto', 'Vinos', 23.9, 'Per\u00fa', 750),
    ('Casillero del Diablo Cabernet Sauvignon', 'Vinos', 23.0, 'Chile', 375),
    ('Marqu\u00e9s de Riscal Reserva', 'Vinos', 89.9, 'Espa\u00f1a \u00b7 Rioja', 750),
    ('Catena Zapata Malbec', 'Vinos', 399.0, 'Argentina', 750),
    ('El Enemigo Malbec', 'Vinos', 95.0, 'Argentina', 750),
    ('Navarro Correas Colecci\u00f3n Privada Malbec', 'Vinos', 45.0, 'Argentina', 750),
    ('Errazuriz Max Reserva Carmenere', 'Vinos', 79.9, 'Chile', 750),
    ('Intipalka Sauvignon Blanc', 'Vinos', 28.5, 'Per\u00fa \u00b7 Valle de Ica', 750),
    ('Tacama Blanco de Blancos', 'Vinos', 50.99, 'Per\u00fa', 750),
    ('Tabernero Gran Blanco Fina Reserva', 'Vinos', 17.5, 'Per\u00fa', 750),
    ('Casillero del Diablo Chardonnay', 'Vinos', 34.9, 'Chile', 750),
    ('Abad\u00eda de San Campio Albari\u00f1o', 'Vinos', 69.9, 'Espa\u00f1a', 750),
    ('Animal Org\u00e1nico Chardonnay', 'Vinos', 59.9, 'Argentina', 750),
    ('Amelia Chardonnay', 'Vinos', 89.9, 'Chile', 750),
    ('JP Chenet Delicious Medium Sweet', 'Vinos', 39.9, 'Francia', 750),
    ('Tacama Ros\u00e9 Semi Seco', 'Vinos', 24.0, 'Per\u00fa', 750),
    ('Riccadonna Asti', 'Vinos', 54.9, 'Italia', 750),
    ('Johnnie Walker Red Label', 'Licores', 99.0, 'Escocia', 750),
    ('Johnnie Walker Black Label', 'Licores', 169.0, 'Escocia', 750),
    ('Chivas Regal 12 a\u00f1os', 'Licores', 149.0, 'Escocia', 750),
    ('Ron Cartavio Black', 'Licores', 39.0, 'Per\u00fa', 750),
    ('Ron Flor de Ca\u00f1a 12 a\u00f1os', 'Licores', 129.0, 'Nicaragua', 750),
    ('Havana Club 7 a\u00f1os', 'Licores', 79.0, 'Cuba', 750),
    ('Absolut Vodka', 'Licores', 69.0, 'Suecia', 750),
    ('Beefeater London Dry Gin', 'Licores', 85.0, 'Inglaterra', 750),
    ('Tequila Jose Cuervo Especial', 'Licores', 79.0, 'M\u00e9xico', 750),
    ('Pisco Barsol Quebranta', 'Licores', 49.0, 'Per\u00fa', 750),
    ('Pisco Port\u00f3n Mosto Verde', 'Licores', 119.0, 'Per\u00fa', 750),
    ('Baileys Original', 'Licores', 89.0, 'Irlanda', 750),
    ('Mo\u00ebt & Chandon Imp\u00e9rial', 'Especiales', 289.0, 'Francia', 750),
    ('Veuve Clicquot Brut', 'Especiales', 329.0, 'Francia', 750),
    ('Chandon Brut', 'Especiales', 69.0, 'Argentina', 750),
    ('Mionetto Prosecco', 'Especiales', 59.0, 'Italia', 750),
    ('Hennessy VS', 'Especiales', 199.0, 'Francia', 750),
    ('R\u00e9my Martin VSOP', 'Especiales', 249.0, 'Francia', 750),
    ('Johnnie Walker Blue Label', 'Especiales', 749.0, 'Escocia', 750),
    ('The Macallan 12 a\u00f1os', 'Especiales', 489.0, 'Escocia', 750),
    ('Don Julio 70', 'Especiales', 399.0, 'M\u00e9xico', 750),
    ('Patr\u00f3n Silver', 'Especiales', 229.0, 'M\u00e9xico', 750),
    ('Blue Lagoon (Laguna Azul)', 'Licores y cremas', 28.0, '', 750),
    ('Mojito tradicional', 'Licores y cremas', 26.0, '', 750),
    ('Blackberry Collins', 'Licores y cremas', 30.0, '', 750),
    ("Jack Daniel's Old No. 7", 'Licores y cremas', 119.0, '', 750),
    ('Vermut Highball', 'Licores y cremas', 24.0, '', 750),
    ('Smoked Whiskey Sour', 'Licores y cremas', 32.0, '', 750),
    ('A\u00f1ejo Patron', 'Licores y cremas', 299.0, '', 750),
    ('Old Monk Rum', 'Licores y cremas', 69.0, '', 750),
    ('Ron Viejo de Caldas', 'Licores y cremas', 59.0, '', 750),
    ('Absolut Original', 'Destilados', 64.9, 'Suecia', 750),
    ('Jos\u00e9 Cuervo Especial', 'Destilados', 79.9, 'M\u00e9xico', 750),
    ('Corona', 'Cervezas', 6.5, 'M\u00e9xico', 330),
    ('Budweiser', 'Cervezas', 5.5, 'Estados Unidos', 330),
    ('Heineken', 'Cervezas', 7.0, 'Pa\u00edses Bajos', 330),
    ('Tres Cruces', 'Cervezas', 4.5, 'Per\u00fa', 330),
    ('Cusque\u00f1a', 'Cervezas', 5.5, 'Per\u00fa', 330),
]
PRECIO_UNICO = {'pisco port\u00f3n mosto verde': 119.0, 'johnnie walker black label': 169.0, 'havana club 7 a\u00f1os': 79.0, 'beefeater london dry gin': 85.0, 'ron cartavio black': 39.0}

if not Path("manage.py").exists():
    sys.exit("ERROR: Ejecuta esto en la carpeta donde est\u00e1 manage.py")
m = re.search(r'DJANGO_SETTINGS_MODULE["\'],\s*["\']([\w.]+)["\']', Path("manage.py").read_text())
os.environ["DJANGO_SETTINGS_MODULE"] = m.group(1)
sys.path.insert(0, os.getcwd())
import django
django.setup()
from ventas.models import Categoria, MovimientoInventario, Producto

# ---------------------------------------------------------------- 1. productos
campos = {f.name for f in Producto._meta.get_fields()}
creados = 0
for nombre, cat, precio, pais, ml in PRODUCTOS:
    if Producto.objects.filter(nombre__iexact=nombre).exists():
        continue
    c, _ = Categoria.objects.get_or_create(nombre=cat)
    datos = {"categoria": c, "nombre": nombre, "marca": "", "precio": Decimal(str(precio)), "stock": 50,
             "volumen_ml": ml, "porcentaje_alcohol": Decimal("0"), "pais_origen": pais,
             "descripcion": "", "es_pack": False}
    p = Producto.objects.create(**{k: v for k, v in datos.items() if k in campos})
    try:
        MovimientoInventario.objects.create(producto=p, tipo=MovimientoInventario.Tipo.INGRESO, cantidad=50,
                                            stock_anterior=0, stock_nuevo=50, usuario=None)
    except Exception as e:
        print("  (aviso: no se registro el movimiento de", nombre, "->", e, ")")
    creados += 1
print(f"OK: Productos: {creados} creados, {len(PRODUCTOS) - creados} ya existian. Total en tabla: {Producto.objects.count()}")

# ---------------------------------------------------------------- 2. plantilla
if len(sys.argv) > 1:
    candidatas = [Path(sys.argv[1])]
else:
    candidatas = [p for p in Path(".").rglob("*.html")
                  if not {"venv", ".venv", "node_modules", "site-packages"} & set(p.parts)
                  and "function placeOrder" in p.read_text(encoding="utf-8", errors="ignore")]
if len(candidatas) != 1:
    sys.exit("ERROR: Encontre %d plantillas con el carrito. Indica la correcta:  python conectar_pedidos.py ruta\\plantilla.html\n  %s"
             % (len(candidatas), "\n  ".join(map(str, candidatas))))
ruta = candidatas[0]
s = ruta.read_text(encoding="utf-8")
if "{% url 'procesar' %}" in s:
    sys.exit("OK: La plantilla %s ya estaba conectada." % ruta)
shutil.copy(ruta, str(ruta) + ".bak")

PEDIDO = """const btn = document.getElementById("coSubmit");
        btn.disabled = true;
        fetch("{% url 'procesar' %}", {
            method: "POST",
            headers: {"Content-Type": "application/json", "X-CSRFToken": "{{ csrf_token }}"},
            body: JSON.stringify({
                nombre: d.nombre, celular: d.celular, direccion: d.direccion, distrito: d.distrito,
                referencia: d.referencia, entrega: d.entrega,
                pago: (d.pago.indexOf("Tarjeta") === 0 ? "Tarjeta" : d.pago),
                items: order.items.map(function (i) { return {nombre: i.n, cantidad: i.q}; })
            })
        }).then(function (r) {
            return r.json().catch(function () { return {ok: false, error: "Sesi\u00f3n vencida o error del servidor. Recarga la p\u00e1gina (Ctrl+F5)."}; });
        }).then(function (r) {
            btn.disabled = false;
            if (!r || !r.ok) { alert((r && r.error) || "No se pudo registrar el pedido."); return; }
            order.num = "#" + (r.pedido_id || r.id);
            if (r.total) order.total = parseFloat(r.total);
            const inst = bootstrap.Modal.getInstance(coModalEl);
            if (inst) inst.hide();
            showSuccess(order);
            cart = [];
            saveCart();
            renderCart();
        }).catch(function () {
            btn.disabled = false;
            alert("Sin conexi\u00f3n con el servidor. Intenta de nuevo.");
        });"""
s, n = re.subn(r"const inst = bootstrap\.Modal\.getInstance\(coModalEl\);\s*if \(inst\) inst\.hide\(\);\s*showSuccess\(order\);\s*cart = \[\];\s*saveCart\(\);\s*renderCart\(\);",
               lambda _: PEDIDO, s, count=1)
if not n:
    sys.exit("ERROR: No reconoci la funcion placeOrder (ya la modificaste?). Pegame ese bloque y lo ajusto.")

fix = ("const PRECIO_UNICO = " + repr(PRECIO_UNICO).replace("'", '"') + ";\n"
       "    Object.keys(COL).forEach(function (k) { COL[k].items.forEach(function (w) {\n"
       "        const pu = PRECIO_UNICO[String(w.n).toLowerCase()]; if (pu !== undefined) w.p = pu; }); });\n\n    ")
if "const KEYS = Object.keys(COL);" in s:
    s = s.replace("const KEYS = Object.keys(COL);", fix + "const KEYS = Object.keys(COL);", 1)
ruta.write_text(s, encoding="utf-8")
print("OK: Plantilla conectada:", ruta, "(copia en .bak)")
print("\nListo. Reinicia el servidor, recarga con Ctrl+F5 y haz un pedido de prueba.")
