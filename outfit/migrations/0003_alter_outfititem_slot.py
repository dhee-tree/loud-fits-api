from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("outfit", "0002_outfit_hidden_reason_outfit_is_hidden"),
    ]

    operations = [
        migrations.AlterField(
            model_name="outfititem",
            name="slot",
            field=models.CharField(
                choices=[("top", "Top"), ("bottom", "Bottom"), ("shoes", "Shoes")],
                max_length=20,
            ),
        ),
    ]
