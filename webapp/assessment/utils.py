import datetime
from assessment.models import AssessmentToExerciseLink
from utils.archive import get_archived_instances


def clone_assessment_links(old_instance, new_instance):
    links = AssessmentToExerciseLink.objects.filter(instance=old_instance)
    for link in links:
        link.id = None
        link.instance = new_instance
        link.save()

def copy_sheet(source_sheet, new_sheet):
    bullets = source_sheet.assessmentbullet_set.get_queryset().all()
    sections = list(source_sheet.assessmentsection_set.get_queryset().all())

    for section in sections:
        section_bullets = list(bullets.filter(section=section))
        section.id = None
        section.sheet = new_sheet
        section.save()
        section.refresh_from_db()
        for bullet in section_bullets:
            bullet.section = section
            bullet.sheet = new_sheet
            bullet.id = None
            bullet.save()


def get_sectioned_sheet(link):
    by_section = {}
    if link.revision is None:
        sheet = link.sheet
        bullets = list(sheet.assessmentbullet_set.get_queryset().all())
        sections = list(sheet.assessmentsection_set.get_queryset().all())
    else:
        old_sheet = get_archived_instances(link.sheet, link.revision)
        sheet = old_sheet["self"]
        bullets = old_sheet["assessmentbullet_set"]
        sections = old_sheet["assessmentsection_set"]

    sections.sort(key=lambda s: s.ordinal_number)
    bullets.sort(key=lambda b: b.ordinal_number)

    for section in sections:
        by_section[section] = {"bullets": [], "total_points": 0}

    for bullet in bullets:
        by_section[bullet.section]["bullets"].append(bullet)
        by_section[bullet.section]["total_points"] += bullet.point_value

    return sheet, by_section


def serializable_assessment(user, sheet, bullets_by_section, cleaned_data):
    document = {
        "title": sheet.title,
        "author_fn": user.first_name,
        "author_ln": user.last_name,
        "author_uid": user.username,
        "assessment_date": datetime.date.today().strftime("%Y-%m-%d"),
        "assessment_time": datetime.datetime.now().strftime("%H:%M"),
        "sections": [],
        "bullet_index": {},
        "total_score": 0,
        "max_total": 0,
        "correct": cleaned_data["correct"],
        "complete": cleaned_data["complete"],
    }

    for name, section in bullets_by_section.items():
        section_doc = {
            "name": name.title,
            "section_points": 0,
            "max_points": section["total_points"],
            "bullets": [],
        }
        for bullet in section["bullets"]:
            score = cleaned_data[f"bullet-{bullet.id}-points"] or 0
            section_doc["bullets"].append(str(bullet.id))
            section_doc["section_points"] += score
            document["bullet_index"][str(bullet.id)] = {
                "title": bullet.title,
                "tooltip": bullet.tooltip,
                "max_points": bullet.point_value,
                "scored_points": score,
                "comment": cleaned_data[f"bullet-{bullet.id}-comment"],
            }

        document["total_score"] += section_doc["section_points"]
        document["sections"].append(section_doc)
        document["max_total"] += section["total_points"]

    return document
