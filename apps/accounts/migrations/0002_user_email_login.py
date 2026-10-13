import apps.accounts.models
from django.db import migrations, models


class Migration(migrations.Migration):
    """Ticket #3 : connexion par email, sans nom d'utilisateur ; champs du profil."""

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.AlterModelManagers(
            name="user",
            managers=[
                ("objects", apps.accounts.models.UserManager()),
            ],
        ),
        migrations.RemoveField(
            model_name="user",
            name="username",
        ),
        migrations.RemoveField(
            model_name="user",
            name="first_name",
        ),
        migrations.RemoveField(
            model_name="user",
            name="last_name",
        ),
        migrations.AlterField(
            model_name="user",
            name="email",
            field=models.EmailField(max_length=254, unique=True, verbose_name="adresse email"),
        ),
        migrations.AddField(
            model_name="user",
            name="display_name",
            field=models.CharField(default="", max_length=50, verbose_name="nom affiché"),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="user",
            name="phone",
            field=models.CharField(blank=True, max_length=20, verbose_name="téléphone"),
        ),
        migrations.AddField(
            model_name="user",
            name="phone_verified",
            field=models.BooleanField(default=False, verbose_name="téléphone vérifié"),
        ),
    ]
