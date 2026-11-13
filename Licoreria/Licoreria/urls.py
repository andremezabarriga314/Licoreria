
from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

from ventas import views


urlpatterns = [
    # Administración Django
    path("admin/", admin.site.urls),

    # Tienda
    path("", views.home, name="home"),

    # Acceso y cierre de sesión
    path("acceso/", views.role_login, name="role_login"),
    path("salir/", views.role_logout, name="role_logout"),

    # Sistema interno
    path("sistema/", views.sistema, name="sistema"),
    path(
        "sistema/operacion/",
        views.system_action,
        name="system_action",
    ),

    # Carrito
    path(
        "agregar/<int:producto_id>/",
        views.agregar_al_carrito,
        name="agregar",
    ),
    path(
        "actualizar/<int:producto_id>/",
        views.actualizar_carrito,
        name="actualizar",
    ),
    path(
        "eliminar/<int:producto_id>/",
        views.eliminar_del_carrito,
        name="eliminar",
    ),
    path("limpiar/", views.limpiar_carrito, name="limpiar"),

    # Procesamiento de pedidos
    path("procesar/", views.procesar_pedido, name="procesar"),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )
