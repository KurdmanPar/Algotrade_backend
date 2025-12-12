# apps/core/__init__.py

# این فایل اطمینان می‌دهد که پوشه 'core' به عنوان یک پکیج پایتون شناخته شود.
# در اغلب موارد، محتوای خالی یا فقط این خط کافی است.
# default_app_config = 'apps.core.apps.CoreConfig' # این خط دیگر در Django 3.2+ نیاز نیست و از آن اجتناب می‌شود
# فقط در صورتی که منطق خاصی در شروع پروژه نیاز باشد، می‌توان آن را اینجا قرار داد، اما معمولاً نیاز نیست.
# مثلاً:
# def startup_logic():
#     print("Core app initialized.")

# startup_logic() # فقط اگر واقعاً نیاز باشد

# برای اطمینان از اینکه ماژول‌های درون core (مثل models, views) به درستی بارگذاری شوند،
# معمولاً نیازی به کار خاصی در این فایل نیست، زیرا Django این کار را به طور خودکار انجام می‌دهد.
# این فایل فقط یک پوشه را به یک پکیج تبدیل می‌کند.

# اگر قصد دارید اجزایی از core را مستقیماً از `apps.core` import کنید (مثلاً `from apps.core import exceptions`),
# می‌توانید آن‌ها را در اینجا export کنید:
# from . import exceptions
# from . import helpers
# from . import services
# ...

# اما این کار معمولاً توصیه نمی‌شود مگر اینکه منطقی برای آن وجود داشته باشد.

# برای سادگی و تطابق با استانداردهای پایتون، محتوای این فایل را خالی یا فقط شامل کامنت توضیحات می‌گذاریم.
"""
Core Application Package for the Algorithmic Trading System.

This package provides the foundational models, serializers, views, permissions,
services, tasks, helpers, and other common utilities required across the system.
"""

# اطمینان از اینکه این پکیج به درستی شناسایی می‌شود
__path__ = __import__('pkgutil').extend_path(__path__, __name__)
