from django.db import migrations, models
import django.db.models.deletion

def create_coursemedia_for_file(apps, schema_editor):
    File = apps.get_model("courses", "File")
    CourseMedia = apps.get_model("courses", "CourseMedia")
    CourseMediaLink = apps.get_model("courses", "CourseMediaLink")
    for f in File.objects.all():
        cm = CourseMedia(
            name=f.name,
            owner=f.owner
        )
        cm.save()
        f.coursemedia_ptr = cm
        f.save()
        cm_link = CourseMediaLink(
            instance=f.courseinstance,
            media=cm,
        )
        cm_link.save()
        
def create_coursemedia_for_image(apps, schema_editor):
    Image = apps.get_model("courses", "Image")
    CourseMedia = apps.get_model("courses", "CourseMedia")
    CourseMediaLink = apps.get_model("courses", "CourseMediaLink")
    for f in Image.objects.all():
        cm = CourseMedia(
            name=f.name,
            owner=f.owner
        )
        cm.save()
        f.coursemedia_ptr = cm
        f.save()
        cm_link = CourseMediaLink(
            instance=f.courseinstance,
            media=cm,
        )
        cm_link.save()
        
def create_coursemedia_for_video(apps, schema_editor):
    VideoLink = apps.get_model("courses", "VideoLink")
    CourseMedia = apps.get_model("courses", "CourseMedia")
    CourseMediaLink = apps.get_model("courses", "CourseMediaLink")
    for f in VideoLink.objects.all():
        cm = CourseMedia(
            name=f.name,
            owner=f.owner
        )
        cm.save()
        f.coursemedia_ptr = cm
        f.save()
        cm_link = CourseMediaLink(
            instance=f.courseinstance,
            media=cm,
        )
        cm_link.save()


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0010_coursemedia_initial_create'),
    ]

    operations = [
        migrations.RunPython(create_coursemedia_for_file),
        migrations.RunPython(create_coursemedia_for_image),
        migrations.RunPython(create_coursemedia_for_video)
    ]

