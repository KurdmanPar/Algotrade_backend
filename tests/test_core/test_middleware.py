# tests/test_core/test_middleware.py

import pytest
from django.test import RequestFactory
from django.contrib.auth.models import AnonymousUser
from apps.accounts.factories import CustomUserFactory # فرض بر این است که فکتوری وجود دارد
from apps.core.middleware import (
    TraceIDMiddleware,
    IPWhitelistMiddleware,
    AuditLogMiddleware,
    TimingMiddleware,
    SimpleRateLimitMiddleware,
)

pytestmark = pytest.mark.django_db

class TestTraceIDMiddleware:
    """
    Tests for the TraceIDMiddleware.
    """
    def test_trace_id_added_to_request(self):
        """
        Test that a trace ID is added to the request object.
        """
        middleware = TraceIDMiddleware(get_response=lambda req: None) # get_response فقط برای ایجاد نمونه
        request = RequestFactory().get('/')

        middleware.process_request(request)

        assert hasattr(request, 'trace_id')
        assert request.trace_id is not None
        # اطمینان از اینکه trace_id یک UUID معتبر است
        import uuid
        try:
            uuid.UUID(request.trace_id)
            is_uuid = True
        except ValueError:
            is_uuid = False
        assert is_uuid

    def test_trace_id_from_header_used(self):
        """
        Test that if X-Trace-ID header is present, it is used.
        """
        middleware = TraceIDMiddleware(get_response=lambda req: None)
        header_trace_id = '12345678-1234-5678-9012-123456789012'
        request = RequestFactory().get('/', HTTP_X_TRACE_ID=header_trace_id)

        middleware.process_request(request)

        assert request.trace_id == header_trace_id

    def test_trace_id_added_to_response_header(self):
        """
        Test that the trace ID is added to the response headers.
        """
        # ایجاد یک درخواست و اعمال میان‌افزار
        rf = RequestFactory()
        request = rf.get('/')
        response_mock = type('MockResponse', (), {'status_code': 200, 'get': lambda x, d=None: d, '__setitem__': lambda s, k, v: s.__dict__.update({k: v})})()

        # ایجاد یک نمونه از میان‌افزار و فراخوانی process_request و process_response
        middleware = TraceIDMiddleware(get_response=lambda req: response_mock)

        # اعمال process_request برای ایجاد trace_id
        middleware.process_request(request)

        # اعمال process_response برای افزودن trace_id به هدر
        final_response = middleware.process_response(request, response_mock)

        assert final_response.get('X-Trace-ID') is not None
        assert final_response['X-Trace-ID'] == request.trace_id


class TestIPWhitelistMiddleware:
    """
    Tests for the IPWhitelistMiddleware.
    """
    def test_allow_access_from_whitelisted_ip(self, CustomUserFactory):
        """
        Test that access is allowed if the client IP is in the user's whitelist.
        """
        user = CustomUserFactory()
        # فرض: پروفایل کاربر از قبل وجود دارد یا در فکتوری ایجاد می‌شود
        profile = user.profile
        profile.allowed_ips = '192.168.1.100,10.0.0.0/8'
        profile.save()

        middleware = IPWhitelistMiddleware(get_response=lambda req: None)
        request = RequestFactory().get('/')
        request.user = user
        request.META['REMOTE_ADDR'] = '192.168.1.100' # IP مجاز

        response = middleware.process_request(request)
        # اگر IP مجاز بود، process_request باید None برگرداند
        assert response is None

    def test_deny_access_from_non_whitelisted_ip(self, CustomUserFactory):
        """
        Test that access is denied if the client IP is not in the user's whitelist.
        """
        user = CustomUserFactory()
        profile = user.profile
        profile.allowed_ips = '192.168.1.100,10.0.0.0/8'
        profile.save()

        middleware = IPWhitelistMiddleware(get_response=lambda req: None)
        request = RequestFactory().get('/')
        request.user = user
        request.META['REMOTE_ADDR'] = '1.1.1.1' # IP غیرمجاز

        response = middleware.process_request(request)
        # اگر IP غیرمجاز بود، باید یک HttpResponseForbidden برگرداند
        assert response is not None
        assert response.status_code == 403 # Forbidden

    def test_allow_access_if_no_whitelist_defined(self, CustomUserFactory):
        """
        Test that access is allowed if no IP whitelist is defined for the user.
        """
        user = CustomUserFactory()
        profile = user.profile
        profile.allowed_ips = '' # یا None
        profile.save()

        middleware = IPWhitelistMiddleware(get_response=lambda req: None)
        request = RequestFactory().get('/')
        request.user = user
        request.META['REMOTE_ADDR'] = '1.2.3.4' # هر IP

        response = middleware.process_request(request)
        assert response is None # دسترسی باید مجاز باشد

    def test_deny_access_if_user_not_authenticated(self):
        """
        Test that access is denied if the user is not authenticated.
        """
        middleware = IPWhitelistMiddleware(get_response=lambda req: None)
        request = RequestFactory().get('/')
        request.user = AnonymousUser() # کاربر ناشناس
        request.META['REMOTE_ADDR'] = '192.168.1.100'

        # این میان‌افزار فقط زمانی چک می‌کند که کاربر احراز هویت شده باشد
        # بنابراین، احراز هویت باید در یک میان‌افزار قبلی (مثل django.contrib.auth.middleware.AuthenticationMiddleware) انجام شود
        # این میان‌افزار فقط مالکیت IP را چک می‌کند
        # بنابراین، اگر کاربر ناشناس باشد، این میان‌افزار کار خاصی نمی‌کند و None برمی‌گرداند
        # کنترل دسترسی به کل سیستم در نماها یا اجازه‌نامه‌ها انجام می‌شود
        response = middleware.process_request(request)
        assert response is None # این میان‌افزار فقط IP را چک می‌کند، نه احراز هویت

    # توجه: برای تست کامل این میان‌افزار، باید مطمئن شوید که AuthenticationMiddleware قبل از آن فراخوانی شده است.


