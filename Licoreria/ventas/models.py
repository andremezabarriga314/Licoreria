
from django.conf import settings
from django.db import models


class Categoria(models.Model):
    nombre = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.nombre


class Producto(models.Model):
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.CASCADE,
        related_name="productos",
    )
    nombre = models.CharField(max_length=100)
    marca = models.CharField(max_length=50, blank=True, null=True)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.IntegerField(default=0)
    volumen_ml = models.IntegerField(
        help_text="Contenido del producto en mililitros."
    )
    porcentaje_alcohol = models.DecimalField(
        max_digits=4,
        decimal_places=1,
    )
    pais_origen = models.CharField(max_length=50, default="Perú")
    descripcion = models.TextField(blank=True, null=True)
    es_pack = models.BooleanField(default=False)
    imagen = models.ImageField(
        upload_to="productos/",
        blank=True,
        null=True,
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nombre


class Pedido(models.Model):

    class Estado(models.TextChoices):
        RECIBIDO = "RECIBIDO", "Recibido"
        CONFIRMADO = "CONFIRMADO", "Confirmado"
        PREPARACION = "PREPARACION", "En preparación"
        EN_CAMINO = "EN_CAMINO", "En camino"
        ENTREGADO = "ENTREGADO", "Entregado"
        CANCELADO = "CANCELADO", "Cancelado"

    METODOS_PAGO = [
        ("YAPE", "Yape"),
        ("PLIN", "Plin"),
        ("TARJETA", "Tarjeta"),
        ("EFECTIVO", "Efectivo"),
    ]

    FORMAS_ENTREGA = [
        ("DELIVERY", "Delivery"),
        ("RECOJO", "Recojo en tienda"),
    ]

    nombre_cliente = models.CharField(max_length=120)
    celular = models.CharField(max_length=20)
    direccion = models.CharField(max_length=255, blank=True)
    distrito = models.CharField(max_length=100, blank=True)
    forma_entrega = models.CharField(
        max_length=20,
        choices=FORMAS_ENTREGA,
        default="DELIVERY",
    )
    referencia = models.TextField(blank=True)
    metodo_pago = models.CharField(
        max_length=20,
        choices=METODOS_PAGO,
        default="EFECTIVO",
    )
    total = models.DecimalField(max_digits=10, decimal_places=2)
    pagado = models.BooleanField(default=False)
    estado = models.CharField(
        max_length=20,
        choices=Estado.choices,
        default=Estado.RECIBIDO,
    )
    creado = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Pedido #{self.pk} - {self.nombre_cliente}"


class ItemPedido(models.Model):
    pedido = models.ForeignKey(
        Pedido,
        on_delete=models.CASCADE,
        related_name="items",
    )
    producto = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,
    )
    cantidad = models.PositiveIntegerField(default=1)
    precio = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.producto.nombre} x {self.cantidad}"


class MovimientoInventario(models.Model):

    class Tipo(models.TextChoices):
        VENTA = "VENTA", "Venta"
        AJUSTE = "AJUSTE", "Ajuste"
        INGRESO = "INGRESO", "Ingreso"
        DEVOLUCION = "DEVOLUCION", "Devolución"

    producto = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,
        related_name="movimientos",
    )
    tipo = models.CharField(
        max_length=12,
        choices=Tipo.choices,
    )
    cantidad = models.IntegerField()
    stock_anterior = models.PositiveIntegerField()
    stock_nuevo = models.PositiveIntegerField()
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    pedido = models.ForeignKey(
        Pedido,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="movimientos_inventario",
    )
    creado = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.producto.nombre}"
