from django.db import migrations, models

def refactor_fields(apps, schema_editor):
    Term = apps.get_model("courses", "Term")
    TermTag = apps.get_model("courses", "TermTag")
    TermAlias = apps.get_model("courses", "TermAlias")
    
    terms = Term.objects.all()
    
    for term in terms:
        alias_list = term.aliases
        tag_list = term.tagarray
        for aname in alias_list:
            alias = TermAlias(
                term=term,
                name=aname
            )
            alias.save()
            
        for tname in tag_list:
            tag = TermTag(
                name=tname
            )
            tag.save()
            term.tags.add(tag)
        
        term.save()

        
class Migration(migrations.Migration):
    dependencies = ('courses', '0005_term_refactor_init'),
    
    operations = [
        migrations.RunPython(refactor_fields),
    ]
    
