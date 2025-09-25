# usuarios/urls.py
from django.urls import path
from .views import (
    RegisterView, VerifyRegisterView, LoginView, VerifyLoginView,
    DashboardView, GastoView, GastoDetailView, PresupuestoView
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("verify-register/", VerifyRegisterView.as_view(), name="verify-register"),
    path("login/", LoginView.as_view(), name="login"),
    path("verify-login/", VerifyLoginView.as_view(), name="verify-login"),
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("gastos/", GastoView.as_view(), name="gastos"),              # GET y POST
    path("gastos/<int:pk>/", GastoDetailView.as_view(), name="gasto-detail"),  # DELETE
    path("presupuesto/", PresupuestoView.as_view(), name="presupuesto"),  # 🔥
]
