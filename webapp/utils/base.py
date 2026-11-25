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

def parent_ordinal_sort(node):
    ordinals = [node.ordinal_number]
    parent_node = node.parentnode
    while parent_node is not None:
        ordinals.insert(0, parent_node.ordinal_number)
        parent_node = parent_node.parentnode
    return ordinals

