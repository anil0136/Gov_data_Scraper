from django.db import models

class UmangScheme(models.Model):
    title = models.CharField(max_length=500)
    description = models.TextField(null=True, blank=True)
    category = models.CharField(max_length=200)
    department = models.CharField(max_length=200, null=True, blank=True)

    url = models.URLField()

    def __str__(self):
        return self.title
    
class GovService(models.Model):
    title = models.CharField(max_length=500)
    service_type = models.CharField(max_length=200, null=True, blank=True)
    department = models.CharField(max_length=200, null=True, blank=True)

    description = models.TextField(null=True, blank=True)
    url = models.URLField()

    def __str__(self):
        return self.title
    
class MyScheme(models.Model):
    title = models.CharField(max_length=500)
    description = models.TextField(null=True, blank=True)

    eligibility = models.TextField(null=True, blank=True)
    benefits = models.TextField(null=True, blank=True)

    category = models.CharField(max_length=200)
    url = models.URLField()

    def __str__(self):
        return self.title
    
class IndiaScheme(models.Model):
    title = models.CharField(max_length=500)
    description = models.TextField(null=True, blank=True)

    ministry = models.CharField(max_length=200, null=True, blank=True)
    category = models.CharField(max_length=200)

    url = models.URLField()

    def __str__(self):
        return self.title
    
class Scholarship(models.Model):
    title = models.CharField(max_length=500)
    provider = models.CharField(max_length=200, null=True, blank=True)

    deadline = models.CharField(max_length=100, null=True, blank=True)
    amount = models.CharField(max_length=100, null=True, blank=True)

    image = models.ImageField(upload_to='scholarships/', null=True, blank=True)
    image_url = models.URLField(null=True, blank=True)

    url = models.URLField()

    def __str__(self):
        return self.title
    


class Grant(models.Model):
    title = models.CharField(max_length=500)
    organization = models.CharField(max_length=200, null=True, blank=True)

    description = models.TextField(null=True, blank=True)
    funding_amount = models.CharField(max_length=100, null=True, blank=True)

    url = models.URLField()

    def __str__(self):
        return self.title


class TenderListing(models.Model):
    source = models.CharField(max_length=100)
    external_id = models.CharField(max_length=200, null=True, blank=True)

    title = models.CharField(max_length=500)
    organization = models.CharField(max_length=255, null=True, blank=True)
    location = models.CharField(max_length=255, null=True, blank=True)
    state = models.CharField(max_length=120, null=True, blank=True)
    country = models.CharField(max_length=120, null=True, blank=True)

    status = models.CharField(max_length=120, null=True, blank=True)
    procurement_type = models.CharField(max_length=120, null=True, blank=True)
    category = models.CharField(max_length=200, null=True, blank=True)
    tender_value = models.CharField(max_length=120, null=True, blank=True)

    published_on = models.CharField(max_length=120, null=True, blank=True)
    deadline = models.CharField(max_length=120, null=True, blank=True)

    description = models.TextField(null=True, blank=True)
    source_url = models.URLField(null=True, blank=True)
    url = models.URLField()
    raw_data = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"{self.source}: {self.title}"
