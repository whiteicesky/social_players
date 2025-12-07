from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("posts", "0003_expand_topics"),
    ]

    operations = [
        migrations.AddField(
            model_name="comment",
            name="attachment",
            field=models.FileField(blank=True, null=True, upload_to="comment_attachments/"),
        ),
    ]
