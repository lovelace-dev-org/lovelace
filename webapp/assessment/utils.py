from assessment.models import *
from utils.archive import get_archived_instances

def clone_assessment_links(old_instance, new_instance):
    links = AssessmentToExerciseLink.objects.filter(
        instance=old_instance
    )
    for link in links:
        link.id = None
        link.instance = new_instance
        link.save()
        
        
def get_bullets_by_section(link):
    by_section = {}
    if link.revision is None:
        sheet = link.sheet
        bullets = sheet.assessmentbullet_set.get_queryset().order_by("section", "ordinal_number")
    else:
        old_sheet = get_archived_instances(link.sheet, link.revision)
        sheet = old_sheet["self"]
        bullets = old_sheet["assessmentbullet_set"]
        bullets.sort(key=lambda b: (b.section, b.ordinal_number))
    
    for bullet in bullets:
        try:
            by_section[bullet.section][0].append(bullet)
            by_section[bullet.section][1] += bullet.point_value
        except KeyError:
            by_section[bullet.section]= [[bullet], bullet.point_value]
    
    return by_section
