"""
Utils file for utilities that do not depend on any apps.
"""

def get_deadline_urgency(deadline, now):
    if deadline is not None:
        if deadline < now:
            return "past"

        diff = deadline - now
        if diff.days <= 1:
            return "urgent"

        if diff.days <= 7:
            return "near"

        return "normal"
    return ""

