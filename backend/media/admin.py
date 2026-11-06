from django.contrib import admin
from django.utils.html import format_html

from .models import MediaAsset

@admin.register(MediaAsset)
class MediaAssetAdmin(admin.ModelAdmin):
    list_display = ('id', 'preview_small', 'kind', 'status', 'owner', 'created_at')
    list_filter = ('kind', 'status')
    list_select_related = ('owner',)
    search_fields = ('id', 'owner__handle', 'alt_text')
    autocomplete_fields = ('owner', 'uploaded_by')
    ordering = ('-created_at',)
    fieldsets = (
        (None, {'fields': ('owner', 'uploaded_by', 'kind', 'status', 'file', 'remote_url', 'alt_text')}),
        ('Preview', {'fields': ('preview',)}),
        ('Metadata', {'fields': ('mime_type', 'file_size', 'width', 'height', 'duration', 'blurhash')}),
        ('Dates', {'fields': ('created_at', 'processed_at')}),
    )
    readonly_fields = ('preview', 'mime_type', 'file_size', 'created_at', 'processed_at')

    @admin.display(description='Preview')
    def preview(self, obj):
        return self._image_tag(obj, 300)

    @admin.display(description='Preview')
    def preview_small(self, obj):
        return self._image_tag(obj, 40)

    def _image_tag(self, obj, size):
        if obj.kind != MediaAsset.Kind.IMAGE:
            return '—'

        url = obj.file.url if obj.file else obj.remote_url

        if not url:
            return '—'

        return format_html('<img src="{}" style="max-height: {}px; max-width: {}px;">', url, size, size)

    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)
        initial.setdefault('uploaded_by', request.user.profile.pk)
        initial.setdefault('owner', request.user.profile.pk)
        return initial

    def save_model(self, request, obj, form, change):
        if 'file' in form.changed_data and obj.file:
            obj.file_size = obj.file.size
            obj.mime_type = getattr(obj.file.file, 'content_type', '') or obj.mime_type

        super().save_model(request, obj, form, change)