from django.contrib import admin
from .models import Categoria, ItemPedido, MovimientoInventario, Pedido, Producto

@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('nombre',)

@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'categoria', 'precio', 'stock', 'es_pack')
    list_filter = ('categoria', 'es_pack', 'pais_origen')
    search_fields = ('nombre', 'marca')

@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre_cliente', 'creado', 'total', 'metodo_pago', 'pagado')
    list_filter = ('pagado', 'metodo_pago', 'creado')
    search_fields = ('nombre_cliente', 'celular')

@admin.register(ItemPedido)
class ItemPedidoAdmin(admin.ModelAdmin):
    list_display = ('pedido', 'producto', 'cantidad', 'precio')
    search_fields = ('producto__nombre',)

@admin.register(MovimientoInventario)
class MovimientoInventarioAdmin(admin.ModelAdmin):
    list_display = ('creado', 'tipo', 'producto', 'cantidad', 'stock_anterior', 'stock_nuevo', 'usuario')
    list_filter = ('tipo', 'creado')
    search_fields = ('producto__nombre', 'usuario__username')
