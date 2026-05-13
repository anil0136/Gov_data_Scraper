from django.db import models

class UmangScheme(models.Model):
    title = models.CharField(max_length=500)
    description = models.TextField(null=True, blank=True)
    category = models.TextField()
    department = models.TextField(null=True, blank=True)

    url = models.URLField(max_length=2048)

    def __str__(self):
        return self.title
    
class GovService(models.Model):
    title = models.CharField(max_length=500)
    service_type = models.TextField(null=True, blank=True)
    department = models.TextField(null=True, blank=True)

    description = models.TextField(null=True, blank=True)
    url = models.URLField(max_length=2048)

    def __str__(self):
        return self.title
    
class MyScheme(models.Model):
    title = models.CharField(max_length=500)
    description = models.TextField(null=True, blank=True)

    eligibility = models.TextField(null=True, blank=True)
    benefits = models.TextField(null=True, blank=True)

    category = models.TextField()
    ministry = models.TextField(null=True, blank=True)
    department = models.TextField(null=True, blank=True)
    level = models.TextField(null=True, blank=True)
    tags = models.TextField(null=True, blank=True)
    application_process = models.TextField(null=True, blank=True)
    documents = models.TextField(null=True, blank=True)
    references = models.TextField(null=True, blank=True)
    raw_data = models.JSONField(default=dict, blank=True)
    url = models.URLField(max_length=2048)

    def __str__(self):
        return self.title
    
class IndiaScheme(models.Model):
    title = models.CharField(max_length=500)
    description = models.TextField(null=True, blank=True)

    ministry = models.TextField(null=True, blank=True)
    category = models.TextField()

    url = models.URLField(max_length=2048)

    def __str__(self):
        return self.title
    
class Scholarship(models.Model):
    title = models.CharField(max_length=500)
    provider = models.TextField(null=True, blank=True)

    deadline = models.TextField(null=True, blank=True)
    amount = models.TextField(null=True, blank=True)

    image = models.ImageField(upload_to='scholarships/', null=True, blank=True)
    image_url = models.URLField(max_length=2048, null=True, blank=True)

    url = models.URLField(max_length=2048)

    def __str__(self):
        return self.title
    


class Grant(models.Model):
    title = models.CharField(max_length=500)
    organization = models.TextField(null=True, blank=True)

    description = models.TextField(null=True, blank=True)
    funding_amount = models.TextField(null=True, blank=True)

    url = models.URLField(max_length=2048)

    def __str__(self):
        return self.title


class TenderListing(models.Model):
    source = models.CharField(max_length=100)
    external_id = models.CharField(max_length=500, null=True, blank=True)

    title = models.CharField(max_length=500)
    organization = models.TextField(null=True, blank=True)
    location = models.TextField(null=True, blank=True)
    state = models.TextField(null=True, blank=True)
    country = models.TextField(null=True, blank=True)

    status = models.TextField(null=True, blank=True)
    procurement_type = models.TextField(null=True, blank=True)
    category = models.TextField(null=True, blank=True)
    tender_value = models.TextField(null=True, blank=True)

    published_on = models.TextField(null=True, blank=True)
    deadline = models.TextField(null=True, blank=True)

    description = models.TextField(null=True, blank=True)
    source_url = models.URLField(max_length=2048, null=True, blank=True)
    url = models.URLField(max_length=2048)
    raw_data = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"{self.source}: {self.title}"
