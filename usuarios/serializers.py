# usuarios/serializers.py
from rest_framework import serializers
from .models import Usuario, Gasto

class UsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ['id', 'nombre', 'correo', 'presupuesto']


class GastoSerializer(serializers.ModelSerializer):
    fecha = serializers.SerializerMethodField()

    class Meta:
        model = Gasto
        fields = ['id', 'categoria', 'cantidad', 'fecha']

    def get_fecha(self, obj):
        # obj.fecha es un date; mantenemos formato ISO YYYY-MM-DD
        return obj.fecha.isoformat() if obj.fecha else None
