# Libido y Tentación

Tienda de licores con catálogo, carrito, pedidos, inventario y panel por roles
(Administrador, Tienda, Trabajador). Hecho con Django.

## Iniciar en local (Windows)

    powershell -ExecutionPolicy Bypass -File .\iniciar.ps1

La primera vez crea el entorno virtual e instala las dependencias.
Tienda: http://127.0.0.1:8000/  |  Panel: http://127.0.0.1:8000/acceso/

## Primera instalación (base de datos nueva)

    python -m venv venv
    .\venv\Scripts\Activate.ps1
    pip install -r requirements.txt
    cd Licoreria
    python manage.py migrate
    python manage.py createsuperuser
    python conectar_pedidos.py
    python manage.py runserver

`conectar_pedidos.py` carga los productos iniciales (stock 50). Se puede repetir sin duplicar.

## Roles
- Administrador: control total.
- Tienda: operaciones y ventas (pedidos, pagos, inventario).
- Trabajador: catálogo y consulta de pedidos.

## Datos que NO están en el repositorio
La base de datos (db.sqlite3), las imágenes subidas (media/) y los secretos (.env).
Respaldo opcional:

    python manage.py dumpdata ventas auth.user auth.group --indent 2 -o respaldo.json
    python manage.py loaddata respaldo.json

## Antes de publicar en internet
DEBUG = False, configurar ALLOWED_HOSTS, usar una SECRET_KEY nueva por variable de entorno,
y cambiar los datos de ejemplo (WhatsApp, Yape, Plin, dirección).
