# apps/accounts/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, UserProfile

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'

class CustomUserAdmin(UserAdmin):
    inlines = (UserProfileInline,)

    list_display = ('email', 'username_display', 'user_type', 'is_verified', 'is_active', 'is_demo', 'date_joined')
    search_fields = ('email', 'username_display')
    list_filter = ('user_type', 'is_verified', 'is_active', 'is_demo', 'date_joined')

    # تغییر fieldsets برای حذف username و اضافه کردن فیلدهای سفارشی
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
        ('Custom Info', {'fields': ('username_display', 'user_type', 'is_verified', 'is_demo', 'failed_login_attempts', 'locked_until', 'last_login_ip', 'last_login_at')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username_display', 'password1', 'password2', 'user_type', 'is_verified', 'is_active', 'is_demo'),
        }),
    )

    # اطمینان از اینکه مرتب‌سازی بر اساس فیلد موجود است
    ordering = ('email',)

admin.site.register(CustomUser, CustomUserAdmin)