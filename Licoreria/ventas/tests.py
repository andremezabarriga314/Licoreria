import json
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from .models import Categoria, ItemPedido, MovimientoInventario, Pedido, Producto


class StoreOperationsTests(TestCase):
    def setUp(self):
        self.category = Categoria.objects.get(nombre="Cervezas")
        self.product = Producto.objects.create(
            categoria=self.category,
            nombre="Cerveza de prueba",
            precio=Decimal("12.50"),
            stock=5,
            volumen_ml=330,
            porcentaje_alcohol=Decimal("5.0"),
        )

    def post_order(self, quantity=2, **overrides):
        data = {
            "nombre": "Cliente de prueba",
            "celular": "987654321",
            "entrega": "Recojo en tienda",
            "direccion": "",
            "distrito": "",
            "referencia": "",
            "pago": "Yape",
            "items": [{"id": self.product.id, "cantidad": quantity}],
        }
        data.update(overrides)
        return self.client.post(
            reverse("procesar"),
            data=json.dumps(data),
            content_type="application/json",
        )

    def test_sales_dashboard_starts_empty(self):
        user = get_user_model().objects.create_superuser(
            username="admin", email="admin@example.com", password="StrongPass123!"
        )
        self.client.force_login(user)

        response = self.client.get(reverse("sistema"), {"seccion": "Ventas"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["orders_count"], 0)
        self.assertContains(response, "Todavía no se registran compras desde la tienda.")

    def test_dashboard_sections_render_for_each_role(self):
        admin = get_user_model().objects.create_superuser(
            username="admin", email="admin@example.com", password="StrongPass123!"
        )
        self.client.force_login(admin)
        for section in ("Productos", "Inventario", "Trabajadores", "Reportes"):
            self.assertEqual(
                self.client.get(reverse("sistema"), {"seccion": section}).status_code,
                200,
            )

        worker = get_user_model().objects.create_user(
            username="worker", password="StrongPass123!"
        )
        Group.objects.get(name="Trabajador").user_set.add(worker)
        self.client.force_login(worker)
        self.assertEqual(
            self.client.get(reverse("sistema"), {"seccion": "Inventario"}).status_code,
            200,
        )

        store = get_user_model().objects.create_user(
            username="store", password="StrongPass123!"
        )
        Group.objects.get(name="Tienda").user_set.add(store)
        self.client.force_login(store)
        self.assertEqual(
            self.client.get(reverse("sistema"), {"seccion": "Catálogo"}).status_code,
            200,
        )

    def test_admin_can_create_product_and_register_initial_stock(self):
        admin = get_user_model().objects.create_superuser(
            username="admin", email="admin@example.com", password="StrongPass123!"
        )
        self.client.force_login(admin)

        response = self.client.post(
            reverse("system_action"),
            {
                "action": "crear_producto",
                "seccion": "Productos",
                "categoria": self.category.id,
                "nombre": "Nuevo producto",
                "marca": "",
                "precio": "18.90",
                "stock": "7",
                "volumen_ml": "500",
                "porcentaje_alcohol": "4.5",
                "pais_origen": "Perú",
                "descripcion": "",
            },
        )

        self.assertRedirects(
            response, f"{reverse('sistema')}?seccion=Productos"
        )
        product = Producto.objects.get(nombre="Nuevo producto")
        movement = MovimientoInventario.objects.get(producto=product)
        self.assertEqual(movement.cantidad, 7)
        self.assertEqual(movement.stock_nuevo, 7)

    def test_store_purchase_records_sale_and_stock_movement(self):
        response = self.post_order(quantity=2)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(Pedido.objects.count(), 1)
        self.assertEqual(ItemPedido.objects.get().precio, Decimal("12.50"))
        self.assertEqual(Pedido.objects.get().total, Decimal("25.00"))
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 3)
        movement = MovimientoInventario.objects.get(tipo=MovimientoInventario.Tipo.VENTA)
        self.assertEqual(movement.cantidad, -2)
        self.assertEqual(movement.stock_anterior, 5)
        self.assertEqual(movement.stock_nuevo, 3)

    def test_invalid_stock_does_not_create_order_or_change_stock(self):
        response = self.post_order(quantity=8)

        self.assertEqual(response.status_code, 409)
        self.assertEqual(Pedido.objects.count(), 0)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 5)
        self.assertEqual(MovimientoInventario.objects.count(), 0)

    def test_login_requires_real_credentials_and_matching_role(self):
        user = get_user_model().objects.create_user(
            username="worker", password="StrongPass123!"
        )
        Group.objects.get(name="Trabajador").user_set.add(user)

        wrong_role = self.client.post(
            reverse("role_login"),
            {"username": "worker", "password": "StrongPass123!", "role": "admin"},
        )
        self.assertRedirects(wrong_role, reverse("home"))
        self.assertNotIn("_auth_user_id", self.client.session)

        valid_login = self.client.post(
            reverse("role_login"),
            {"username": "worker", "password": "StrongPass123!", "role": "trabajador"},
        )
        self.assertRedirects(valid_login, reverse("sistema"))
        self.assertEqual(
            self.client.get(reverse("sistema")).context["role"],
            "trabajador",
        )

    def test_superuser_can_open_each_selected_panel(self):
        get_user_model().objects.create_superuser(
            username="admin", email="admin@example.com", password="StrongPass123!"
        )

        for role in ("admin", "trabajador", "tienda"):
            response = self.client.post(
                reverse("role_login"),
                {
                    "username": "admin",
                    "password": "StrongPass123!",
                    "role": role,
                },
            )
            self.assertRedirects(response, reverse("sistema"))
            self.assertEqual(
                self.client.get(reverse("sistema")).context["role"],
                role,
            )

    def test_homepage_renders_database_catalog(self):
        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "catalogoTiendaData")
        self.assertContains(response, self.product.nombre)
