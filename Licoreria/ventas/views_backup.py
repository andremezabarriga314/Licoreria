from decimal import Decimal
from functools import wraps

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import F, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from .models import (
    Categoria,
    Producto,
    Pedido,
    ItemPedido,
    MovimientoInventario,
)


# ============================================================
# ROLES
# ============================================================

ROLE_NAMES = {
    "admin": "Administrador",
    "tienda": "Tienda",
    "trabajador": "Trabajador",
}


def get_user_role(user):
    """
    Determina el rol del usuario.

    Prioridad:
    1. superuser -> admin
    2. grupo Administrador
    3. grupo Tienda
    4. grupo Trabajador
    """

    if user.is_superuser:
        return "admin"

    groups = set(user.groups.values_list("name", flat=True))

    if "Administrador" in groups or "admin" in groups:
        return "admin"

    if "Tienda" in groups or "tienda" in groups:
        return "tienda"

    if "Trabajador" in groups or "trabajador" in groups:
        return "trabajador"

    return None


def role_required(*allowed_roles):
    """
    Protege una vista según el rol.
    """

    def decorator(view_func):

        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):

            role = get_user_role(request.user)

            if role not in allowed_roles:
                messages.error(
                    request,
                    "No tienes permisos para realizar esta operación."
                )
                return redirect("sistema")

            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator


# ============================================================
# INICIO / LOGIN
# ============================================================

def home(request):
    productos = Producto.objects.select_related("categoria").all()

    categorias = Categoria.objects.all()

    return render(
        request,
        "catalogo.html",
        {
            "productos": productos,
            "categorias": categorias,
        },
    )


def role_login(request):

    if request.user.is_authenticated:
        return redirect("sistema")

    if request.method == "POST":

        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        user = authenticate(
            request,
            username=username,
            password=password,
        )

        if user is not None:

            role = get_user_role(user)

            if not role:
                messages.error(
                    request,
                    "Este usuario no tiene un rol asignado."
                )
                return redirect("role_login")

            login(request, user)

            return redirect("sistema")

        messages.error(
            request,
            "Usuario o contraseña incorrectos."
        )

    return render(
        request,
        "acceso.html",
    )


@login_required
def role_logout(request):

    logout(request)

    return redirect("home")


# ============================================================
# DASHBOARD PRINCIPAL
# ============================================================

@login_required
def sistema(request):

    role = get_user_role(request.user)

    if not role:
        logout(request)
        return redirect("role_login")

    section = request.GET.get("section", "Resumen")

    # --------------------------------------------------------
    # PRODUCTOS
    # --------------------------------------------------------

    products = Producto.objects.select_related(
        "categoria"
    ).order_by(
        "categoria__nombre",
        "nombre",
    )

    # --------------------------------------------------------
    # PEDIDOS
    # --------------------------------------------------------

    orders = Pedido.objects.prefetch_related(
        "items__producto"
    ).order_by(
        "-creado"
    )

    # --------------------------------------------------------
    # TRABAJADORES
    # --------------------------------------------------------

    workers = User.objects.filter(
        groups__name="Trabajador"
    ).order_by(
        "username"
    )

    # --------------------------------------------------------
    # MOVIMIENTOS
    # --------------------------------------------------------

    movements = MovimientoInventario.objects.select_related(
        "producto",
        "usuario",
        "pedido",
    ).order_by(
        "-creado"
    )

    # --------------------------------------------------------
    # ESTADÍSTICAS
    # --------------------------------------------------------

    products_count = products.count()

    stock_count = (
        products.aggregate(
            total=Sum("stock")
        )["total"]
        or 0
    )

    workers_count = workers.count()

    orders_count = orders.count()

    sales_today = (
        orders.filter(
            creado__date=__import__("datetime").date.today()
        ).aggregate(
            total=Sum("total")
        )["total"]
        or Decimal("0.00")
    )

    # --------------------------------------------------------
    # PRODUCTOS MÁS VENDIDOS
    # --------------------------------------------------------

    top_products = (
        ItemPedido.objects
        .values("producto__nombre")
        .annotate(
            unidades=Sum("cantidad"),
            ingresos=Sum(
                F("precio") * F("cantidad")
            ),
        )
        .order_by("-unidades")[:10]
    )

    # --------------------------------------------------------
    # PEDIDOS RECIENTES
    # --------------------------------------------------------

    recent_orders = orders[:10]

    # --------------------------------------------------------
    # PRODUCTOS DISPONIBLES
    # --------------------------------------------------------

    available_products = products.filter(
        stock__gt=0
    )

    # --------------------------------------------------------
    # CONTEXTO
    # --------------------------------------------------------

    context = {
        "role": role,
        "role_name": ROLE_NAMES[role],

        "section": section,

        "products": products,
        "available_products": available_products,

        "orders": orders,
        "recent_orders": recent_orders,

        "workers": workers,

        "movements": movements,

        "products_count": products_count,
        "stock_count": stock_count,
        "workers_count": workers_count,
        "orders_count": orders_count,

        "sales_today": sales_today,

        "top_products": top_products,
    }

    return render(
        request,
        "sistema.html",
        context,
    )