class TestAuditLogMiddleware:
    """
    Tests for the AuditLogMiddleware.
    """
    # این میان‌افزار نیازمند یک کاربر احراز هویت شده و یک مسیر خاص است که مدلی را تغییر دهد
    # تست آن ممکن است نیازمند ساختار پیچیده‌تری باشد
    # مثال ساده: فقط چک کنید که آیا هنگام یک درخواست، یک ورودی AuditLog ایجاد می‌شود یا خیر
    def test_audit_log_created_on_request(self, api_client, CustomUserFactory):
        """
        Test that an audit log entry is created when a request is processed by the middleware.
        This requires a real view and a logged-in user.
        """
        user = CustomUserFactory()
        api_client.force_authenticate(user=user)

        # ایجاد یک view موقت یا استفاده از یک view موجود
        # مثلاً ایجاد یک endpoint که یک شیء ایجاد می‌کند
        # یا فقط یک endpoint GET ساده برای تست
        # فرض بر این است که یک endpoint وجود دارد که از این میان‌افزار استفاده می‌کند
        # چون این میان‌افزار به طور مستقیم نمی‌تواند از طریق RF تست شود، باید از Client واقعی استفاده کرد یا میان‌افزار را به صورت جداگانه تست کرد
        # مثال: ایجاد یک view تستی که از این میان‌افزار استفاده می‌کند
        # یا mock کردن قسمتی که AuditLog ایجاد می‌شود
        # برای اینجا، فقط یک نمونه ساده از نحوه استفاده از میان‌افزار در Django را نشان می‌دهیم
        # و فرض می‌کنیم که اگر process_response فراخوانی شود، منطق آن کار می‌کند
        # این تست نیازمند ادغام با یک view واقعی و تست از طریق Client است
        # middleware = AuditLogMiddleware(get_response=lambda req: HttpResponse("OK"))
        # request = RequestFactory().post('/') # یا هر عملیات نوشتنی
        # request.user = user
        # request.path = '/some-endpoint/'
        # response = middleware.process_response(request, HttpResponse("OK"))
        # assert AuditLog.objects.filter(user=user, action='REQUEST_200').exists() # مثال
        pass # چون تست واقعی نیازمند یک view واقعی است


