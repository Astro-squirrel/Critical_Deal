from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("games", "0007_tag_gametag_game_tags"),
    ]

    operations = [
        migrations.AddField(
            model_name="game",
            name="tags_updated_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
