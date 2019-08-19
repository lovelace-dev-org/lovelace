from django.db import migrations, models
import django.db.models.deletion

def convert_contentgraph(apps, schema_editor):
    ContentGraph = apps.get_model("courses", "ContentGraph")
    Instance = apps.get_model("courses", "CourseInstance")
    
    instances = Instance.objects.all()
    
    for instance in instances:
        contents = instance.contents.all()
        
        for cg in contents:
            cg.pk = None
            cg.instance = instance
            cg.save()
            
    ContentGraph.objects.filter(instance=None).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0009_contentgraph_onetomany_initial'),
    ]

    operations = [
        migrations.RunPython(convert_contentgraph)
    ]