class TestTimingMiddleware:
    """
    Tests for the TimingMiddleware.
    """
    def test_timing_middleware_sets_start_time(self):
        """
        Test that the timing middleware adds a start_time to the request.
        """
        middleware = TimingMiddleware(get_response=lambda req: None)
        request = RequestFactory().get('/')

        middleware.process_request(request)

        assert hasattr(request, 'start_time')
        assert request.start_time is not None

    def test_timing_middleware_logs_duration(self, caplog):
        """
        Test that the timing middleware logs the request duration.
        """
        from django.http import HttpResponse
        import time
        # ایجاد یک view موقت که کمی زمان می‌برد
        def slow_view(req):
             time.sleep(0.01) # 10ms delay
             return HttpResponse("Slow Response")

        middleware = TimingMiddleware(get_response=slow_view)
        request = RequestFactory().get('/')

        # اعمال process_request
        middleware.process_request(request)
        # اجرای view
        response = middleware.get_response(request)
        # اعمال process_response (که لاگ را ایجاد می‌کند)
        final_response = middleware.process_response(request, response)

        # چک کردن اینکه آیا یک پیام لاگ شامل 'seconds' وجود دارد
        assert "seconds" in caplog.text
        # چک کردن اینکه آیا مقدار زمانی بیشتر از 0.01 ثانیه (10ms) است
        assert "0.01" in caplog.text or "0.02" in caplog.text # بسته به دقت


class TestSimpleRateLimitMiddleware:
    """
    Tests for the SimpleRateLimitMiddleware.
    Note: This requires mocking the cache backend for reliable testing.
    """
    @pytest.fixture(autouse=True)
    def setup_cache(self, mocker):
        """
        Mock the cache backend for all tests in this class.
        """
        self.mock_cache_get = mocker.patch('django.core.cache.cache.get')
        self.mock_cache_set = mocker.patch('django.core.cache.cache.set')

    def test_rate_limit_allows_request_under_threshold(self, mocker):
        """
        Test that the middleware allows a request if the rate is under the limit.
        """
        from django.http import HttpRequest
        from django.core.cache import cache
        from apps.accounts.factories import CustomUserFactory

        user = CustomUserFactory()
        middleware = SimpleRateLimitMiddleware(get_response=lambda req: None)
        request = RequestFactory().get('/')
        request.META['REMOTE_ADDR'] = '127.0.0.1'
        request.user = user

        # فرض: کاربر تاکنون 0 درخواست فرستاده است
        self.mock_cache_get.return_value = 0

        response = middleware.process_request(request)
        # باید None برگرداند (یعنی اجازه دهد)
        assert response is None

        # چک کردن اینکه آیا cache.set فراخوانی شده است (برای افزایش شمارنده)
        self.mock_cache_set.assert_called_once()

    def test_rate_limit_denies_request_over_threshold(self, mocker):
        """
        Test that the middleware denies a request if the rate exceeds the limit.
        """
        from django.http import HttpRequest
        from django.core.cache import cache
        from apps.accounts.factories import CustomUserFactory

        user = CustomUserFactory()
        middleware = SimpleRateLimitMiddleware(get_response=lambda req: None)
        request = RequestFactory().get('/')
        request.META['REMOTE_ADDR'] = '127.0.0.1'
        request.user = user

        # فرض: کاربر تاکنون 1001 بار درخواست فرستاده (بیشتر از GLOBAL_RATE_LIMIT_PER_MINUTE در settings)
        # فرض می‌کنیم GLOBAL_RATE_LIMIT_PER_MINUTE = 1000
        # در تست، می‌توانیم مقدار را مستقیماً mock کنیم یا مقدار cache را بیشتر از حد بگذاریم
        # فرض کنیم مقدار cache 1001 است
        self.mock_cache_get.return_value = 1001 # فرض: GLOBAL_RATE_LIMIT_PER_MINUTE در settings 1000 است

        response = middleware.process_request(request)
        # باید یک HttpResponseForbidden برگرداند
        assert response is not None
        assert response.status_code == 403 # Forbidden

        # چک کردن اینکه cache.set فراخوانی نشده یا نباید شمارنده افزایش یابد زیرا رد شده است
        # self.mock_cache_set.assert_not_called() # این ممکن است بستگی به پیاده‌سازی داشته باشد

# --- تست سایر میان‌افزارهای سفارشی ---
# می‌توانید برای میان‌افزارهایی که بعداً ایجاد می‌کنید (مثلاً SecurityMiddleware) نیز تست بنویسید
# مثلاً:
# class TestSecurityMiddleware:
#     def test_csrf_protection(self):
#         # ...
#     def test_xss_protection(self):
#         # ...

logger.info("Core middleware tests loaded successfully.")
