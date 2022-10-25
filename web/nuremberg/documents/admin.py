from django.contrib import admin

from .models import (
    Document,
    DocumentImage,
    DocumentPersonalAuthor,
    DocumentsToPersonalAuthors,
    DocumentGroupAuthor,
    PersonalAuthorProperty,
    PersonalAuthorPropertyRank,
)


# Inlines


class DocumentImageInline(admin.TabularInline):
    model = DocumentImage
    fields = ('page_number', 'physical_page_number', 'image_tag')
    readonly_fields = fields
    extra = 0


class PersonalAuthorsInline(admin.StackedInline):
    model = DocumentsToPersonalAuthors
    extra = 0
    verbose_name = "Personal Author"
    classes = ['collapse']


class PersonalAuthorPropertyInline(admin.TabularInline):
    model = PersonalAuthorProperty
    fields = (
        'name',
        'entity',
        'property_rank',
        'personal_author_description',
        'wikidata_id',
    )
    readonly_fields = fields
    extra = 0

    @admin.display(description='Rank')
    def property_rank(self, object):
        return object.rank


# ModelAdmins


class ReadOnlyAdmin(admin.ModelAdmin):
    def get_readonly_fields(self, request, obj=None):
        return [f.name for f in obj._meta.fields]

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class DocumentAdmin(ReadOnlyAdmin):
    list_display = ('id', 'title', 'image_count')
    inlines = [PersonalAuthorsInline, DocumentImageInline]
    ordering = ('-image_count',)
    search_fields = ('title', 'literal_title')
    list_filter = ('language', 'source')


class DocumentGroupAuthorAdmin(ReadOnlyAdmin):
    search_fields = ('name',)


class DocumentPersonalAuthorAdmin(ReadOnlyAdmin):
    list_display = ('full_name', 'title')
    search_fields = ('first_name', 'last_name')
    inlines = [PersonalAuthorPropertyInline]


class PersonalAuthorPropertyRankAdmin(ReadOnlyAdmin):
    list_display = ('name', 'rank', 'instance_count')
    ordering = ('-rank',)
    search_fields = ('name',)


class PersonalAuthorPropertyAdmin(ReadOnlyAdmin):
    list_display = (
        'personal_author',
        'name',
        'entity',
        'rank',
        'personal_author_description',
    )
    list_filter = ('personal_author_name', 'name')
    search_fields = (
        'name',
        'wikidata_id',
        'personal_author_name',
        'personal_author_description',
    )


admin.site.register(Document, DocumentAdmin)
admin.site.register(DocumentImage, ReadOnlyAdmin)
admin.site.register(DocumentPersonalAuthor, DocumentPersonalAuthorAdmin)
admin.site.register(DocumentGroupAuthor, DocumentGroupAuthorAdmin)
admin.site.register(PersonalAuthorProperty, PersonalAuthorPropertyAdmin)
admin.site.register(
    PersonalAuthorPropertyRank, PersonalAuthorPropertyRankAdmin
)
