from django.db import models
from django.utils.functional import cached_property


class AnalystReport(models.Model):
    REPORT_PREFIX = "Document Analyst's Report"

    id = models.AutoField(db_column='RecordID', primary_key=True)
    analyst = models.CharField(db_column='Analyst', max_length=100)
    date = models.DateField(db_column='DateSort')
    date_display = models.CharField(db_column='DateDisplay', max_length=100)
    report = models.CharField(db_column='Report', max_length=15000)

    class Meta:
        managed = False
        db_table = 'tblDocAnalystReports'
        # by default, sort by "date" from newest to older
        ordering = ['-date']

    @cached_property
    def content(self):
        # simple text purging, for more complex stuff we should move to regexes
        result = self.report.strip()
        if result.startswith(self.REPORT_PREFIX):
            result = result[len(self.REPORT_PREFIX) :]
        return result.strip()


class TrialInfo(models.Model):
    id = models.AutoField(db_column='RecordID', primary_key=True)
    name = models.CharField(db_column='TrialName', max_length=200)
    alias = models.CharField(db_column='TrialNameAlias', max_length=200)
    description = models.TextField(db_column='Description')

    class Meta:
        managed = False
        db_table = 'tblTrialsInfo'

    @cached_property
    def image_path(self):
        return f"{self.name.lower().replace(' ', '-')}.jpg"
