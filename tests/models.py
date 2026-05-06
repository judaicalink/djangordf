from django.db import models


class SampleModel(models.Model):
    name = models.CharField(max_length=200)
    count = models.IntegerField(default=0)
    ratio = models.FloatField(default=0.0)
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(null=True, blank=True)
    note = models.TextField(null=True, blank=True)
    data = models.BinaryField(null=True, blank=True)

    class Meta:
        app_label = "tests"
