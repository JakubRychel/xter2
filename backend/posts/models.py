import uuid

from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.indexes import GinIndex
from django.db import models
from django.db.models import Q
from django.utils import timezone


class Post(models.Model):
    class Visibility(models.TextChoices):
        PUBLIC = 'public', 'Public'
        UNLISTED = 'unlisted', 'Unlisted'
        FOLLOWERS = 'followers', 'Followers only'
        DIRECT = 'direct', 'Direct'

    id = models.UUIDField(primary_key=True, default=uuid.uuid7, editable=False)

    author = models.ForeignKey(
        'profiles.Profile', on_delete=models.CASCADE, related_name='posts', db_index=False
    )
    created_by = models.ForeignKey(
        'profiles.PersonalProfile', on_delete=models.SET_NULL, null=True, blank=True, related_name='created_posts'
    )

    parent = models.ForeignKey(
        'self', on_delete=models.PROTECT, null=True, blank=True, related_name='replies', db_index=False
    )
    path = ArrayField(models.UUIDField(), default=list, blank=True, editable=False)
    
    visibility = models.CharField(max_length=20, choices=Visibility.choices, default=Visibility.PUBLIC)

    content = models.TextField(blank=True)
    lang = models.CharField(max_length=35, blank=True)
    media = models.ManyToManyField('media.MediaAsset', through='PostMedia', related_name='posts', blank=True)

    uri = models.CharField(max_length=2048, unique=True, null=True, blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    edited_at = models.DateTimeField(null=True, blank=True)
    edited_by = models.ForeignKey(
        'profiles.PersonalProfile', on_delete=models.SET_NULL, null=True, blank=True, related_name='+', db_index=False
    )
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        'profiles.PersonalProfile', on_delete=models.SET_NULL, null=True, blank=True, related_name='+', db_index=False
    )

    class Meta:
        indexes = [
            models.Index(fields=['author', '-created_at'], name='posts_post_author_created_idx'),
            models.Index(fields=['parent', 'created_at'], name='posts_post_parent_created_idx'),
            GinIndex(fields=['path'], name='posts_post_path_gin'),
            models.Index(fields=['edited_by'], condition=Q(edited_by__isnull=False), name='posts_post_edited_by_idx'),
            models.Index(fields=['deleted_by'], condition=Q(deleted_by__isnull=False), name='posts_post_deleted_by_idx'),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(parent__isnull=True, path__len=0) | Q(parent__isnull=False, path__len__gt=0),
                name='posts_post_thread_consistency',
            ),
            models.CheckConstraint(
                condition=Q(deleted_at__isnull=True) | Q(content=''),
                name='posts_post_deleted_has_no_content',
            ),
        ]

    @property
    def is_local(self):
        return self.uri is None

    @property
    def is_reply(self):
        return self.parent_id is not None

    @property
    def is_edited(self):
        return self.edited_at is not None

    @property
    def is_deleted(self):
        return self.deleted_at is not None

    @property
    def root_id(self):
        return self.path[0] if self.path else self.id

    def _fill_path(self):
        if not self._state.adding:
            return

        self.path = [*self.parent.path, self.parent_id] if self.parent_id else []

    def clean(self):
        super().clean()
        self._fill_path()

    def save(self, *args, **kwargs):
        self._fill_path()
        super().save(*args, **kwargs)

    def __str__(self):
        if self.is_deleted:
            return f'{self.author}: [deleted]'
        return f'{self.author}: {self.content[:50]}'


class PostMetrics(models.Model):
    post = models.OneToOneField('Post', on_delete=models.CASCADE, primary_key=True, related_name='metrics')

    replies_count = models.PositiveIntegerField(default=0)
    reposts_count = models.PositiveIntegerField(default=0)
    likes_count = models.PositiveIntegerField(default=0)
    dislikes_count = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f'{self.post_id} metrics'


class PostInteraction(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid7, editable=False)

    profile = models.ForeignKey(
        'profiles.Profile', on_delete=models.CASCADE, related_name='%(class)ss', db_index=False
    )
    created_by = models.ForeignKey(
        'profiles.PersonalProfile', on_delete=models.SET_NULL, null=True, blank=True, related_name='created_%(class)ss'
    )

    post = models.ForeignKey('Post', on_delete=models.CASCADE, related_name='%(class)ss', db_index=False)
    uri = models.CharField(max_length=2048, unique=True, null=True, blank=True)

    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        abstract = True

    @property
    def is_local(self):
        return self.uri is None


class Reaction(PostInteraction):
    class Value(models.TextChoices):
        LIKE = 'like', 'Like'
        DISLIKE = 'dislike', 'Dislike'

    value = models.CharField(max_length=10, choices=Value.choices)

    class Meta:
        indexes = [
            models.Index(fields=['post', 'value', '-created_at'], name='posts_reaction_post_value_idx'),
            models.Index(fields=['profile', 'value', '-created_at'], name='posts_reaction_profile_idx'),
        ]
        constraints =[
            models.UniqueConstraint(fields=['profile', 'post'], name='posts_reaction_unique_profile_post'),
        ]

    def __str__(self):
        return f'{self.profile} {self.value} {self.post_id}'


class Repost(PostInteraction):
    class Meta:
        indexes = [
            models.Index(fields=['post', '-created_at'], name='posts_repost_post_created_idx'),
            models.Index(fields=['profile', '-created_at'], name='posts_repost_profile_idx'),
        ]
        constraints = [
            models.UniqueConstraint(fields=['profile', 'post'], name='posts_repost_unique_profile_post'),
        ]

    def __str__(self):
        return f'{self.profile} repost {self.post_id}'


class PostMedia(models.Model):
    post = models.ForeignKey('Post', on_delete=models.CASCADE, related_name='media_items')
    media = models.OneToOneField('media.MediaAsset', on_delete=models.PROTECT, related_name='post_item')
    position = models.PositiveSmallIntegerField()
    caption = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['post', 'position'], name='posts_postmedia_unique_post_position'),
        ]

    def __str__(self):
        return f'{self.post_id} #{self.position} → {self.media_id}'