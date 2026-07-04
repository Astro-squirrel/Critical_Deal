import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("games", "0001_initial"),
        ("recommendations", "0002_gameaianalysis"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="UserGameAIAnalysis",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("score", models.PositiveIntegerField(default=0)),
                ("price_score", models.PositiveIntegerField(default=0)),
                ("taste_score", models.PositiveIntegerField(default=0)),
                ("quality_score", models.PositiveIntegerField(default=0)),
                (
                    "decision",
                    models.CharField(
                        choices=[("BUY", "Buy"), ("CONSIDER", "Consider"), ("WAIT", "Wait")],
                        default="WAIT",
                        max_length=20,
                    ),
                ),
                ("recommendation_text", models.TextField()),
                ("price_reason", models.TextField()),
                ("taste_reason", models.TextField()),
                ("pattern_label", models.CharField(default="UNKNOWN", max_length=40)),
                ("pattern_analysis", models.TextField()),
                ("metrics", models.JSONField(blank=True, default=dict)),
                ("input_fingerprint", models.CharField(max_length=64)),
                ("prompt_version", models.CharField(max_length=40)),
                ("generated_at", models.DateTimeField(auto_now=True)),
                ("game", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="user_ai_analyses", to="games.game")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="game_ai_analyses", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-generated_at"],
                "unique_together": {("user", "game")},
                "indexes": [
                    models.Index(fields=["user", "game", "generated_at"], name="recommenda_user_id_48e4b9_idx"),
                    models.Index(fields=["input_fingerprint", "prompt_version"], name="recommenda_input_f_9bc8f6_idx"),
                ],
            },
        ),
    ]
