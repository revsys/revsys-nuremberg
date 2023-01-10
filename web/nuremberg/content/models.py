from django.db import models


class AnalystReport(models.Model):
    id = models.AutoField(db_column='RecordID', primary_key=True)
    analyst = models.CharField(db_column='Analyst', max_length=100)
    date = models.CharField(db_column='Date', max_length=100)
    report = models.CharField(db_column='Report', max_length=15000)
    updated_at = models.DateTimeField(db_column='RecordUpdated')

    class Meta:
        managed = False
        db_table = 'tblDocAnalystReports'
