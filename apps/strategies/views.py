# apps/strategies/views.py
from rest_framework import viewsets, permissions
from rest_framework.response import Response
from .models import Strategy # اضافه شد
from .serializers import StrategySerializer

class IsOwnerOrReadOnly(permissions.BasePermission):
   """
   اجازه دسترسی را فقط به مالک شیء می‌دهد.
   """
   def has_object_permission(self, request, view, obj):
       if request.method in permissions.SAFE_METHODS:
           return True
       return obj.owner == request.user

class StrategyViewSet(viewsets.ModelViewSet):
   serializer_class = StrategySerializer
   permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]

   # اضافه کردن خط زیر:
   queryset = Strategy.objects.all()

   def get_queryset(self):
       # فقط استراتژی‌های کاربر فعلی را نشان بده
       return Strategy.objects.filter(owner=self.request.user)

   def perform_create(self, serializer):
       # مالک را به طور خودکار تنظیم کن
       serializer.save(owner=self.request.user)

