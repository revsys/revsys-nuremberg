# Generated manually for database schema update
# Adds HLSLDocID field to DocumentText model (column already exists in database)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0021_populate_tblcases_tag_name'),
    ]

    operations = [
        # Note: The HLSLDocID column already exists in tblNurembergFullTexts
        # This migration just adds it to the Django model
        # For unmanaged models, this doesn't modify the database
        migrations.AlterModelOptions(
            name='documenttext',
            options={'managed': False},
        ),
    ]
