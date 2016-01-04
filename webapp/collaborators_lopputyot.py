# -*- coding: utf-8 -*-

import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'lovelace.settings'

import datetime
import codecs
from django.db.models import Q
from courses.models import UserFileTaskAnswer
# ea_5__code_return_box

answers = UserFileTaskAnswer.objects.filter(
    Q(task__url_name="lt_5__koodin_palautus") |
    Q(task__url_name="ea_5__code_return_box"),
    answer_date__gt=datetime.datetime(2013,9,10)
)

with codecs.open("collabs", "w", "utf-8") as output:
    for answer in answers:
        u_id = answer.user.userprofile.student_id
        u_name = "%s %s" % (answer.user.first_name, answer.user.last_name)
        u_email = answer.user.email
        ans_collabs = "%s" % (answer.collaborators)
        line_str = "%s (%s, %s):" % (answer.user, u_id, u_name)
        print line_str + " " * (50 - len(line_str)) + ans_collabs
        output.write(line_str + " " * (50 - len(line_str)) + ans_collabs + "\n")

