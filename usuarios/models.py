# usuarios/models.py
from django.db import models
from django.utils import timezone
import random
from datetime import date, timedelta


class Usuario(models.Model):
    id = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=15)
    correo = models.EmailField(unique=True)
    presupuesto = models.DecimalField(max_digits=12, decimal_places=2, default=0)  # 🔥 nuevo campo

    def __str__(self):
        return self.correo

class Gasto(models.Model):
    CATEGORIAS = [
        ('comida', 'Comida'),
        ('transporte', 'Transporte'),
        ('entretenimiento', 'Entretenimiento'),
        ('otros', 'Otros'),
    ]

    id = models.AutoField(primary_key=True)
    correo_usuarios = models.ForeignKey(Usuario, on_delete=models.CASCADE, to_field="correo")
    fecha = models.DateField(default=date.today)  # ahora sí solo guarda la fecha
    cantidad = models.DecimalField(max_digits=12, decimal_places=2)
    categoria = models.CharField(max_length=20, choices=CATEGORIAS)

class OTPCode(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)

    @classmethod
    def create_otp(cls, usuario):
        code = str(random.randint(100000, 999999))  # 6 dígitos
        otp = cls.objects.create(
            usuario=usuario,
            code=code,
            expires_at=timezone.now() + timedelta(minutes=5)
        )
        return otp

    def __str__(self):
        return f"{self.usuario.correo} - {self.code}"
