# apps/core/views.py
from rest_framework import viewsets, permissions
from .permissions import IsOwnerOrReadOnly


class SecureModelViewSet(viewsets.ModelViewSet):
    """
    ViewSet پایه:
    - نیاز به احراز هویت
    - محدود کردن queryset به آبجکت‌های متعلق به کاربر (owner/user)
    - ست کردن خودکار owner/user هنگام ساخت آبجکت
    """

    # بهتر است همهٔ درخواست‌ها لاگین شده باشند
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]

    # در صورت نیاز می‌توانید این را در کلاس‌های فرزند override کنید
    user_field_name = None  # مثلا در subclass بگویید: user_field_name = "owner"

    def get_user_field_name(self, model=None):
        """
        نام فیلد کاربر/مالک را به شکل قابل Override برمی‌گرداند.
        Priority: مقدار تعیین‌شده روی viewset > فیلد owner > فیلد user.
        """
        if self.user_field_name:
            return self.user_field_name

        # اگر مدل پاس داده نشده، از queryset یا serializer حدس بزن
        if model is None:
            model = getattr(getattr(self, "queryset", None), "model", None)
            if model is None and hasattr(self, "serializer_class"):
                meta = getattr(self.serializer_class, "Meta", None)
                model = getattr(meta, "model", None)

        if model is None:
            return None

        if hasattr(model, "owner"):
            return "owner"
        if hasattr(model, "user"):
            return "user"

        return None

    def get_queryset(self):
        """
        - اگر کلاس فرزند queryset تعریف کرده باشد، از همان استفاده می‌شود.
        - در غیر این صورت، از model در Meta.serializer استفاده می‌شود.
        - سپس براساس owner/user، queryset به آبجکت‌های متعلق به کاربر فعلی فیلتر می‌شود.
        """
        if getattr(self, "queryset", None) is not None:
            qs = self.queryset
        else:
            assert hasattr(self, "serializer_class"), (
                f"'{self.__class__.__name__}' should either have a `queryset` attribute, "
                f"or override the `get_queryset()` method, or define a `serializer_class` with Meta.model."
            )
            meta = getattr(self.serializer_class, "Meta", None)
            assert meta is not None and hasattr(meta, "model"), (
                f"'{self.serializer_class.__name__}' should have a `Meta` class with `model`."
            )
            model = meta.model
            qs = model.objects.all()

        model = qs.model
        user_field = self.get_user_field_name(model=model)
        if user_field:
            # مثلا qs.filter(owner=self.request.user)
            return qs.filter(**{user_field: self.request.user})

        # اگر مدل فیلد مالکیت نداشت، همان queryset (مثلا برای مدل‌های public)
        return qs

    def perform_create(self, serializer):
        """
        هنگام ساخت، کاربر فعلی را روی فیلد مالک (owner/user/...) ست می‌کند
        اگر مدل/serializer فیلد مرتبط داشته باشد.
        """
        user_field = self.get_user_field_name()
        if user_field:
            serializer.save(**{user_field: self.request.user})
        else:
            serializer.save()