import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("games", "0005_game_related_products_updated_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="relatedproduct",
            name="linked_game",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="related_product_entries",
                to="games.game",
            ),
        ),
    ]