# ============================================================
# OPERACIONES DEL SISTEMA
# ============================================================

@login_required
def system_action(request):

    if request.method != "POST":
        return redirect("sistema")

    action = request.POST.get("action", "")
    role = get_user_role(request.user)

    # ========================================================
    # CREAR PRODUCTO
    # SOLO ADMINISTRADOR
    # ========================================================

    if action == "crear_producto":

        if role != "admin":
            messages.error(
                request,
                "Solo el Administrador puede crear productos."
            )
            return redirect("sistema")

        categoria_id = request.POST.get("categoria")
        nombre = request.POST.get("nombre", "").strip()
        marca = request.POST.get("marca", "").strip()
        precio = request.POST.get("precio", "0")
        stock = request.POST.get("stock", "0")
        volumen_ml = request.POST.get("volumen_ml", "0")
        porcentaje = request.POST.get(
            "porcentaje_alcohol",
            "0"
        )
        pais = request.POST.get(
            "pais_origen",
            "Perú"
        )
        descripcion = request.POST.get(
            "descripcion",
            ""
        )

        if not categoria_id or not nombre:
            messages.error(
                request,
                "Completa los campos obligatorios."
            )
            return redirect("sistema")

        categoria = get_object_or_404(
            Categoria,
            id=categoria_id
        )

        producto = Producto.objects.create(
            categoria=categoria,
            nombre=nombre,
            marca=marca or None,
            precio=Decimal(precio),
            stock=int(stock),
            volumen_ml=int(volumen_ml),
            porcentaje_alcohol=Decimal(porcentaje),
            pais_origen=pais,
            descripcion=descripcion,
        )

        MovimientoInventario.objects.create(
            producto=producto,
            tipo=MovimientoInventario.Tipo.INGRESO,
            cantidad=producto.stock,
            stock_anterior=0,
            stock_nuevo=producto.stock,
            usuario=request.user,
        )

        messages.success(
            request,
            f"Producto '{producto.nombre}' creado correctamente."
        )

        return redirect("sistema")


    # ========================================================
    # ACTUALIZAR PRODUCTO
    # SOLO ADMINISTRADOR
    # ========================================================

    if action == "actualizar_producto":

        if role != "admin":
            messages.error(
                request,
                "Solo el Administrador puede modificar productos."
            )
            return redirect("sistema")

        producto_id = request.POST.get("producto_id")

        producto = get_object_or_404(
            Producto,
            id=producto_id
        )

        stock_anterior = producto.stock

        producto.nombre = request.POST.get(
            "nombre",
            producto.nombre
        ).strip()

        producto.marca = request.POST.get(
            "marca",
            producto.marca or ""
        ).strip()

        producto.precio = Decimal(
            request.POST.get(
                "precio",
                producto.precio
            )
        )

        producto.volumen_ml = int(
            request.POST.get(
                "volumen_ml",
                producto.volumen_ml
            )
        )

        producto.porcentaje_alcohol = Decimal(
            request.POST.get(
                "porcentaje_alcohol",
                producto.porcentaje_alcohol
            )
        )

        producto.pais_origen = request.POST.get(
            "pais_origen",
            producto.pais_origen
        )

        producto.descripcion = request.POST.get(
            "descripcion",
            producto.descripcion or ""
        )

        nuevo_stock = int(
            request.POST.get(
                "stock",
                producto.stock
            )
        )

        producto.stock = nuevo_stock

        producto.save()

        if nuevo_stock != stock_anterior:

            MovimientoInventario.objects.create(
                producto=producto,
                tipo=MovimientoInventario.Tipo.AJUSTE,
                cantidad=nuevo_stock - stock_anterior,
                stock_anterior=stock_anterior,
                stock_nuevo=nuevo_stock,
                usuario=request.user,
            )

        messages.success(
            request,
            "Producto actualizado correctamente."
        )

        return redirect("sistema")


    # ========================================================
    # AJUSTAR STOCK
    # TIENDA
    # ADMINISTRADOR
    # ========================================================

    if action == "ajustar_stock":

        if role not in ("admin", "tienda"):
            messages.error(
                request,
                "El Trabajador no puede modificar el stock."
            )
            return redirect("sistema")

        producto_id = request.POST.get("producto_id")

        producto = get_object_or_404(
            Producto,
            id=producto_id
        )

        cantidad = int(
            request.POST.get(
                "cantidad",
                "0"
            )
        )

        stock_anterior = producto.stock

        nuevo_stock = stock_anterior + cantidad

        if nuevo_stock < 0:

            messages.error(
                request,
                "El stock no puede quedar negativo."
            )

            return redirect("sistema")

        producto.stock = nuevo_stock
        producto.save(
            update_fields=["stock"]
        )

        MovimientoInventario.objects.create(
            producto=producto,
            tipo=MovimientoInventario.Tipo.AJUSTE,
            cantidad=cantidad,
            stock_anterior=stock_anterior,
            stock_nuevo=nuevo_stock,
            usuario=request.user,
        )

        messages.success(
            request,
            f"Stock actualizado: {nuevo_stock} unidades."
        )

        return redirect("sistema")


    # ========================================================
    # REGISTRAR INGRESO DE MERCADERÍA
    # TIENDA
    # ADMINISTRADOR
    # ========================================================

    if action == "ingreso_stock":

        if role not in ("admin", "tienda"):

            messages.error(
                request,
                "No tienes permisos para registrar ingresos."
            )

            return redirect("sistema")

        producto_id = request.POST.get(
            "producto_id"
        )

        cantidad = int(
            request.POST.get(
                "cantidad",
                "0"
            )
        )

        if cantidad <= 0:

            messages.error(
                request,
                "La cantidad debe ser mayor que cero."
            )

            return redirect("sistema")

        producto = get_object_or_404(
            Producto,
            id=producto_id
        )

        anterior = producto.stock

        producto.stock += cantidad

        producto.save(
            update_fields=["stock"]
        )

        MovimientoInventario.objects.create(
            producto=producto,
            tipo=MovimientoInventario.Tipo.INGRESO,
            cantidad=cantidad,
            stock_anterior=anterior,
            stock_nuevo=producto.stock,
            usuario=request.user,
        )

        messages.success(
            request,
            f"Ingreso registrado: +{cantidad} unidades."
        )

        return redirect("sistema")


    # ========================================================
    # CAMBIAR ESTADO DE PEDIDO
    # ADMINISTRADOR / TIENDA
    # ========================================================

    if action == "estado_pedido":

        if role not in ("admin", "tienda"):

            messages.error(
                request,
                "El Trabajador no puede gestionar pedidos."
            )

            return redirect("sistema")

        pedido_id = request.POST.get(
            "pedido_id"
        )

        pedido = get_object_or_404(
            Pedido,
            id=pedido_id
        )

        estado = request.POST.get(
            "estado",
            ""
        )

        # Solo si tu modelo Pedido ya tiene campo estado.
        if hasattr(pedido, "estado"):

            pedido.estado = estado
            pedido.save(
                update_fields=["estado"]
            )

            messages.success(
                request,
                f"Pedido #{pedido.id} actualizado."
            )

        else:

            messages.warning(
                request,
                "Tu modelo Pedido todavía no tiene el campo 'estado'."
            )

        return redirect("sistema")


    # ========================================================
    # ACCIÓN DESCONOCIDA
    # ========================================================

    messages.error(
        request,
        "Operación no reconocida."
    )

    return redirect("sistema")


