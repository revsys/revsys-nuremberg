from django.contrib import admin

from .models import (
    Document,
    DocumentActivity,
    DocumentCase,
    DocumentEvidenceCode,
    DocumentGroupAuthor,
    DocumentImage,
    DocumentImageType,
    DocumentPersonalAuthor,
    DocumentSource,
    DocumentsToPersonalAuthors,
    DocumentText,
    PersonalAuthorProperty,
    PersonalAuthorPropertyRank,
)


# Inlines


class DocumentEvidenceCodeInline(admin.TabularInline):
    model = DocumentEvidenceCode
    classes = ['collapse']


class DocumentImageInline(admin.TabularInline):
    model = DocumentImage
    fields = ('page_number', 'physical_page_number', 'image_tag')
    readonly_fields = fields
    extra = 0
    classes = ['collapse']


class PersonalAuthorsInline(admin.StackedInline):
    model = DocumentsToPersonalAuthors
    extra = 0
    verbose_name = "Personal Author"
    classes = ['collapse']


class PersonalAuthorPropertyInline(admin.TabularInline):
    model = PersonalAuthorProperty
    fields = (
        'name',
        'value',
        'qualifier_with_value',
        'property_rank',
        'personal_author_description',
        'wikidata_id',
    )
    readonly_fields = fields
    extra = 0

    @admin.display(description='Rank')
    def property_rank(self, object):
        return object.rank

    @admin.display(description='Qualifier')
    def qualifier_with_value(self, object):
        if object.qualifier:
            return f'{object.qualifier}: {object.qualifier_value}'


# ModelAdmins


class ReadOnlyAdmin(admin.ModelAdmin):
    def get_readonly_fields(self, request, obj=None):
        return [f.name for f in obj._meta.fields] + list(self.readonly_fields)

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class DocumentAdmin(ReadOnlyAdmin):
    list_display = ('id', 'title', 'image_count')
    inlines = [
        PersonalAuthorsInline,
        DocumentEvidenceCodeInline,
        DocumentImageInline,
    ]
    ordering = ('-image_count',)
    search_fields = ('title', 'literal_title')
    list_filter = ('language', 'source')
    readonly_fields = ['slug']


class DocumentImageAdmin(ReadOnlyAdmin):
    list_filter = ('scale', 'image_type')


class DocumentGroupAuthorAdmin(ReadOnlyAdmin):
    search_fields = ('name',)


class DocumentPersonalAuthorAdmin(ReadOnlyAdmin):
    list_display = ('full_name', 'title')
    search_fields = ('first_name', 'last_name')
    inlines = [PersonalAuthorPropertyInline]


class DocumentTextAdmin(ReadOnlyAdmin):
    list_display = ('title', 'evidence_code_series', 'evidence_code_num')
    list_filter = ['evidence_code_series']
    search_fields = ['evidence_code_tag']


class PersonalAuthorPropertyRankAdmin(ReadOnlyAdmin):
    list_display = ('name', 'rank', 'instance_count')
    ordering = ('-rank',)
    search_fields = ('name',)


class PersonalAuthorPropertyAdmin(ReadOnlyAdmin):
    list_display = (
        'personal_author',
        'name',
        'value',
        'rank',
        'qualifier',
        'qualifier_value',
    )
    list_filter = ('personal_author_name', 'name')
    search_fields = (
        'name',
        'wikidata_id',
        'personal_author_name',
        'personal_author_description',
    )


admin.site.register(Document, DocumentAdmin)
admin.site.register(DocumentActivity, ReadOnlyAdmin)
admin.site.register(DocumentCase, ReadOnlyAdmin)
admin.site.register(DocumentGroupAuthor, DocumentGroupAuthorAdmin)
admin.site.register(DocumentImage, DocumentImageAdmin)
admin.site.register(DocumentImageType, ReadOnlyAdmin)
admin.site.register(DocumentPersonalAuthor, DocumentPersonalAuthorAdmin)
admin.site.register(DocumentSource, ReadOnlyAdmin)
admin.site.register(DocumentText, DocumentTextAdmin)
admin.site.register(PersonalAuthorProperty, PersonalAuthorPropertyAdmin)
admin.site.register(
    PersonalAuthorPropertyRank, PersonalAuthorPropertyRankAdmin
)
