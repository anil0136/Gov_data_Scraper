from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("scraper", "0003_scholarship_image_url"),
    ]

    operations = [
        migrations.AddField(
            model_name="myscheme",
            name="application_process",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="myscheme",
            name="department",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="myscheme",
            name="documents",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="myscheme",
            name="level",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name="myscheme",
            name="ministry",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="myscheme",
            name="raw_data",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="myscheme",
            name="references",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="myscheme",
            name="tags",
            field=models.TextField(blank=True, null=True),
        ),
    ]
