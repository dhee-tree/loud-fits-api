from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("product", "0004_product_tryon_asset"),
    ]

    operations = [
        migrations.AlterField(
            model_name="product",
            name="category",
            field=models.CharField(
                choices=[("top", "Top"), ("bottom", "Bottom"), ("shoes", "Shoes")],
                max_length=20,
            ),
        ),
    ]
