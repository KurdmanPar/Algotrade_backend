# apps/core/middleware.py

import logging
import time
import uuid
from django.http import HttpResponseForbidden
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings
from django.core.cache import cache
from django.contrib.auth import get_user_model
from .helpers import is_ip_in_allowed_list # فرض بر این است که تابع وجود دارد
from .models import AuditLog # فرض بر این است که مدل وجود دارد

User = get_user_model()
logger = logging.getLogger(__name__)

class TraceIDMiddleware(MiddlewareMixin):
    """
    Adds a unique Trace ID to each request/response cycle.
    Useful for tracking requests across different agents and services in an MAS.
    """
    def process_request(self, request):
        # ایجاد یا گرفتن Trace ID از هدر
        trace_id = request.META.get('HTTP_X_TRACE_ID') or str(uuid.uuid4())
        request.trace_id = trace_id
        # اضافه کردن Trace ID به لاگ‌ها
        # می‌توانید از logging.Filter یا تغییر در formatter استفاده کنید
        # یا به صورت دستی آن را به کلیدهای لاگ اضافه کنید
        # مثلاً: logger.info(f"Request Trace ID: {request.trace_id}", extra={'trace_id': request.trace_id})
        return None

    def process_response(self, request, response):
        # اضافه کردن Trace ID به هدر پاسخ
        if hasattr(request, 'trace_id'):
            response['X-Trace-ID'] = request.trace_id
        return response


class IPWhitelistMiddleware(MiddlewareMixin):
    """
    Middleware to restrict access based on a user's allowed IP list.
    Checks the user's profile against the request's IP address.
    This should ideally run *after* authentication middleware.
    """
    def process_request(self, request):
        user = getattr(request, 'user', None)

        # فقط برای کاربران احراز هویت شده چک می‌کنیم
        if user and user.is_authenticated:
            try:
                profile = user.profile
                allowed_ips_str = profile.allowed_ips
                if allowed_ips_str:
                    allowed_ips_list = [item.strip() for item in allowed_ips_str.split(',') if item.strip()]
                    client_ip = self.get_client_ip(request)

                    if not is_ip_in_allowed_list(client_ip, allowed_ips_list):
                        logger.warning(f"Access denied for user {user.email} from IP {client_ip}. IP not in whitelist.")
                        # می‌توانید از یک استثنا سفارشی نیز استفاده کنید
                        # raise PermissionDenied("Access denied from this IP address.")
                        return HttpResponseForbidden("Access denied from this IP address.")
            except AttributeError:
                # اگر پروفایل وجود نداشت، فقط لاگ کنید یا اجازه دهید
                logger.warning(f"User {user.email} does not have a profile for IP whitelist check.")
                # اگر وجود پروفایل الزامی است، می‌توانید خطایی ایجاد کنید
                # return HttpResponseBadRequest("User profile not found.")
        # اگر کاربر احراز هویت نشده یا IP مجاز بود، ادامه دهید
        return None

    def get_client_ip(self, request):
        """
        Extracts the real client IP, considering proxies.
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class AuditLogMiddleware(MiddlewareMixin):
    """
    Middleware to log basic request information to the AuditLog model.
    Be cautious with this middleware as it can create a lot of log entries.
    It's often better to log specific actions in views/services rather than all requests.
    """
    def process_response(self, request, response):
        # فقط درخواست‌های احراز هویت شده و نه assetها (CSS, JS) را لاگ می‌کنیم
        user = getattr(request, 'user', None)
        if user and user.is_authenticated and not request.path.startswith(settings.STATIC_URL or '/static/'):
            AuditLog.objects.create(
                user=user,
                action=f"REQUEST_{response.status_code}",
                target_model="HTTPRequest",
                target_id=None, # یا می‌توانید endpoint را ذخیره کنید
                details={
                    'method': request.method,
                    'path': request.path,
                    'status_code': response.status_code,
                    'content_type': response.get('Content-Type', ''),
                },
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                session_key=getattr(request, 'session', {}).get('session_key', ''),
            )
        return response

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class TimingMiddleware(MiddlewareMixin):
    """
    Middleware to measure the time taken to process a request.
    Useful for performance monitoring.
    """
    def process_request(self, request):
        request.start_time = time.time()
        return None

    def process_response(self, request, response):
        if hasattr(request, 'start_time'):
            duration = time.time() - request.start_time
            # لاگ کردن میزان زمان اجرا
            logger.info(f"Request to {request.path} took {duration:.4f} seconds.", extra={'duration': duration})
        return response

# --- مثال: Rate Limiting Middleware ---
# این فقط یک مثال ساده است. برای Rate Limiting حرفه‌ای، از کتابخانه‌هایی مانند django-ratelimit یا celery یا redis استفاده کنید.
class SimpleRateLimitMiddleware(MiddlewareMixin):
    """
    A very basic rate limiter using cache.
    Not suitable for production without significant enhancements.
    """
    def process_request(self, request):
        client_ip = self.get_client_ip(request)
        cache_key = f"rate_limit_{client_ip}"
        current_count = cache.get(cache_key, 0)

        if current_count >= getattr(settings, 'GLOBAL_RATE_LIMIT_PER_MINUTE', 1000):
            logger.warning(f"Rate limit exceeded for IP {client_ip}")
            return HttpResponseForbidden("Rate limit exceeded. Please try again later.")

        # افزایش شمارنده
        cache.set(cache_key, current_count + 1, timeout=60) # 60 ثانیه = 1 دقیقه
        return None

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
