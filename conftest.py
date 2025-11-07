# import sys
# import os
#
# # اضافه کردن پوشه backend به مسیرهای پایتون
# sys.path.append(os.path.abspath(os.path.dirname(__file__)))
# # sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'backend', 'backend\config')))


# backend/conftest.py (نسخه اصلاح شده)

import pytest
from django.conf import settings

@pytest.fixture(scope='session')
def django_db_setup():
    # ما تنظیمات دیتابیس را برای تست ها جایگزین می کنیم
    # اما باید کلیدهای مهمی مانند ATOMIC_REQUESTS را نیز حفظ کنیم
    settings.DATABASES['default'] = {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
        # این خط را به صراحت اضافه می کنیم تا در محیط تست نیز فعال باشد
        'ATOMIC_REQUESTS': True,
    }