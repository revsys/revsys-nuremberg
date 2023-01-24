from django.db import models
from django.utils.functional import cached_property


class AnalystReport(models.Model):
    REPORT_PREFIX = "Document Analyst's Report"

    id = models.AutoField(db_column='RecordID', primary_key=True)
    analyst = models.CharField(db_column='Analyst', max_length=100)
    date = models.DateField(db_column='DateSort')
    date_display = models.CharField(db_column='Date', max_length=100)
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
