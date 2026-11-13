from django.db import models
from django.conf import settings

class Categoria(models.Model):
    nombre = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.nombre

class Producto(models.Model):
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE, related_name='productos')
    nombre = models.CharField(max_length=100)
    marca = models.CharField(max_length=50, blank=True, null=True)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.IntegerField(default=0)
    volumen_ml = models.IntegerField(help_text="Volumen en mililitros (ej: 750)")
    porcentaje_alcohol = models.DecimalField(max_digits=4, decimal_places=1)
    pais_origen = models.CharField(max_length=50, default="Perú")
    descripcion = models.TextField(blank=True, null=True)
    es_pack = models.BooleanField(default=False)
    imagen = models.ImageField(upload_to='productos/', blank=True, null=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nombre} ({self.volumen_ml}ml)"

class Pedido(models.Model):
    METODOS_PAGO = [
        ('YAPE', 'Yape'),
        ('PLIN', 'Plin'),
        ('TARJETA', 'Tarjeta de Crédito/Débito'),
        ('EFECTIVO', 'Efectivo contra entrega'),
    ]
    nombre_cliente = models.CharField(max_length=100)
    celular = models.CharField(max_length=15)
    direccion = models.CharField(max_length=255)
    distrito = models.CharField(max_length=100)
    forma_entrega = models.CharField(
        max_length=20,
        choices=[("DELIVERY", "Delivery"), ("RECOJO", "Recojo en tienda")],
        default="DELIVERY",
    )
    referencia = models.CharField(max_length=160, blank=True)
    metodo_pago = models.CharField(max_length=20, choices=METODOS_PAGO)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    creado = models.DateTimeField(auto_now_add=True)
    pagado = models.BooleanField(default=False)

    def __str__(self):
        return f"Pedido #{self.id} - {self.nombre_cliente}"


class ItemPedido(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='items')
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    cantidad = models.PositiveIntegerField(default=1)
    precio = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.cantidad} x {self.producto.nombre}"


class MovimientoInventario(models.Model):
    class Tipo(models.TextChoices):
        VENTA = "VENTA", "Venta"
        AJUSTE = "AJUSTE", "Ajuste de inventario"
        INGRESO = "INGRESO", "Ingreso de inventario"

    producto = models.ForeignKey(
        Producto, on_delete=models.PROTECT, related_name="movimientos"
    )
    tipo = models.CharField(max_length=10, choices=Tipo.choices)
    cantidad = models.IntegerField()
    stock_anterior = models.PositiveIntegerField()
    stock_nuevo = models.PositiveIntegerField()
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="movimientos_inventario",
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
        return f"{self.get_tipo_display()}: {self.producto.nombre} ({self.cantidad})"
