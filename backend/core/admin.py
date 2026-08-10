from django.contrib import admin

from .models import Membership, Organization, User


class OrganizationAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "legal_name",
        "organization_type",
        "country",
    )
    fields = (
        "name",
        "legal_name",
        "organization_type",
        "description",
        "website",
        "contact_email",
        "phone",
        "address",
        "city",
        "state",
        "country",
    )
    readonly_fields = ("created_at", "updated_at")
    # Show timestamps in admin detail view
    def get_readonly_fields(self, request, obj=None):
        return self.readonly_fields + ("created_at", "updated_at") if obj else self.readonly_fields

admin.site.register(User)
admin.site.register(Organization, OrganizationAdmin)
admin.site.register(Membership)