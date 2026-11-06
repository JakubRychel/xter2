import uuid

from django.conf import settings
from django.db import models
from django.db.models.functions import Lower
from django.core.validators import RegexValidator
from django.utils import timezone


local_handle_validator = RegexValidator(
    regex=r'^(?!\.)(?!.*\.\.)[a-z0-9._]{1,30}(?<!\.)$',
    message='Handle may contain only lowercase letters, digits, "_" and "." '
            '(max 30 characters, no dot at the start/end, no consecutive dots).',
)

class Profile(models.Model):
    # class ProfileType(models.TextChoices):
    #     pass

    id = models.UUIDField(primary_key=True, default=uuid.uuid7, editable=False)
    handle = models.CharField(max_length=255)
    domain = models.CharField(max_length=255, null=True, blank=True)

    display_name = models.CharField(max_length=100, blank=True)
    bio = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                Lower('handle'),
                Lower('domain'),
                nulls_distinct=False,
                name='profiles_profile_unique_handle_domain',
                violation_error_message='This handle is already taken.'
            )
        ]

    def clean(self):
        super().clean()
        if self.domain is None:
            self.handle = self.handle.lower()
            local_handle_validator(self.handle)

    @property
    def is_local(self):
        return self.domain is None

    def __str__(self):
        if self.domain:
            return f'@{self.handle}@{self.domain}'

        return f'@{self.handle}'

class PersonalProfile(Profile):
    pass

class ManagedProfile(Profile):
    members = models.ManyToManyField(
        'PersonalProfile',
        through='ProfileMembership',
        related_name='managed_profiles',
        blank=True
    )

class ProfileMembership(models.Model):
    class Role(models.TextChoices):
        OWNER = 'owner', 'Owner'

    member = models.ForeignKey('PersonalProfile', on_delete=models.CASCADE, related_name='memberships')
    profile = models.ForeignKey('ManagedProfile', on_delete=models.CASCADE, related_name='memberships')
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.OWNER)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['member', 'profile'],
                name='profiles_membership_unique_member_profile'
            )
        ]

    def __str__(self):
        return f'{self.member} → {self.profile} ({self.role})'