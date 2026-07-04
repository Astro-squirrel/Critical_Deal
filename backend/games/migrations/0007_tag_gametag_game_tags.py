import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("games", "0006_relatedproduct_linked_game"),
    ]

    operations = [
        migrations.CreateModel(
            name="Tag",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=80, unique=True)),
            ],
            options={
                "ordering": ["name"],
                "indexes": [models.Index(fields=["name"], name="games_tag_name_idx")],
            },
        ),
        migrations.CreateModel(
            name="GameTag",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("rank", models.PositiveSmallIntegerField(default=0)),
                ("weight", models.PositiveSmallIntegerField(default=0)),
                ("source", models.CharField(choices=[("steam", "Steam")], default="steam", max_length=40)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "game",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="game_tags", to="games.game"),
                ),
                (
                    "tag",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="game_tags", to="games.tag"),
                ),
            ],
            options={
                "ordering": ["rank", "tag__name"],
                "indexes": [
                    models.Index(fields=["game", "rank"], name="games_gt_game_rank_idx"),
                    models.Index(fields=["tag"], name="games_gt_tag_idx"),
                    models.Index(fields=["source"], name="games_gt_source_idx"),
                ],
                "unique_together": {("game", "tag")},
            },
        ),
        migrations.AddField(
            model_name="game",
            name="tags",
            field=models.ManyToManyField(blank=True, related_name="games", through="games.GameTag", to="games.tag"),
        ),
    ]
