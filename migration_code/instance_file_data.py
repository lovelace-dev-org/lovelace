from django.db import migrations, models
import django.db.models.deletion

def ifile_instance_to_course(apps, schema_editor):
    
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
        
        migrations.RunPython(ifile_instance_to_course),
        migrations.RunPython(create_instance_file_links)        
    ]
