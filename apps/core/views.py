# apps/core/views.py
from rest_framework import viewsets, permissions
from rest_framework.exceptions import PermissionDenied


class IsOwnerOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        # اگر مدل فیلد owner داشت
        if hasattr(obj, 'owner'):
            return obj.owner == request.user
        # اگر فیلد user داشت
        elif hasattr(obj, 'user'):
            return obj.user == request.user
        # در غیر این صورت، فقط خواندنی است
        elif request.method in permissions.SAFE_METHODS:
            return True
        return False


class SecureModelViewSet(viewsets.ModelViewSet):
    """
    ViewSet پایه ایمن برای مدل‌هایی که دارای فیلد owner یا user هستند.
    """
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]

    def get_queryset(self):
        queryset = super().get_queryset()
        # اگر مدل دارای فیلد owner باشد
        if hasattr(queryset.model, 'owner'):
            return queryset.filter(owner=self.request.user)
        # اگر فیلد user داشت
        elif hasattr(queryset.model, 'user'):
            return queryset.filter(user=self.request.user)
        # اگر فیلدی نداشت، فقط اجازه خواندن داده شود
        else:
            if self.action not in ['list', 'retrieve']:
                raise PermissionDenied("This resource does not support modification.")
            return queryset

    def perform_create(self, serializer):
        user = self.request.user
        # اگر فیلد owner در serializer وجود داشت
        if 'owner' in serializer.fields:
            serializer.save(owner=user)
        # اگر فیلد user داشت
        elif 'user' in serializer.fields:
            serializer.save(user=user)
        # در غیر این صورت، فقط ذخیره کن
        else:
            serializer.save()