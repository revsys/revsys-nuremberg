# Generated manually for database schema update
# Populates TrialName (tag_name) by extracting from Case field

from django.db import migrations
import re


def extract_and_populate_tag_names(apps, schema_editor):
    """Extract tag names from Case field and populate TrialName column."""
    db_alias = schema_editor.connection.alias

    # Get raw connection to execute SQL
    with schema_editor.connection.cursor() as cursor:
        # Fetch all cases
        cursor.execute("SELECT CaseID, `Case` FROM tblCases")
        cases = cursor.fetchall()

        for case_id, case_name in cases:
            if not case_name:
                continue

            # Extract tag name using regex
            # Matches "IMT" or "NMT XX" at the start
            match = re.match(r'^(IMT|NMT\s+\d{1,2})[\.:]\s', case_name)

            if match:
                tag = match.group(1)
                # Normalize "NMT 01" to "NMT 1", keep "NMT 12" as "NMT 12"
                if tag.startswith('NMT'):
                    parts = tag.split()
                    if len(parts) == 2:
                        tag = f"NMT {int(parts[1])}"

                # Update the TrialName column
                cursor.execute(
                    "UPDATE tblCases SET TrialName = %s WHERE CaseID = %s",
                    [tag, case_id]
                )
            else:
                # For cases without standard pattern, use the full name
                # This handles "None Specified" and other special cases
                cursor.execute(
                    "UPDATE tblCases SET TrialName = %s WHERE CaseID = %s",
                    [case_name, case_id]
                )

        # Also populate TrialNameAlias with short_name extraction
        cursor.execute("SELECT CaseID, `Case` FROM tblCases")
        cases = cursor.fetchall()

        for case_id, case_name in cases:
            if not case_name:
                continue

            # Extract short name: split on " -", replace "." with ":", remove leading zeros
            short_name = case_name.split(" -")[0].replace(".", ":").replace(" 0", " ")

            cursor.execute(
                "UPDATE tblCases SET TrialNameAlias = %s WHERE CaseID = %s",
                [short_name, case_id]
            )


def reverse_populate_tag_names(apps, schema_editor):
    """Clear the populated TrialName and TrialNameAlias columns."""
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("UPDATE tblCases SET TrialName = NULL, TrialNameAlias = NULL")


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0020_add_missing_tblcases_columns'),
    ]

    operations = [
        migrations.RunPython(
            extract_and_populate_tag_names,
            reverse_populate_tag_names
        ),
    ]
