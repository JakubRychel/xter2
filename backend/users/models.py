import uuid

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models, transaction
from django.utils import timezone


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, handle, **extra_fields):
        if not email:
            raise ValueError('E-mail address is required')
        if not handle:
            raise ValueError('Handle is required')

        email = self.normalize_email(email).lower()
        profile_model = self.model._meta.get_field('profile').related_model

        with transaction.atomic(using=self._db):
            profile = profile_model(handle=handle)
            profile.full_clean()
            profile.save(using=self._db)

            user = self.model(email=email, profile=profile, **extra_fields)
            user.set_password(password)
            user.save(using=self._db)

        return user

    def create_user(self, email, password=None, handle=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)

        return self._create_user(email, password, handle, **extra_fields)

    def create_superuser(self, email, password=None, handle=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if not extra_fields['is_staff'] or not extra_fields['is_superuser']:
            raise ValueError('Superuser must have is_staff=True and is_superuser=True')

        return self._create_user(email, password, handle, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid7, editable=False)
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    profile = models.OneToOneField('profiles.PersonalProfile', on_delete=models.CASCADE, related_name='user')

    objects = UserManager()

    USERNAME_FIELD = 'email'
    EMAIL_FIELD = 'email'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email