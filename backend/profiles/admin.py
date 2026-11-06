from django.contrib import admin

from .models import ManagedProfile, PersonalProfile, Profile, ProfileMembership


class ProfileMembershipInline(admin.TabularInline):
    model = ProfileMembership
    extra = 0
    autocomplete_fields = ('member',)
    readonly_fields = ('created_at',)

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'display_name', 'domain', 'created_at')
    list_filter = (('domain', admin.EmptyFieldListFilter),)
    search_fields = ('handle', 'display_name', 'domain')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('handle',)

    def has_add_permission(self, request):
        return False

@admin.register(PersonalProfile)
class PersonalProfileAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'display_name', 'user', 'created_at')
    list_select_related = ('user',)
    search_fields = ('handle', 'display_name', 'user__email')
    fields = ('handle', 'display_name', 'bio', 'user', 'created_at', 'updated_at')
    readonly_fields = ('user', 'created_at', 'updated_at')
    ordering = ('handle',)

    def has_add_permission(self, request):
        return False

@admin.register(ManagedProfile)
class ManagedProfileAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'display_name', 'created_at')
    search_fields = ('handle', 'display_name')
    fields = ('handle', 'display_name', 'bio', 'created_at', 'updated_at')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('handle',)
    inlines = (ProfileMembershipInline,)