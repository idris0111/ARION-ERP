from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('myapp', '0010_break_room'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(model_name='pet', name='is_active', field=models.BooleanField(default=True)),
        migrations.AlterField(model_name='pet', name='animal_type', field=models.CharField(max_length=24)),
        migrations.AlterField(model_name='pet', name='personality', field=models.CharField(choices=[('friendly', 'Friendly'), ('funny', 'Funny'), ('calm', 'Calm'), ('energetic', 'Energetic'), ('motivating', 'Motivating'), ('smart', 'Smart'), ('playful', 'Playful'), ('sarcastic-light', 'Sarcastic-Light')], default='friendly', max_length=20)),
        migrations.CreateModel(
            name='PetAppearance',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('body_style', models.CharField(default='classic', max_length=24)),
                ('primary_color', models.CharField(default='sand', max_length=24)),
                ('secondary_color', models.CharField(default='cream', max_length=24)),
                ('eye_color', models.CharField(default='warm', max_length=24)),
                ('ears', models.CharField(default='classic', max_length=24)),
                ('tail', models.CharField(default='classic', max_length=24)),
                ('face_markings', models.CharField(blank=True, max_length=24)),
                ('body_markings', models.CharField(blank=True, max_length=24)),
                ('clothes', models.CharField(blank=True, max_length=24)),
                ('accessory', models.CharField(blank=True, max_length=24)),
                ('room', models.CharField(default='cozy', max_length=24)),
                ('pet', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='appearance', to='myapp.pet')),
            ],
        ),
        migrations.CreateModel(
            name='PetSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('pet_enabled', models.BooleanField(default=True)),
                ('show_mini_pet', models.BooleanField(default=False)),
                ('show_on_all_pages', models.BooleanField(default=False)),
                ('auto_reactions', models.BooleanField(default=True)),
                ('animation_enabled', models.BooleanField(default=True)),
                ('sound_enabled', models.BooleanField(default=False)),
                ('reduced_motion', models.BooleanField(default=False)),
                ('focus_mode_hides_pet', models.BooleanField(default=True)),
                ('default_mode', models.CharField(default='mini', max_length=12)),
                ('preferred_position', models.JSONField(default=dict)),
                ('reminder_frequency', models.CharField(default='NEVER', max_length=12)),
                ('quality', models.CharField(default='balanced', max_length=12)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='pet_settings', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='PetInteraction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('interaction_type', models.CharField(max_length=24)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('pet', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='interactions', to='myapp.pet')),
            ],
        ),
    ]
