from django.db import migrations, models
import django.db.models.deletion

def move_instance_to_link(apps, schema_editor):
    
    InstanceIncludeFile = apps.get_model("courses", "InstanceIncludeFile")
    for ifile in InstanceIncludeFile.objects.all():        
        ifile.course = ifile.instance.course
        ifile.save()

def create_instance_file_links(apps, schema_editor):
    
    InstanceIncludeFile = apps.get_model("courses", "InstanceIncludeFile")
    InstanceIncludeFileToInstanceLink = apps.get_model("courses", "InstanceIncludeFileToInstanceLink")
    CourseInstance = apps.get_model("courses", "CourseInstance")    
    for ifile in InstanceIncludeFile.objects.all():
        for instance in CourseInstance.objects.fiter(course=ifile.course):
            link = InstanceIncludeFileToInstanceLink(
                revision=None,
                instance=instance,
                include_file=ifile
            )
            link.save()



class Migration(migrations.Migration):

    dependencies = [
        # previous migration file
    ]

    operations = [
        
        migrations.RunPython(create_coursemedia_for_file),
        migrations.RunPython(create_coursemedia_for_image),        migrations.RunPython(create_coursemedia_for_video)
        
    ]
