
import json
from decimal import Decimal, InvalidOperation
from functools import wraps
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.db import transaction
from django.db.models import F, Sum, ExpressionWrapper, DecimalField
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .models import (
    Categoria,
    Producto,
    Pedido,
    ItemPedido,
    MovimientoInventario,
)
from .forms import ProductoForm, TrabajadorForm


User = get_user_model()

ROLE_NAMES = {
    "admin": "Administrador",
    "tienda": "Tienda",
    "trabajador": "Trabajador",
}

ROLE_SECTIONS = {
    "admin": [
        "Resumen", "Productos", "Ventas", "Pedidos",
        "Inventario", "Trabajadores", "Reportes",
    ],
    "tienda": [
        "Resumen", "Catálogo", "Ventas", "Pedidos", "Inventario",
    ],
    "trabajador": [
        "Resumen", "Catálogo", "Pedidos",
    ],
}


# ============================================================
# ROLES Y PERMISOS
# ============================================================

def get_user_role(user):
    if not user.is_authenticated:
        return None

    if user.is_superuser:
        return "admin"

    groups = set(user.groups.values_list("name", flat=True))

    if groups.intersection({"Administrador", "admin"}):
        return "admin"

    if groups.intersection({"Tienda", "tienda"}):
        return "tienda"

    if groups.intersection({"Trabajador", "trabajador"}):
        return "trabajador"

    return None


def role_required(*allowed_roles):
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            if get_user_role(request.user) not in allowed_roles:
                messages.error(
                    request,
                    "No tienes permisos para realizar esta operación.",
                )
                return redirect("sistema")

            return view_func(request, *args, **kwargs)

        return wrapper
    return decorator


def dashboard_redirect(request, section=None):
    section = (
        section
        or request.POST.get("seccion")
        or request.POST.get("section")
        or "Resumen"
    )

    role = get_user_role(request.user) if request.user.is_authenticated else None

    if role and section not in ROLE_SECTIONS[role]:
        section = "Resumen"

    url = reverse("sistema")
    return redirect(f"{url}?{urlencode({'section': section})}")


