# apps/core/mixins.py

from rest_framework import permissions, generics, viewsets
from django.db.models import Q
from django.core.exceptions import PermissionDenied
from django.contrib.auth import get_user_model
from .permissions import IsOwnerOrReadOnly, IsOwnerOfRelatedObject, IsAdminUserOrReadOnly, IsVerifiedUser, IsPublicOrOwner
from .models import BaseOwnedModel # فرض بر این است که مدل BaseOwnedModel در core تعریف شده است یا از آن ارث می‌برد
from .exceptions import CoreSystemException, DataIntegrityException, ConfigurationError
from .helpers import get_client_ip, generate_device_fingerprint
from .services import AuditService, SecurityService # فرض بر این است که این سرویس‌ها وجود دارند
import logging

logger = logging.getLogger(__name__)
User = get_user_model()

# --- میکسین‌های مربوط به امنیت و مالکیت ---

class OwnerFilterMixin:
    """
    Mixin to filter the queryset based on the owner of the object.
    Assumes the model has an 'owner' field.
    Should be used in conjunction with an appropriate permission class like IsOwnerOrReadOnly.
    """
    owner_field_name = 'owner' # نام فیلد مالک (می‌توان از طریق override تغییر داد)

    def get_queryset(self):
        """
        Filters the base queryset to only include objects owned by the current user.
        This method should be called *after* super().get_queryset() in the final ViewSet.
        """
        qs = super().get_queryset() # فرض: کلاس والد یک get_queryset دارد (مثل generics.GenericAPIView یا viewsets.ModelViewSet)
        user = self.request.user
        if not user.is_authenticated:
            # اگر کاربر احراز هویت نشده باشد، مجموعه خالی برگردانده می‌شود
            return qs.none()

        # فیلتر بر اساس فیلد مالک
        filter_kwargs = {f"{self.owner_field_name}": user}
        return qs.filter(**filter_kwargs)


