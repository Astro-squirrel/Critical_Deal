from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("games", "0008_game_tags_updated_at"),
    ]

    operations = [
        migrations.CreateModel(
            name="PlayerSnapshot",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("players", models.PositiveIntegerField(default=0)),
                ("recorded_at", models.DateTimeField()),
                (
                    "source",
                    models.CharField(
                        choices=[("steam", "Steam"), ("steamcharts", "SteamCharts")],
                        default="steam",
                        max_length=40,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "game",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="player_history",
                        to="games.game",
                    ),
                ),
            ],
            options={
                "ordering": ["recorded_at"],
                "unique_together": {("game", "source", "recorded_at")},
            },
        ),
        migrations.AddIndex(
            model_name="playersnapshot",
            index=models.Index(fields=["game", "recorded_at"], name="games_player_game_time_idx"),
        ),
        migrations.AddIndex(
            model_name="playersnapshot",
            index=models.Index(fields=["source", "recorded_at"], name="games_player_source_time_idx"),
        ),
    ]
