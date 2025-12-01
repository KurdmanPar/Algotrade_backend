# apps/accounts/views.py
from rest_framework import viewsets, generics, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth import get_user_model, login
from django.shortcuts import get_object_or_404
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.decorators import action
from .models import UserProfile
from .serializers import (
    UserSerializer,
    UserRegistrationSerializer,
    LoginSerializer,
    UserProfileSerializer
)
from apps.core.views import SecureModelViewSet  # اطمینان حاصل کنید که این فایل وجود دارد و SecureModelViewSet را تعریف می‌کند

User = get_user_model()


class UserViewSet(SecureModelViewSet):  # تغییر: از SecureModelViewSet استفاده می‌کند
    queryset = User.objects.all()
    serializer_class = UserSerializer
    # این ViewSet فقط کاربران ادمین می‌توانند لیست کامل را ببینند
    # کاربر عادی فقط خودش را می‌بیند (در get_queryset تعریف شده)

    def get_queryset(self):
        if self.request.user.is_staff:
            return User.objects.all()
        return User.objects.filter(id=self.request.user.id)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def profile(self, request):
        user = request.user
        profile, created = UserProfile.objects.get_or_create(user=user)
        serializer = UserProfileSerializer(profile)
        return Response(serializer.data)


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]

    def perform_create(self, serializer):
        user = serializer.save()
        # ساخت پروفایل کاربر به صورت خودکار
        UserProfile.objects.get_or_create(user=user)


class LoginView(generics.GenericAPIView):
    serializer_class = LoginSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        login(request, user)

        refresh = RefreshToken.for_user(user)
        data = {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': UserSerializer(user).data
        }
        return Response(data, status=status.HTTP_200_OK)


class ProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        profile, created = UserProfile.objects.get_or_create(user=self.request.user)
        return profile