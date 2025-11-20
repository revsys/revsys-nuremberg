# Generated manually for database schema update
# Adds missing columns to tblCases that were removed in new database dump

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0019_defensedocumentbookcodename_defensedocumentcodename'),
    ]

    operations = [
        # Add TrialName column
        migrations.RunSQL(
            sql="""
                ALTER TABLE tblCases
                ADD COLUMN TrialName varchar(200) NULL;
            """,
            reverse_sql="""
                ALTER TABLE tblCases
                DROP COLUMN TrialName;
            """
        ),
        # Add TrialNameAlias column
        migrations.RunSQL(
            sql="""
                ALTER TABLE tblCases
                ADD COLUMN TrialNameAlias varchar(200) NULL;
            """,
            reverse_sql="""
                ALTER TABLE tblCases
                DROP COLUMN TrialNameAlias;
            """
        ),
        # Add Description column
        migrations.RunSQL(
            sql="""
                ALTER TABLE tblCases
                ADD COLUMN Description TEXT NULL;
            """,
            reverse_sql="""
                ALTER TABLE tblCases
                DROP COLUMN Description;
            """
        ),
        # Add TrialImageCaption column
        migrations.RunSQL(
            sql="""
                ALTER TABLE tblCases
                ADD COLUMN TrialImageCaption varchar(500) NULL;
            """,
            reverse_sql="""
                ALTER TABLE tblCases
                DROP COLUMN TrialImageCaption;
            """
        ),
        # Add Note column
        migrations.RunSQL(
            sql="""
                ALTER TABLE tblCases
                ADD COLUMN Note TEXT NULL;
            """,
            reverse_sql="""
                ALTER TABLE tblCases
                DROP COLUMN Note;
            """
        ),
    ]
