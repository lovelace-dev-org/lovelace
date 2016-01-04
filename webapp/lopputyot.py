# -*- coding: utf-8 -*-

import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'lovelace.settings'

import datetime
import codecs
from django.db.models import Q
from courses.models import FileTaskReturnFile
# ea_5__code_return_box

filenames = FileTaskReturnFile.objects.filter(
    Q(returnable__userfiletaskanswer__task__url_name="lt_5__koodin_palautus") |
    Q(returnable__userfiletaskanswer__task__url_name="ea_5__code_return_box"),
    returnable__userfiletaskanswer__answer_date__gt=datetime.datetime(2013,9,10)
).values_list("fileinfo", flat=True)

with codecs.open("cp-params", "w", "utf-8") as paramfile:
    for fname in filenames:
        print '"%s"' % fname
        paramfile.write('"%s"\n' % fname)

