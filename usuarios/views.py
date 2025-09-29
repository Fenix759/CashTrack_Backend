# usuarios/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from django.utils import timezone
from django.contrib.auth.models import User
from .models import Usuario, OTPCode, Gasto
from .serializers import UsuarioSerializer, GastoSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from django.core.mail import send_mail
from django.conf import settings
from rest_framework.permissions import IsAuthenticated
from rest_framework import generics
from decimal import Decimal, InvalidOperation
import os
# --- Importar SendGrid ---
import sendgrid
from sendgrid.helpers.mail import Mail


def enviar_otp(correo, code):
    asunto = "Tu código de uso temporal - CashTrack"
    mensaje = f"Tu código de verificación es: {code}\n\nExpira en 5 minutos."

    try:
        sg = sendgrid.SendGridAPIClient(api_key=settings.SENDGRID_API_KEY)
        email = Mail(
            from_email=settings.DEFAULT_FROM_EMAIL,  # remitente validado en SendGrid
            to_emails=correo,
            subject=asunto,
            plain_text_content=mensaje,
        )
        response = sg.send(email)
        print(f"Correo enviado a {correo}, status: {response.status_code}")
    except Exception as e:
        print(f"Error enviando correo: {e}")



class RegisterView(APIView):
    def post(self, request):
        correo = request.data.get("correo")
        nombre = request.data.get("nombre")

        if Usuario.objects.filter(correo=correo).exists():
            return Response({"error": "Usuario ya existe"}, status=400)

        usuario = Usuario(nombre=nombre, correo=correo)
        usuario.save()

        # crear también (si no existe) el User nativo para JWT
        User.objects.get_or_create(username=correo, defaults={"email": correo})

        otp = OTPCode.create_otp(usuario)
        enviar_otp(correo, otp.code)
        return Response({"message": "OTP enviado al correo"}, status=200)


class VerifyRegisterView(APIView):
    def post(self, request):
        correo = request.data.get("correo")
        code = request.data.get("otp")

        try:
            otp = OTPCode.objects.filter(usuario__correo=correo, code=code, used=False).latest("id")
        except OTPCode.DoesNotExist:
            return Response({"error": "OTP inválido"}, status=400)

        if otp.expires_at < timezone.now():
            return Response({"error": "OTP expirado"}, status=400)

        otp.used = True
        otp.save()
        return Response({"message": "Usuario verificado con éxito"}, status=200)


class LoginView(APIView):
    def post(self, request):
        correo = request.data.get("correo")

        try:
            usuario = Usuario.objects.get(correo=correo)
        except Usuario.DoesNotExist:
            return Response({"error": "Usuario no existe"}, status=404)

        otp = OTPCode.create_otp(usuario)
        enviar_otp(correo, otp.code)
        return Response({"message": "OTP enviado al correo"}, status=200)


class VerifyLoginView(APIView):
    def post(self, request):
        correo = request.data.get("correo")
        code = request.data.get("otp")

        try:
            otp = OTPCode.objects.filter(usuario__correo=correo, code=code, used=False).latest("id")
        except OTPCode.DoesNotExist:
            return Response({"error": "OTP inválido"}, status=400)

        if otp.expires_at < timezone.now():
            return Response({"error": "OTP expirado"}, status=400)

        otp.used = True
        otp.save()

        # --- PARCHE RÁPIDO: crear/usar User y generar token con él ---
        user, _ = User.objects.get_or_create(username=correo, defaults={"email": correo})
        refresh = RefreshToken.for_user(user)

        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }, status=200)


class DashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            usuario = Usuario.objects.get(correo=request.user.username)
        except Usuario.DoesNotExist:
            return Response({"error": "Usuario no encontrado"}, status=404)

        gastos = Gasto.objects.filter(correo_usuarios=usuario)

        # total
        total = sum([float(g.cantidad) for g in gastos])  # 🔥 convertir a float

        # categorias: suma por categoria
        categorias_raw = {}
        for g in gastos:
            categorias_raw[g.categoria] = categorias_raw.get(g.categoria, Decimal('0')) + g.cantidad

        # preparar estructura con porcentaje relativo al total (si total==0 porcentaje = 0)
        categorias = {}
        for cat, val in categorias_raw.items():
            try:
                porcentaje = (Decimal(val) / Decimal(total) * 100) if total and total != 0 else Decimal('0')
            except (InvalidOperation, ZeroDivisionError):
                porcentaje = Decimal('0')
            categorias[cat] = {
                "valor": val,
                "porcentaje": round(float(porcentaje), 2)
            }

        # progreso relacionado al presupuesto (porcentaje de presupuesto gastado)
        presupuesto = usuario.presupuesto or Decimal('0')
        try:
            progreso = (Decimal(total) / Decimal(presupuesto) * 100) if presupuesto and presupuesto != 0 else Decimal('0')
        except (InvalidOperation, ZeroDivisionError):
            progreso = Decimal('0')

        # serializar gastos con GastoSerializer
        gastos_serializados = GastoSerializer(gastos, many=True).data

        # devolver Decimal como float/str (DRF serializa Decimal a string por defecto; convertimos a float para frontend)
        def dec_to_number(x):
            if isinstance(x, Decimal):
                # si es entero grande, convertir a float puede perder precisión; para dinero suele estar bien.
                return float(x)
            return x

        response = {
            "total": dec_to_number(total),
            "categorias": categorias,
            "gastos": gastos_serializados,
            "presupuesto": dec_to_number(presupuesto),
            "progreso": round(float(progreso), 2)
        }

        return Response(response, status=200)


class GastoView(generics.ListCreateAPIView):
    serializer_class = GastoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        usuario = Usuario.objects.get(correo=self.request.user.username)
        return Gasto.objects.filter(correo_usuarios=usuario)

    def perform_create(self, serializer):
        usuario = Usuario.objects.get(correo=self.request.user.username)
        serializer.save(correo_usuarios=usuario)


class GastoDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = GastoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        usuario = self.request.user.username
        return Gasto.objects.filter(correo_usuarios__correo=usuario)


class PresupuestoView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            usuario = Usuario.objects.get(correo=request.user.username)
        except Usuario.DoesNotExist:
            return Response({"error": "Usuario no encontrado"}, status=404)

        nuevo_presupuesto = request.data.get("presupuesto")
        if nuevo_presupuesto is None:
            return Response({"error": "Debes enviar un valor"}, status=400)

        # parsear a Decimal de forma segura
        try:
            usuario.presupuesto = Decimal(str(nuevo_presupuesto))
        except (InvalidOperation, ValueError):
            return Response({"error": "Valor de presupuesto inválido"}, status=400)

        usuario.save()
        return Response({"message": "Presupuesto actualizado con éxito", "presupuesto": float(usuario.presupuesto)}, status=200)
