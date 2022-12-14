# Generated by Django 4.1.1 on 2022-10-04 12:54

from django.db import migrations, models
import django.db.models.deletion
import nuremberg.core.storages


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0006_documentevidencecode_documentevidenceprefix_documentexhibitcode_documentexhibitcodename'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='documentimage',
            options={'ordering': ['page_number']},
        ),
        migrations.AddField(
            model_name='documentimage',
            name='image',
            field=models.ImageField(blank=True, null=True, storage=nuremberg.core.storages.DocumentStorage()),
        ),
        migrations.AlterField(
            model_name='documentimage',
            name='image_type',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='documents.documentimagetype'),
        ),
        migrations.AlterField(
            model_name='documentimage',
            name='url',
            field=models.CharField(blank=True, db_column='url', max_length=255, null=True),
        ),
        migrations.RenameField(
            model_name='documentimage',
            old_name='url',
            new_name='_url',
        ),
    ]
