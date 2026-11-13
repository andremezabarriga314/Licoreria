from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model

from .models import Producto

User = get_user_model()


class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = (
            "categoria",
            "nombre",
            "marca",
            "precio",
            "stock",
            "volumen_ml",
            "porcentaje_alcohol",
            "pais_origen",
            "descripcion",
            "es_pack",
            "imagen",
        )
        widgets = {
            "descripcion": forms.Textarea(attrs={"rows": 3}),
            "precio": forms.NumberInput(attrs={"min": "0.01", "step": "0.01"}),
            "stock": forms.NumberInput(attrs={"min": "0"}),
            "volumen_ml": forms.NumberInput(attrs={"min": "1"}),
            "porcentaje_alcohol": forms.NumberInput(
                attrs={"min": "0", "max": "100", "step": "0.1"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"
        self.fields["categoria"].widget.attrs["class"] = "form-select"
        self.fields["es_pack"].widget.attrs["class"] = "form-check-input"

    def clean_precio(self):
        precio = self.cleaned_data["precio"]
        if precio <= 0:
            raise forms.ValidationError("El precio debe ser mayor que cero.")
        return precio

    def clean_stock(self):
        stock = self.cleaned_data["stock"]
        if stock < 0:
            raise forms.ValidationError("El stock no puede ser negativo.")
        return stock

    def clean_volumen_ml(self):
        volumen = self.cleaned_data["volumen_ml"]
        if volumen <= 0:
            raise forms.ValidationError("El volumen debe ser mayor que cero.")
        return volumen

    def clean_porcentaje_alcohol(self):
        porcentaje = self.cleaned_data["porcentaje_alcohol"]
        if porcentaje < 0 or porcentaje > 100:
            raise forms.ValidationError("El porcentaje debe estar entre 0 y 100.")
        return porcentaje


class TrabajadorForm(UserCreationForm):
    rol = forms.ChoiceField(
        choices=(("Trabajador", "Trabajador"), ("Tienda", "Tienda"))
    )
    first_name = forms.CharField(max_length=150, label="Nombre")
    email = forms.EmailField(required=False, label="Correo")

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "first_name", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"
        self.fields["rol"].widget.attrs["class"] = "form-select"