class SecureModelViewSetMixin:
    """
    A mixin to apply common security settings to ViewSets.
    Combines ownership filtering (via OwnerFilterMixin) and permission checking.
    Assumes the related model inherits from BaseOwnedModel or has an 'owner' field.
    """
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]

    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view requires.
        """
        return [permission() for permission in self.permission_classes]

    # توجه: این میکسین معمولاً با OwnerFilterMixin ترکیب می‌شود
    # def get_queryset(self):
    #     # این متد باید در نهایت با متد get_queryset نما ترکیب شود
    #     # معمولاً با استفاده از OwnerFilterMixin یا از طریق override این متد در نما انجام می‌شود
    #     # برای مثال:
    #     # qs = super().get_queryset() # این super، ممکن است OwnerFilterMixin یا یک نما پایه دیگر باشد
    #     # اگر مدل دارای فیلد owner بود، فیلتر مالک را اعمال کن
    #     # if hasattr(qs.model, 'owner'):
    #     #     user = self.request.user
    #     #     if user.is_authenticated:
    #     #         return qs.filter(owner=user)
    #     #     else:
    #     #         return qs.none()
    #     # return qs
    #     # اما چون این فقط یک میکسین است، فقط منطق کلی را ارائه می‌دهد
    #     # منطق فیلتر کردن معمولاً در OwnerFilterMixin انجام می‌شود.
    #     return super().get_queryset()


class SecureAPIViewMixin:
    """
    A mixin to apply common security settings to generic API Views (APIView, GenericAPIView).
    Combines ownership filtering for querysets and permission checking.
    """
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]

    def get_permissions(self):
        return [permission() for permission in self.permission_classes]

    def filter_queryset_by_owner(self, queryset):
        """
        Filters a given queryset by the current user's ownership if applicable.
        """
        user = self.request.user
        if not user.is_authenticated:
            return queryset.none()

        if hasattr(queryset.model, 'owner'):
            return queryset.filter(owner=user)
        return queryset


# --- میکسین‌های مربوط به فیلتر و جستجو ---

class SearchFilterMixin:
    """
    Mixin to add a simple search capability based on a specified field.
    Override 'search_fields' attribute to define searchable fields.
    """
    search_fields = ['name', 'description'] # فیلدهای پیش‌فرض قابل جستجو

    def get_queryset(self):
        """
        Applies search filter if 'search' parameter is present in the request.
        """
        qs = super().get_queryset() # فرض: کلاس والد یک get_queryset دارد
        search_query = self.request.query_params.get('search', None)
        if search_query:
            q_objects = Q()
            for field in self.search_fields:
                q_objects |= Q(**{f"{field}__icontains": search_query})
            qs = qs.filter(q_objects)
        return qs


class TimeRangeFilterMixin:
    """
    Mixin to filter queryset based on a time range (e.g., created_at, updated_at).
    Override 'time_field' attribute to specify the field to filter on.
    """
    time_field = 'created_at' # فیلد پیش‌فرض

    def get_queryset(self):
        """
        Applies time range filter based on 'start_time' and 'end_time' query parameters.
        """
        qs = super().get_queryset() # فرض: کلاس والد یک get_queryset دارد
        start_time = self.request.query_params.get('start_time', None)
        end_time = self.request.query_params.get('end_time', None)

        if start_time:
            from django.utils.dateparse import parse_datetime
            start_dt = parse_datetime(start_time)
            if start_dt:
                qs = qs.filter(**{f"{self.time_field}__gte": start_dt})
            else:
                logger.warning(f"Invalid start_time format: {start_time} in view {self.__class__.__name__}")
        if end_time:
            from django.utils.dateparse import parse_datetime
            end_dt = parse_datetime(end_time)
            if end_dt:
                qs = qs.filter(**{f"{self.time_field}__lte": end_dt})
            else:
                logger.warning(f"Invalid end_time format: {end_time} in view {self.__class__.__name__}")

        return qs


# --- میکسین‌های مربوط به اعتبارسنجی و مدیریت خطا ---

class ValidationResponseMixin:
    """
    Mixin to standardize the response format for validation errors.
    """
    def handle_exception(self, exc):
        """
        Overrides the default handle_exception to add more context or logging for validation errors.
        """
        if isinstance(exc, ValidationError):
            # می‌توانید اینجا لاگ کنید یا پاسخ خطا را سفارشی کنید
            logger.warning(f"Validation error in {self.__class__.__name__}: {exc}")
            # ممکن است بخواهید ساختار پاسخ خطا را تغییر دهید
            # exc.detail = {'validation_error': exc.detail} # مثال
        return super().handle_exception(exc)


# --- میکسین‌های مربوط به منطق کسب‌وکار (Business Logic) ---

class AuditLogCreationMixin:
    """
    Mixin to automatically create an audit log entry upon saving an object.
    Requires the view to have access to the request and the object to have an 'owner' field.
    This is a simplified example; a more robust implementation might use signals.
    """
    def perform_create(self, serializer):
        """
        Calls the parent's perform_create and then logs the creation event.
        """
        obj = serializer.save()
        # استفاده از سرویس Core یا تابع مستقیم برای لاگ
        # AuditService.log_event_from_view(serializer, self.request, 'CREATE')
        # یا:
        request = self.request
        AuditService.log_action(
            user=request.user,
            action='CREATE',
            target_model_name=obj._meta.label,
            target_id=obj.id,
            details={'serialized_data': serializer.data}, # ممکن است نیاز به فیلتر کردن داده حساس باشد
            request=request # برای گرفتن IP و User-Agent
        )
        logger.info(f"Object {obj._meta.label} (ID: {obj.id}) created by user {request.user.id}.")

    def perform_update(self, serializer):
        """
        Calls the parent's perform_update and then logs the update event.
        """
        obj = serializer.save()
        request = self.request
        AuditService.log_action(
            user=request.user,
            action='UPDATE',
            target_model_name=obj._meta.label,
            target_id=obj.id,
            details={'updated_fields': list(serializer.validated_data.keys())}, # فقط فیلدهای بروزرسانی شده
            request=request
        )
        logger.info(f"Object {obj._meta.label} (ID: {obj.id}) updated by user {request.user.id}.")

# --- میکسین‌های عمومی ---
class TimestampFilterMixin:
    """
    Mixin to add filtering capabilities based on created_at or updated_at.
    """
    def get_queryset(self):
        qs = super().get_queryset() # فرض: کلاس والد یک get_queryset دارد
        # فیلتر بر اساس بازه زمانی ایجاد
        created_after = self.request.query_params.get('created_after', None)
        created_before = self.request.query_params.get('created_before', None)
        if created_after:
            from django.utils.dateparse import parse_datetime
            dt = parse_datetime(created_after)
            if dt:
                qs = qs.filter(created_at__gte=dt)
        if created_before:
            from django.utils.dateparse import parse_datetime
            dt = parse_datetime(created_before)
            if dt:
                qs = qs.filter(created_at__lte=dt)

        # فیلتر بر اساس بازه زمانی بروزرسانی
        updated_after = self.request.query_params.get('updated_after', None)
        updated_before = self.request.query_params.get('updated_before', None)
        if updated_after:
            from django.utils.dateparse import parse_datetime
            dt = parse_datetime(updated_after)
            if dt:
                qs = qs.filter(updated_at__gte=dt)
        if updated_before:
            from django.utils.dateparse import parse_datetime
            dt = parse_datetime(updated_before)
            if dt:
                qs = qs.filter(updated_at__lte=dt)

        return qs

# --- میکسین برای مدل‌هایی با فیلد is_active ---
class ActiveFilterMixin:
    """
    Mixin to filter queryset for active objects only if requested via query param.
    """
    def get_queryset(self):
        qs = super().get_queryset() # فرض: کلاس والد یک get_queryset دارد
        active_only = self.request.query_params.get('active_only', None)
        if active_only and active_only.lower() in ['true', '1', 'yes']:
            if hasattr(qs.model, 'is_active'):
                qs = qs.filter(is_active=True)
        return qs

# --- میکسین برای افزودن مالکیت خودکار در سریالایزر ---
class SetOwnerOnCreateMixin:
    """
    Mixin for ViewSets or GenericViews to automatically set the 'owner' field
    on the serializer's validated_data during creation.
    Assumes the serializer has an 'owner' field and the model supports it.
    """
    def perform_create(self, serializer):
        """
        Overrides perform_create to inject the current user as the owner.
        """
        user = self.request.user
        # اطمینان از اینکه فیلد owner در validated_data قرار می‌گیرد
        # و از تلاش برای تغییر مالک توسط کاربر جلوگیری می‌کند
        if hasattr(serializer.Meta.model, 'owner') and user.is_authenticated:
            serializer.save(owner=user)
        else:
            # اگر مدل دارای فیلد owner نبود یا کاربر احراز هویت نشده بود، فقط ذخیره کن
            serializer.save()

    def perform_update(self, serializer):
        """
        (Optional) Prevents changing the 'owner' field during updates.
        """
        validated_data = serializer.validated_data
        validated_data.pop('owner', None) # حذف owner از validated_data
        serializer.save()

# --- میکسین برای مدیریت IP ---
class IPWhitelistCheckMixin:
    """
    Mixin to check the client's IP against the user's profile whitelist.
    Requires the user to have a profile with an 'allowed_ips' field.
    """
    def check_ip_against_whitelist(self):
        """
        Checks the client's IP against the allowed list in the user's profile.
        Raises PermissionDenied if not allowed.
        """
        user = self.request.user
        client_ip = get_client_ip(self.request)

        try:
            profile = user.profile
            allowed_ips_str = profile.allowed_ips
            if allowed_ips_str:
                 from apps.core.helpers import validate_ip_list # import داخل تابع برای جلوگیری از حلقه
                 allowed_ips_list = validate_ip_list(allowed_ips_str)
                 if not allowed_ips_list:
                     logger.error(f"Invalid IP list format in profile for user {user.email}.")
                     raise PermissionDenied("Your IP whitelist configuration is invalid.")
                 from apps.core.helpers import is_ip_in_allowed_list # import داخل تابع برای جلوگیری از حلقه
                 is_allowed = is_ip_in_allowed_list(client_ip, allowed_ips_list)
                 if not is_allowed:
                      logger.warning(f"Access denied for user {user.email} from IP {client_ip} (not in whitelist).")
                      raise PermissionDenied("Access denied from this IP address.")
        except AttributeError: # اگر پروفایل وجود نداشت یا فیلد allowed_ips وجود نداشت
             logger.error(f"User {user.email} does not have a profile or allowed_ips field for IP whitelist check.")
             raise PermissionDenied("Your profile is incomplete. Please contact support.")
        except Exception as e:
             logger.error(f"Error checking IP whitelist for user {user.email} from IP {client_ip}: {str(e)}")
             raise PermissionDenied("An error occurred checking your IP permissions.")

    def dispatch(self, request, *args, **kwargs):
        """
        Override dispatch to run the IP check before the main view logic.
        """
        # فقط برای کاربران احراز هویت شده
        if request.user.is_authenticated:
            self.check_ip_against_whitelist()
        return super().dispatch(request, *args, **kwargs)

# --- میکسین برای افزودن اثر دستگاه ---
class AddDeviceFingerprintToContextMixin:
    """
    Mixin to add a device fingerprint to the validated_data or context.
    Useful for tracking and security purposes on owned models.
    """
    def perform_create(self, serializer):
        """
        Adds the device fingerprint to the validated_data before saving.
        Assumes the model has a 'device_fingerprint' field.
        """
        user = self.request.user
        if user.is_authenticated:
            device_fp = generate_device_fingerprint(self.request)
            # اطمینان از اینکه فیلد device_fingerprint در validated_data قرار می‌گیرد
            validated_data = serializer.validated_data
            if hasattr(serializer.Meta.model, 'device_fingerprint'):
                 validated_data['device_fingerprint'] = device_fp
            serializer.save(**validated_data)
        else:
            serializer.save()

    def perform_update(self, serializer):
        """
        (Optional) Adds the device fingerprint during update as well.
        """
        validated_data = serializer.validated_data
        user = self.request.user
        if user.is_authenticated:
            device_fp = generate_device_fingerprint(self.request)
            if hasattr(serializer.Meta.model, 'device_fingerprint'):
                 validated_data['device_fingerprint'] = device_fp
            # owner را حذف کن تا تغییر نکند
            validated_data.pop('owner', None)
            serializer.save(**validated_data)
        else:
            # owner را حذف کن تا تغییر نکند
            validated_data.pop('owner', None)
            serializer.save(**validated_data)

    def get_serializer_context(self):
        """
        Adds device fingerprint to the serializer context (for read operations).
        """
        context = super().get_serializer_context()
        if self.request.user.is_authenticated:
            context['device_fingerprint'] = generate_device_fingerprint(self.request)
        return context

# --- میکسین برای افزودن Trace ID ---
class AddTraceIDToContextMixin:
    """
    Mixin to add a Trace ID from the request headers to the serializer context.
    Useful for MAS monitoring and request tracing.
    """
    def get_serializer_context(self):
        """
        Adds trace_id from request header to the serializer context.
        """
        context = super().get_serializer_context()
        trace_id = self.request.META.get('HTTP_X_TRACE_ID') # یا نام هدر شما
        if trace_id:
            context['trace_id'] = trace_id
        return context

# --- میکسین برای افزودن IP کاربر ---
class AddUserIPToContextMixin:
    """
    Mixin to add the client's IP address from the request to the serializer context.
    Useful for logging or security checks.
    """
    def get_serializer_context(self):
        """
        Adds client IP from request to the serializer context.
        """
        context = super().get_serializer_context()
        ip_addr = get_client_ip(self.request)
        if ip_addr:
            context['client_ip'] = ip_addr
        return context

# --- میکسین برای مدیریت کش ---
class CacheControlMixin:
    """
    Mixin to add basic cache control headers to responses.
    Useful for preventing browser caching of sensitive API responses.
    """
    def dispatch(self, request, *args, **kwargs):
        """
        Adds Cache-Control headers to the response.
        """
        response = super().dispatch(request, *args, **kwargs)
        # مثال: جلوگیری از کش کردن توسط مرورگر و پروکسی
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        return response

# --- میکسین برای افزودن اطلاعات امنیتی ---
class AddSecurityContextMixin:
    """
    Mixin to enrich the serializer context with security-related information.
    """
    def get_serializer_context(self):
        """
        Adds security context like IP, User-Agent, Device Fingerprint to the context.
        """
        context = super().get_serializer_context()
        request = self.request
        if request.user.is_authenticated:
            context['security_context'] = {
                'ip_address': get_client_ip(request),
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                'device_fingerprint': generate_device_fingerprint(request),
            }
        return context


# --- مثال ترکیبی ---
# می‌توانید چندین میکسین را با هم ترکیب کنید
class SecureOwnerFilteredViewSet(OwnerFilterMixin, SecureModelViewSetMixin, viewsets.ModelViewSet):
    """
    یک ViewSet که از میکسین‌های امنیتی و فیلتر مالک استفاده می‌کند.
    مناسب برای مدل‌هایی که از BaseOwnedModel ارث می‌برند.
    """
    pass # منطق اضافی در نیاز باشد می‌تواند اینجا قرار گیرد

# --- مثال استفاده در یک نما ---
# class MySecureView(generics.ListCreateAPIView, SecureAPIViewMixin, OwnerFilterMixin):
#     queryset = MyModel.objects.all()
#     serializer_class = MyModelSerializer
#     # اجازه‌نامه و فیلتر مالک به صورت خودکار اعمال می‌شود

logger.info("Core mixins loaded successfully.")
