from django.db import models


class AnalystReport(models.Model):
    id = models.AutoField(db_column='RecordID', primary_key=True)
    analyst = models.CharField(db_column='Analyst', max_length=100)
    date = models.DateField(db_column='DateSort')
    date_display = models.CharField(db_column='DateDisplay', max_length=100)
    report = models.CharField(db_column='Report', max_length=15000)

    class Meta:
        managed = False
        db_table = 'tblDocAnalystReports'


class TrialInfo(models.Model):
    id = models.AutoField(db_column='RecordID', primary_key=True)
    name = models.CharField(db_column='TrialName', max_length=200)
    alias = models.CharField(db_column='TrialNameAlias', max_length=200)
    description = models.TextField(db_column='Description')

    class Meta:
        managed = False
        db_table = 'tblTrialsInfo'