# ============================================================
# CARRITO
# ============================================================

def obtener_carrito(request):
    return request.session.setdefault(
        "carrito",
        {}
    )


def guardar_carrito(request, carrito):
    request.session["carrito"] = carrito
    request.session.modified = True


def agregar_al_carrito(
    request,
    producto_id
):

    producto = get_object_or_404(
        Producto,
        id=producto_id
    )

    carrito = obtener_carrito(request)

    key = str(producto.id)

    cantidad = int(
        request.POST.get(
            "cantidad",
            1
        )
    )

    if cantidad < 1:
        cantidad = 1

    actual = int(
        carrito.get(
            key,
            0
        )
    )

    nueva = actual + cantidad

    if nueva > producto.stock:

        nueva = producto.stock

    carrito[key] = nueva

    guardar_carrito(
        request,
        carrito
    )

    return redirect(
        request.META.get(
            "HTTP_REFERER",
            "home"
        )
    )


def actualizar_carrito(
    request,
    producto_id
):

    producto = get_object_or_404(
        Producto,
        id=producto_id
    )

    carrito = obtener_carrito(request)

    cantidad = int(
        request.POST.get(
            "cantidad",
            1
        )
    )

    if cantidad <= 0:

        carrito.pop(
            str(producto.id),
            None
        )

    else:

        carrito[str(producto.id)] = min(
            cantidad,
            producto.stock
        )

    guardar_carrito(
        request,
        carrito
    )

    return redirect(
        request.META.get(
            "HTTP_REFERER",
            "home"
        )
    )


