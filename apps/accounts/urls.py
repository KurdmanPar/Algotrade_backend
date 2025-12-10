# apps/accounts/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'accounts'

# تعریف Router برای ViewSet (اگر وجود داشته باشد)
# router = DefaultRouter()
# router.register(r'users', views.UserViewSet, basename='user') # تغییر basename

urlpatterns = [
    # --- Authentication Endpoints ---
    path('register/', views.RegistrationView.as_view(), name='register'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('refresh/', views.TokenRefreshView.as_view(), name='token_refresh'),
    path('verify/', views.TokenVerifyView.as_view(), name='token_verify'),
    path('change-password/', views.ChangePasswordView.as_view(), name='change_password'),

    # --- User Profile Endpoints ---
    path('profile/', views.ProfileView.as_view(), name='user_profile'),
    path('profile/partial/', views.PartialProfileView.as_view(), name='partial_profile'),

    # --- User Session Management Endpoints ---
    path('sessions/', views.UserSessionsView.as_view(), name='sessions'),
    path('sessions/<uuid:session_id>/', views.UserSessionDetailView.as_view(), name='session_detail'),

    # --- User API Key Management Endpoints ---
    path('api-keys/', views.UserAPIKeysView.as_view(), name='api_keys'),
    path('api-keys/<uuid:api_key_id>/', views.UserAPIKeyDetailView.as_view(), name='api_key_detail'),

    # --- Password Reset Endpoints ---
    path('password-reset/', views.PasswordResetRequestView.as_view(), name='password_reset_request'),
    path('password-reset/confirm/<str:uidb64>/<str:token>/', views.PasswordResetConfirmView.as_view(),
         name='password_reset_confirm'), # تغییر type converter از uidb64 به str

    # --- Two-Factor Authentication Endpoints ---
    path('2fa/setup/', views.TwoFactorSetupView.as_view(), name='2fa_setup'),
    path('2fa/verify/', views.TwoFactorVerifyView.as_view(), name='2fa_verify'),
    path('2fa/disable/', views.TwoFactorDisableView.as_view(), name='2fa_disable'),

    # --- Account Verification Endpoints ---
    path('verify-email/', views.VerifyEmailView.as_view(), name='verify_email'),
    path('verify-kyc/', views.VerifyKYCView.as_view(), name='verify_kyc'),

    # --- Admin Endpoints ---
    path('admin/users/', views.AdminUserListView.as_view(), name='admin_users'),
    path('admin/users/<uuid:user_id>/', views.AdminUserDetailView.as_view(), name='admin_user_detail'),

    # اگر UserViewSet دارید، مسیر آن را می‌توانید اینجوری اضافه کنید:
    # path('', include(router.urls)),
]

# توجه: اگر از ViewSet برای کاربران استفاده نمی‌کنید، خطوط مربوط به router و include(router.urls) را حذف کنید.
# مسیرهای فعلی که مستقیماً به نماهای کلاسی متصل شده‌اند، کافی هستند.