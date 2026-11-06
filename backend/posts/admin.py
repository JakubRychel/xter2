from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.utils.text import Truncator

from media.models import MediaAsset

from .models import Post, PostMedia, Reaction, Repost

class PostMediaInline(admin.TabularInline):
    model = PostMedia
    extra = 0
    fields = ('position', 'media', 'preview', 'caption')
    ordering = ('position',)

    @admin.display(description='Preview')
    def preview(self, obj):
        media = obj.media if obj.media_id else None
        if not media or media.kind != MediaAsset.Kind.IMAGE:
            return '—'

        url = media.file.url if media.file else media.remote_url
        if not url:
            return '—'

        return format_html('<img src="{}" style="max-height: 80px; max-width: 80px;">', url)

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('short_content', 'author', 'visibility', 'is_reply', 'is_deleted', 'created_at')
    list_filter = (
        'visibility',
        ('parent', admin.EmptyFieldListFilter),
        ('deleted_at', admin.EmptyFieldListFilter),
        ('uri', admin.EmptyFieldListFilter)
    )
    list_select_related = ('author',)
    search_fields = ('id', 'content', 'author__handle')
    fieldsets = (
        (None, {'fields': ('id', 'author', 'created_by', 'parent', 'path', 'visibility', 'content', 'lang')}),
        ('Metrics', {'fields': ('metrics_summary',)}),
        ('History', {'fields': ('created_at', 'updated_at', 'edited_at', 'edited_by', 'deleted_at', 'deleted_by')}),
        ('Federation', {'fields': ('uri',)}),
    )
    ordering = ('-created_at',)
    inlines = (PostMediaInline,)

    @admin.display(description='Content', ordering='content')
    def short_content(self, obj):
        return Truncator(obj.content).chars(80) or '—'

    @admin.display(description='Reply', boolean=True)
    def is_reply(self, obj):
        return obj.is_reply

    @admin.display(description='Deleted', boolean=True)
    def is_deleted(self, obj):
        return obj.is_deleted

    @admin.display(description='Metrics')
    def metrics_summary(self, obj):
        metrics = getattr(obj, 'metrics', None)

        if metrics is None:
            return 'Replies: 0 · Reposts: 0 · Likes: 0 · Dislikes: 0'

        return (
            f'Replies: {metrics.replies_count} · Reposts: {metrics.reposts_count} · '
            f'Likes: {metrics.likes_count} · Dislikes: {metrics.dislikes_count}'
        )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class PostInteractionAdmin(admin.ModelAdmin):
    list_select_related = ('profile', 'post')
    list_filter = (('uri', admin.EmptyFieldListFilter),)
    search_fields = ('id', 'profile__handle', 'post__id')
    ordering = ('-created_at',)

    @admin.display(description='Post')
    def post_link(self, obj):
        url = reverse('admin:posts_post_change', args=[obj.post_id])
        return format_html('<a href="{}">{}</a>', url, Truncator(obj.post.content).chars(50) or obj.post_id)

    @admin.display(description='Local', boolean=True)
    def is_local(self, obj):
        return obj.is_local

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(Reaction)
class ReactionAdmin(PostInteractionAdmin):
    list_display = ('profile', 'value', 'post_link', 'is_local', 'created_at')
    list_filter = ('value', *PostInteractionAdmin.list_filter)
    fields = ('id', 'profile', 'created_by', 'post', 'value', 'uri', 'created_at')


@admin.register(Repost)
class RepostAdmin(PostInteractionAdmin):
    list_display = ('profile', 'post_link', 'is_local', 'created_at')
    fields = ('id', 'profile', 'created_by', 'post', 'uri', 'created_at')