def eliminar_del_carrito(
    request,
    producto_id
):

    carrito = obtener_carrito(request)

    carrito.pop(
        str(producto_id),
        None
    )

    guardar_carrito(
        request,
        carrito
    )

    return redirect(
        request.META.get(
            "HTTP_REFERER",
            "home"
        )
    )


def limpiar_carrito(request):

    request.session["carrito"] = {}

    request.session.modified = True

    return redirect(
        request.META.get(
            "HTTP_REFERER",
            "home"
        )
    )


# ============================================================
# PROCESAR PEDIDO
# ============================================================

@transaction.atomic
def procesar_pedido(request):

    if request.method != "POST":

        return JsonResponse(
            {
                "ok": False,
                "error": "Método no permitido."
            },
            status=405,
        )

    carrito = obtener_carrito(request)

    if not carrito:

        return JsonResponse(
            {
                "ok": False,
                "error": "El carrito está vacío."
            },
            status=400,
        )

    nombre = request.POST.get(
        "nombre",
        ""
    ).strip()

    celular = request.POST.get(
        "celular",
        ""
    ).strip()

    direccion = request.POST.get(
        "direccion",
        ""
    ).strip()

    distrito = request.POST.get(
        "distrito",
        ""
    ).strip()

    forma_entrega = request.POST.get(
        "entrega",
        "DELIVERY"
    )

    referencia = request.POST.get(
        "referencia",
        ""
    ).strip()

    metodo_pago = request.POST.get(
        "pago",
        "EFECTIVO"
    )

    if not nombre or not celular:

        return JsonResponse(
            {
                "ok": False,
                "error": "Completa tus datos."
            },
            status=400,
        )

    total = Decimal("0.00")

    productos = Producto.objects.select_for_update().filter(
        id__in=carrito.keys()
    )

    productos_map = {
        str(producto.id): producto
        for producto in productos
    }

    for key, cantidad in carrito.items():

        producto = productos_map.get(
            str(key)
        )

        if not producto:

            return JsonResponse(
                {
                    "ok": False,
                    "error": "Uno de los productos ya no existe."
                },
                status=400,
            )

        cantidad = int(cantidad)

        if cantidad <= 0:
            continue

        if cantidad > producto.stock:

            return JsonResponse(
                {
                    "ok": False,
                    "error": (
                        f"No hay suficiente stock de "
                        f"{producto.nombre}."
                    ),
                },
                status=400,
            )

        total += producto.precio * cantidad

    # --------------------------------------------------------
    # CREAR PEDIDO
    # --------------------------------------------------------

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
    )

    # --------------------------------------------------------
    # DESCONTAR STOCK + REGISTRAR MOVIMIENTO
    # --------------------------------------------------------

    for key, cantidad in carrito.items():

        producto = productos_map.get(
            str(key)
        )

        if not producto:
            continue

        cantidad = int(cantidad)

        if cantidad <= 0:
            continue

        stock_anterior = producto.stock

        producto.stock -= cantidad

        producto.save(
            update_fields=["stock"]
        )

        ItemPedido.objects.create(
            pedido=pedido,
            producto=producto,
            cantidad=cantidad,
            precio=producto.precio,
        )

        MovimientoInventario.objects.create(
            producto=producto,
            tipo=MovimientoInventario.Tipo.VENTA,
            cantidad=-cantidad,
            stock_anterior=stock_anterior,
            stock_nuevo=producto.stock,
            usuario=(
                request.user
                if request.user.is_authenticated
                else None
            ),
            pedido=pedido,
        )

    # --------------------------------------------------------
    # LIMPIAR CARRITO
    # --------------------------------------------------------

    request.session["carrito"] = {}

    request.session.modified = True

    return JsonResponse(
        {
            "ok": True,
            "pedido_id": pedido.id,
            "total": str(total),
            "mensaje": (
                f"Pedido #{pedido.id} registrado correctamente."
            ),
        }
    )