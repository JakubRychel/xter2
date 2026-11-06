from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import AdminUserCreationForm, UserChangeForm
from django.core.exceptions import ValidationError

from .models import User
from profiles.models import PersonalProfile

class UserCreationForm(AdminUserCreationForm):
    username = forms.CharField(max_length=30)

    class Meta:
        model = User
        fields = ('email',)

    def clean_username(self):
        handle = self.cleaned_data['username'].lower()

        try:
            PersonalProfile(handle=handle).full_clean()
        except ValidationError as e:
            raise ValidationError(e.messages)

        return handle

    def save(self, commit=True):
        user = super().save(commit=False)
        user.profile = PersonalProfile.objects.create(handle=self.cleaned_data['username'])

        if commit:
            user.save()
            self.save_m2m()

        return user

class UserEditForm(UserChangeForm):
    class Meta:
        model = User
        fields = '__all__'


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    form = UserEditForm
    add_form = UserCreationForm
    ordering = ('email',)
    list_display = ('email', 'username', 'is_staff', 'is_active', 'date_joined')
    list_select_related = ('profile',)
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups')
    search_fields = ('email', 'profile__handle')
    readonly_fields = ('username', 'last_login', 'date_joined')
    fieldsets = (
        (None, {'fields': ('email', 'username', 'password')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {'classes': ('wide',), 'fields': ('email', 'username', 'usable_password', 'password1', 'password2')}),
    )

    @admin.display(description='Username', ordering='profile__handle')
    def username(self, obj):
        return obj.profile.handle