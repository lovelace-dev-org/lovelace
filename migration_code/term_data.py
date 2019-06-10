from django.db import migrations, models
import django.db.models.deletion

def term_instance_to_course(apps, schema_editor):

    Term = apps.get_model("courses", "Term")
    for term in Term.objects.all():
        term.course = term.instance.course
        term.save()

def create_instance_term_links(apps, schema_editor):
    
    Term = apps.get_model("courses", "Term")
    TermToInstanceLink = apps.get_model("courses", "TermToInstanceLink")
    CourseInstance = apps.get_model("courses", "CourseInstance")
    
    for term in Term.objecs.all():
        for instance in CourseInstance.objects.filter(course=term.course):
            link = TermToInstanceLink(
                instance=instance,
                revision=None,
                term=term
            )
            link.save()

class Migration(migrations.Migration):

    dependencies = [
        # previous migration file
    ]

    operations = [
        
        migrations.RunPython(term_instance_to_course),
        migrations.RunPython(create_instance_term_links),
    ]

