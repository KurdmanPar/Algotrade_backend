# tests/factories/users.py
import factory
from django.contrib.auth import get_user_model

User = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    # فقط فیلدهایی که در مدل CustomUser وجود دارند را تعریف می‌کنیم
    email = factory.Faker('email')
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    is_active = True
    # فیلد username حذف شد چون در مدل CustomUser وجود ندارد