# Generated manually for database schema update
# Restores "Currently being processed." notes for cases without overview pages

from django.db import migrations


def restore_processing_notes(apps, schema_editor):
    """Mark cases without overview pages as 'Currently being processed.'"""
    with schema_editor.connection.cursor() as cursor:
        # Cases 6, 7, 9, 11, 12, 13, 14, 15 don't have overview pages (URL patterns)
        # in content/urls.py, so mark them as "Currently being processed."
        # This prevents the template from showing broken links.
        # Cases 14 and 15 are new in the updated database.
        cases_without_urls = [6, 7, 9, 11, 12, 13, 14, 15]

        for case_id in cases_without_urls:
            cursor.execute(
                "UPDATE tblCases SET Note = %s WHERE CaseID = %s",
                ["Currently being processed.", case_id]
            )


def reverse_processing_notes(apps, schema_editor):
    """Clear the processing notes."""
    with schema_editor.connection.cursor() as cursor:
        cases_without_urls = [6, 7, 9, 11, 12, 13, 14, 15]

        for case_id in cases_without_urls:
            cursor.execute(
                "UPDATE tblCases SET Note = NULL WHERE CaseID = %s",
                [case_id]
            )


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0022_documenttext_add_hlsl_doc_id'),
    ]

    operations = [
        migrations.RunPython(
            restore_processing_notes,
            reverse_processing_notes
        ),
    ]