def safe_back_redirect(request):
    referer = request.META.get("HTTP_REFERER", "")

    if referer and url_has_allowed_host_and_scheme(
        referer,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(referer)

    return redirect("home")


def json_error(error, status=400):
    return JsonResponse({"ok": False, "error": error}, status=status)


# ============================================================
# TIENDA PÚBLICA
# ============================================================

def home(request):
    productos = Producto.objects.select_related(
        "categoria"
    ).order_by("categoria__nombre", "nombre")

    categorias = Categoria.objects.all().order_by("nombre")

    return render(
        request,
        "catalogo.html",
        {
            "productos": productos,
            "categorias": categorias,
        },
    )


# ============================================================
# AUTENTICACIÓN
# ============================================================

def role_login(request):
    if request.user.is_authenticated:
        if get_user_role(request.user):
            return redirect("sistema")
        logout(request)

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        user = authenticate(
            request,
            username=username,
            password=password,
        )

        if user is not None:
            if not get_user_role(user):
                messages.error(
                    request,
                    "Este usuario no tiene un rol asignado.",
                )
                return redirect("role_login")

            login(request, user)
            return redirect("sistema")

        messages.error(request, "Usuario o contraseña incorrectos.")

    return render(request, "acceso.html")


@login_required
@require_POST
def role_logout(request):
    logout(request)
    return redirect("home")


# ============================================================
# PANEL ADMINISTRATIVO
# ============================================================

@login_required
def sistema(request):
    role = get_user_role(request.user)

    if not role:
        logout(request)
        messages.error(request, "Tu usuario no tiene un rol válido.")
        return redirect("role_login")

    sections = ROLE_SECTIONS[role]

    section = request.GET.get(
        "section",
        request.GET.get("seccion", "Resumen"),
    )

    if section not in sections:
        section = "Resumen"

    products = Producto.objects.select_related(
        "categoria"
    ).order_by("categoria__nombre", "nombre")

    orders = Pedido.objects.prefetch_related(
        "items__producto"
    ).order_by("-creado")

    workers = User.objects.filter(
        groups__name__in=[
            "Trabajador", "trabajador", "Tienda", "tienda",
        ]
    ).distinct().order_by("username")

    movements = MovimientoInventario.objects.select_related(
        "producto", "usuario", "pedido",
    ).order_by("-creado")

    today = timezone.localdate()

    products_count = products.count()
    stock_count = products.aggregate(
        total=Sum("stock")
    )["total"] or 0

    workers_count = workers.count()
    orders_count = orders.count()

    active_orders_count = orders.exclude(
        estado__in=[
            Pedido.Estado.ENTREGADO,
            Pedido.Estado.CANCELADO,
        ]
    ).count()

    pending_payment_count = orders.filter(
        pagado=False
    ).exclude(
        estado=Pedido.Estado.CANCELADO
    ).count()

    sales_today = (
        orders.filter(
            creado__date=today,
            pagado=True,
        )
        .exclude(estado=Pedido.Estado.CANCELADO)
        .aggregate(total=Sum("total"))["total"]
        or Decimal("0.00")
    )

    top_products = (
        ItemPedido.objects
        .filter(pedido__pagado=True)
        .exclude(pedido__estado=Pedido.Estado.CANCELADO)
        .values("producto__nombre")
        .annotate(
            unidades=Sum("cantidad"),
            ingresos=Sum(
                ExpressionWrapper(
                    F("precio") * F("cantidad"),
                    output_field=DecimalField(
                        max_digits=12,
                        decimal_places=2,
                    ),
                )
            ),
        )
        .order_by("-unidades")[:10]
    )

    recent_orders = orders[:10]
    available_products = products.filter(stock__gt=0)

    product_rows = [
        {
            "producto": producto,
            "form": ProductoForm(instance=producto),
        }
        for producto in products
    ]

    monthly_orders = (
        orders.filter(
            creado__year=today.year,
            creado__month=today.month,
            pagado=True,
        )
        .exclude(estado=Pedido.Estado.CANCELADO)
    )

    monthly_total = (
        monthly_orders.aggregate(total=Sum("total"))["total"]
        or Decimal("0.00")
    )

    context = {
        "role": role,
        "role_name": ROLE_NAMES[role],
        "sections": sections,
        "section": section,
        "products": products,
        "product_rows": product_rows,
        "product_form": ProductoForm(),
        "available_products": available_products,
        "orders": orders,
        "orders_display": orders,
        "recent_orders": recent_orders,
        "estados_pedido": Pedido.Estado.choices,
        "workers": workers,
        "worker_form": TrabajadorForm(),
        "movements": movements,
        "products_count": products_count,
        "stock_count": stock_count,
        "workers_count": workers_count,
        "orders_count": orders_count,
        "active_orders_count": active_orders_count,
        "pending_payment_count": pending_payment_count,
        "sales_today": sales_today,
        "top_products": top_products,
        "monthly_orders": monthly_orders,
        "monthly_total": monthly_total,
    }

    return render(request, "sistema.html", context)


# ============================================================
# ACCIONES DEL PANEL
# ============================================================

@login_required
@require_POST
def system_action(request):
    role = get_user_role(request.user)
    action = request.POST.get("action", "").strip()

    if not role:
        logout(request)
        return redirect("role_login")

    if action == "crear_producto":
        if role != "admin":
            messages.error(request, "Solo el administrador puede crear productos.")
            return dashboard_redirect(request, "Productos")

        form = ProductoForm(request.POST, request.FILES)

        if not form.is_valid():
            messages.error(request, "Revisa los datos del producto.")
            return dashboard_redirect(request, "Productos")

        try:
            with transaction.atomic():
                producto = form.save()

                if producto.stock > 0:
                    MovimientoInventario.objects.create(
                        producto=producto,
                        tipo=MovimientoInventario.Tipo.INGRESO,
                        cantidad=producto.stock,
                        stock_anterior=0,
                        stock_nuevo=producto.stock,
                        usuario=request.user,
                    )

            messages.success(request, f"Producto {producto.nombre} creado correctamente.")
        except Exception:
            messages.error(request, "No se pudo guardar el producto.")

        return dashboard_redirect(request, "Productos")

    if action == "actualizar_producto":
        if role != "admin":
            messages.error(request, "Solo el administrador puede editar productos.")
            return dashboard_redirect(request, "Productos")

        try:
            with transaction.atomic():
                producto = get_object_or_404(
                    Producto.objects.select_for_update(),
                    pk=request.POST.get("producto_id"),
                )

                stock_anterior = producto.stock

                form = ProductoForm(
                    request.POST,
                    request.FILES,
                    instance=producto,
                )

                if not form.is_valid():
                    messages.error(request, "Revisa los datos del producto.")
                    return dashboard_redirect(request, "Productos")

                producto = form.save()

                if producto.stock != stock_anterior:
                    MovimientoInventario.objects.create(
                        producto=producto,
                        tipo=MovimientoInventario.Tipo.AJUSTE,
                        cantidad=producto.stock - stock_anterior,
                        stock_anterior=stock_anterior,
                        stock_nuevo=producto.stock,
                        usuario=request.user,
                    )

            messages.success(request, "Producto actualizado correctamente.")

        except Exception:
            messages.error(request, "No se pudo actualizar el producto.")

        return dashboard_redirect(request, "Productos")

    if action == "crear_usuario":
        if role != "admin":
            messages.error(request, "Solo el administrador puede crear usuarios.")
            return dashboard_redirect(request, "Trabajadores")

        form = TrabajadorForm(request.POST)

        if not form.is_valid():
            messages.error(request, "Revisa los datos del usuario.")
            return dashboard_redirect(request, "Trabajadores")

        try:
            with transaction.atomic():
                user = form.save()
                selected_role = form.cleaned_data["rol"]

                group, _ = Group.objects.get_or_create(name=selected_role)
                user.groups.add(group)

            messages.success(request, f"Usuario {user.username} creado correctamente.")

        except Exception:
            messages.error(request, "No se pudo crear el usuario.")

        return dashboard_redirect(request, "Trabajadores")

    if action == "ajustar_stock":
        if role not in ("admin", "tienda"):
            messages.error(request, "No tienes permiso para modificar el inventario.")
            return dashboard_redirect(request, "Inventario")

        try:
            with transaction.atomic():
                producto = get_object_or_404(
                    Producto.objects.select_for_update(),
                    pk=request.POST.get("producto_id"),
                )

                anterior = producto.stock

                if request.POST.get("stock") not in (None, ""):
                    nuevo = int(request.POST["stock"])
                    cantidad = nuevo - anterior
                else:
                    cantidad = int(request.POST.get("cantidad", "0"))
                    nuevo = anterior + cantidad

                if nuevo < 0:
                    messages.error(request, "El stock no puede ser negativo.")
                    return dashboard_redirect(request, "Inventario")

                if nuevo == anterior:
                    messages.info(request, "El stock no presentó cambios.")
                    return dashboard_redirect(request, "Inventario")

                producto.stock = nuevo
                producto.save(update_fields=["stock"])

                MovimientoInventario.objects.create(
                    producto=producto,
                    tipo=MovimientoInventario.Tipo.AJUSTE,
                    cantidad=cantidad,
                    stock_anterior=anterior,
                    stock_nuevo=nuevo,
                    usuario=request.user,
                )

            messages.success(request, f"Inventario actualizado: {nuevo} unidades.")

        except (ValueError, TypeError):
            messages.error(request, "Ingresa una cantidad válida.")
        except Exception:
            messages.error(request, "No se pudo actualizar el inventario.")

        return dashboard_redirect(request, "Inventario")

    if action == "ingreso_stock":
        if role not in ("admin", "tienda"):
            messages.error(request, "No tienes permiso para registrar ingresos.")
            return dashboard_redirect(request, "Inventario")

        try:
            cantidad = int(request.POST.get("cantidad", "0"))

            if cantidad <= 0:
                messages.error(request, "La cantidad debe ser mayor que cero.")
                return dashboard_redirect(request, "Inventario")

            with transaction.atomic():
                producto = get_object_or_404(
                    Producto.objects.select_for_update(),
                    pk=request.POST.get("producto_id"),
                )

                anterior = producto.stock
                producto.stock += cantidad
                producto.save(update_fields=["stock"])

                MovimientoInventario.objects.create(
                    producto=producto,
                    tipo=MovimientoInventario.Tipo.INGRESO,
                    cantidad=cantidad,
                    stock_anterior=anterior,
                    stock_nuevo=producto.stock,
                    usuario=request.user,
                )

            messages.success(request, f"Ingreso registrado: {cantidad} unidades.")

        except (ValueError, TypeError):
            messages.error(request, "Ingresa una cantidad válida.")
        except Exception:
            messages.error(request, "No se pudo registrar el ingreso.")

        return dashboard_redirect(request, "Inventario")

    if action == "marcar_pagado":
        if role not in ("admin", "tienda"):
            messages.error(request, "No tienes permiso para registrar pagos.")
            return dashboard_redirect(request, "Pedidos")

        try:
            with transaction.atomic():
                pedido = get_object_or_404(
                    Pedido.objects.select_for_update(),
                    pk=request.POST.get("pedido_id"),
                )

                if pedido.estado == Pedido.Estado.CANCELADO:
                    messages.error(request, "No se puede cobrar un pedido cancelado.")
                elif pedido.pagado:
                    messages.info(request, "Este pedido ya figura como pagado.")
                else:
                    pedido.pagado = True
                    pedido.save(update_fields=["pagado"])
                    messages.success(request, f"Pedido #{pedido.pk} marcado como pagado.")

        except Exception:
            messages.error(request, "No se pudo actualizar el pago.")

        return dashboard_redirect(request, "Pedidos")

    if action == "estado_pedido":
        if role not in ("admin", "tienda"):
            messages.error(request, "No tienes permiso para gestionar pedidos.")
            return dashboard_redirect(request, "Pedidos")

        try:
            with transaction.atomic():
                pedido = get_object_or_404(
                    Pedido.objects.select_for_update(),
                    pk=request.POST.get("pedido_id"),
                )

                nuevo_estado = request.POST.get("estado", "")
                estados_validos = dict(Pedido.Estado.choices)

                if nuevo_estado not in estados_validos:
                    messages.error(request, "El estado seleccionado no es válido.")
                    return dashboard_redirect(request, "Pedidos")

                if pedido.estado == Pedido.Estado.CANCELADO:
                    messages.error(request, "Este pedido ya está cancelado.")
                    return dashboard_redirect(request, "Pedidos")

                if pedido.estado == Pedido.Estado.ENTREGADO:
                    messages.error(request, "Un pedido entregado no puede cambiar de estado.")
                    return dashboard_redirect(request, "Pedidos")

                if nuevo_estado == pedido.estado:
                    messages.info(request, "El pedido ya tiene ese estado.")
                    return dashboard_redirect(request, "Pedidos")

                if nuevo_estado == Pedido.Estado.CANCELADO:
                    items = list(pedido.items.all().order_by("producto_id"))
                    producto_ids = sorted({item.producto_id for item in items})

                    productos_bloqueados = {
                        producto.pk: producto
                        for producto in Producto.objects.select_for_update()
                        .filter(pk__in=producto_ids)
                        .order_by("pk")
                    }

                    for item in items:
                        producto = productos_bloqueados.get(item.producto_id)

                        if producto is None:
                            raise ValueError("No se encontró un producto del pedido.")

                        anterior = producto.stock
                        producto.stock += item.cantidad
                        producto.save(update_fields=["stock"])

                        MovimientoInventario.objects.create(
                            producto=producto,
                            tipo=MovimientoInventario.Tipo.DEVOLUCION,
                            cantidad=item.cantidad,
                            stock_anterior=anterior,
                            stock_nuevo=producto.stock,
                            usuario=request.user,
                            pedido=pedido,
                        )

                pedido.estado = nuevo_estado
                pedido.save(update_fields=["estado"])

            messages.success(
                request,
                f"Pedido #{pedido.pk}: {estados_validos[nuevo_estado]}.",
            )

            if nuevo_estado == Pedido.Estado.CANCELADO and pedido.pagado:
                messages.warning(
                    request,
                    "El inventario fue devuelto. Verifica por separado la devolución del pago.",
                )

        except (ValueError, TypeError):
            messages.error(request, "No se pudo cambiar el estado del pedido.")
        except Exception:
            messages.error(request, "Ocurrió un error al gestionar el pedido.")

        return dashboard_redirect(request, "Pedidos")

    messages.error(request, "La operación solicitada no existe.")
    return dashboard_redirect(request)


# ============================================================
# CARRITO
# ============================================================

def obtener_carrito(request):
    carrito = request.session.get("carrito", {})
    return carrito if isinstance(carrito, dict) else {}


def guardar_carrito(request, carrito):
    request.session["carrito"] = carrito
    request.session.modified = True


@require_POST
def agregar_al_carrito(request, producto_id):
    producto = get_object_or_404(Producto, pk=producto_id)
    carrito = obtener_carrito(request)
    key = str(producto.pk)

    try:
        cantidad = int(request.POST.get("cantidad", "1"))
    except (ValueError, TypeError):
        cantidad = 1

    cantidad = max(1, cantidad)

    if producto.stock <= 0:
        messages.error(request, "Este producto no tiene stock disponible.")
    else:
        try:
            actual = int(carrito.get(key, 0))
        except (ValueError, TypeError):
            actual = 0

        carrito[key] = min(actual + cantidad, producto.stock)
        guardar_carrito(request, carrito)

        if actual + cantidad > producto.stock:
            messages.warning(request, f"Solo hay {producto.stock} unidades disponibles.")
        else:
            messages.success(request, "Producto agregado al carrito.")

    return safe_back_redirect(request)


@require_POST
def actualizar_carrito(request, producto_id):
    producto = get_object_or_404(Producto, pk=producto_id)
    carrito = obtener_carrito(request)

    try:
        cantidad = int(request.POST.get("cantidad", "1"))
    except (ValueError, TypeError):
        cantidad = 1

    if cantidad <= 0 or producto.stock <= 0:
        carrito.pop(str(producto.pk), None)
    else:
        carrito[str(producto.pk)] = min(cantidad, producto.stock)

    guardar_carrito(request, carrito)
    return safe_back_redirect(request)


@require_POST
def eliminar_del_carrito(request, producto_id):
    carrito = obtener_carrito(request)
    carrito.pop(str(producto_id), None)
    guardar_carrito(request, carrito)
    return safe_back_redirect(request)


@require_POST
def limpiar_carrito(request):
    guardar_carrito(request, {})
    return safe_back_redirect(request)


# ============================================================
# PROCESAR PEDIDO
# ============================================================

@require_POST
@transaction.atomic
def procesar_pedido(request):
    try:
        datos = json.loads(request.body.decode("utf-8")) if request.body else {}
    except (json.JSONDecodeError, UnicodeDecodeError):
        return json_error("Los datos del pedido no son v?lidos.")

    nombre = str(datos.get("nombre", request.POST.get("nombre", ""))).strip()
    celular = str(datos.get("celular", request.POST.get("celular", ""))).strip()
    direccion = str(datos.get("direccion", request.POST.get("direccion", ""))).strip()
    distrito = str(datos.get("distrito", request.POST.get("distrito", ""))).strip()
    referencia = str(datos.get("referencia", request.POST.get("referencia", ""))).strip()

    def normalizar_opcion(opciones, valor):
        valor = str(valor or "").strip().casefold()
        

        # El cat?logo usa "Tarjeta de d?bito"; Django guarda "TARJETA".
        if valor in ("tarjeta de debito", "tarjeta de d?bito", "debito", "d?bito") and any(
            str(clave).strip().upper() == "TARJETA" for clave, _ in opciones
        ):
            return "TARJETA"

        for clave, etiqueta in opciones:
            if valor in (str(clave).strip().casefold(),
                         str(etiqueta).strip().casefold()):
                return clave
        return None

    forma_entrega = normalizar_opcion(
        Pedido.FORMAS_ENTREGA,
        datos.get("entrega", request.POST.get("entrega", "DELIVERY"))
    )
    metodo_pago = normalizar_opcion(
        Pedido.METODOS_PAGO,
        datos.get("pago", request.POST.get("pago", "EFECTIVO"))
    )

    if not nombre or not celular:
        return json_error("Completa tu nombre y celular.")

    if len(nombre) > 120 or len(celular) > 20:
        return json_error("El nombre o celular supera la longitud permitida.")

    if len(direccion) > 255 or len(distrito) > 100:
        return json_error("La direcci?n o distrito supera la longitud permitida.")

    if forma_entrega is None:
        return json_error("La forma de entrega no es v?lida.")

    if metodo_pago is None:
        return json_error("El m?todo de pago no es v?lido.")

    if "delivery" in str(forma_entrega).casefold() and not direccion:
        return json_error("Ingresa la direcci?n de entrega.")

    items_json = datos.get("items")
    lineas = []

    if isinstance(items_json, list):
        if not items_json:
            return json_error("El carrito est? vac?o.")

        for item in items_json:
            if not isinstance(item, dict):
                return json_error("Hay productos inv?lidos en el carrito.")

            nombre_producto = str(item.get("nombre", "")).strip()

            try:
                cantidad = int(item.get("cantidad", 0))
                precio = Decimal(str(item.get("precio", "0")))
            except (ValueError, TypeError, InvalidOperation):
                return json_error("Hay cantidades o precios inv?lidos.")

            if not nombre_producto or cantidad < 1 or cantidad > 99:
                return json_error("Revisa los productos y sus cantidades.")

            if len(nombre_producto) > 100:
                return json_error("El nombre de un producto es demasiado largo.")

            if not precio.is_finite() or precio <= 0:
                return json_error("Hay un producto con precio inv?lido.")

            lineas.append({
                "nombre": nombre_producto,
                "cantidad": cantidad,
                "precio": precio,
                "producto_id": None
            })

    else:
        carrito = obtener_carrito(request)

        if not carrito:
            return json_error("El carrito est? vac?o.")

        for key, value in carrito.items():
            try:
                producto_id = int(key)
                cantidad = int(value)
            except (ValueError, TypeError):
                return json_error("El carrito contiene datos inv?lidos.")

            if producto_id <= 0 or cantidad < 1:
                return json_error("El carrito contiene cantidades inv?lidas.")

            lineas.append({
                "producto_id": producto_id,
                "cantidad": cantidad,
                "precio": None,
                "nombre": None
            })

    try:
        with transaction.atomic():
            categoria, _ = Categoria.objects.get_or_create(
                nombre="Cat?logo web"
            )

            productos_pedido = []
            total = Decimal("0.00")

            for linea in lineas:
                if linea["producto_id"] is not None:
                    producto = (
                        Producto.objects.select_for_update()
                        .filter(pk=linea["producto_id"])
                        .first()
                    )

                    if producto is None:
                        return json_error("Uno de los productos ya no existe.")

                else:
                    coincidencias = Producto.objects.filter(
                        nombre__iexact=linea["nombre"]
                    ).order_by("pk")

                    if coincidencias.count() > 1:
                        return json_error(
                            f"El producto '{linea['nombre']}' est? duplicado."
                        )

                    producto = coincidencias.first()

                    if producto is None:
                        producto = Producto.objects.create(
                            categoria=categoria,
                            nombre=linea["nombre"],
                            precio=linea["precio"],
                            stock=0,
                            volumen_ml=1,
                            porcentaje_alcohol=Decimal("0.00"),
                            pais_origen="Per?",
                            descripcion="Registrado desde el cat?logo web."
                        )

                precio_final = producto.precio

                if precio_final is None or precio_final <= 0:
                    return json_error(
                        f"El precio de {producto.nombre} no es v?lido."
                    )

                cantidad = linea["cantidad"]
                subtotal = precio_final * cantidad
                total += subtotal

                productos_pedido.append({
                    "producto": producto,
                    "cantidad": cantidad,
                    "precio": precio_final
                })

            pedido = Pedido.objects.create(
                nombre_cliente=nombre,
                celular=celular,
                direccion=direccion,
                distrito=distrito,
                forma_entrega=forma_entrega,
                referencia=referencia,
                metodo_pago=metodo_pago,
                total=total,
                pagado=False,
                estado=Pedido.Estado.RECIBIDO
            )

            items_respuesta = []

            for item in productos_pedido:
                ItemPedido.objects.create(
                    pedido=pedido,
                    producto=item["producto"],
                    cantidad=item["cantidad"],
                    precio=item["precio"]
                )

                items_respuesta.append({
                    "nombre": item["producto"].nombre,
                    "cantidad": item["cantidad"],
                    "precio": str(item["precio"])
                })

            request.session["carrito"] = {}
            request.session.modified = True

            return JsonResponse({
                "ok": True,
                "id": pedido.pk,
                "pedido_id": pedido.pk,
                "nombre": pedido.nombre_cliente,
                "total": str(total),
                "items": items_respuesta,
                "mensaje": "Pedido recibido y pendiente de confirmar disponibilidad."
            })

    except Exception as e:
        return json_error(f"No se pudo registrar el pedido: {str(e)}")

