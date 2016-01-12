# -*- coding: utf-8 -*-
#from django.conf import settings
#settings.configure() # check django source for more detail
# now you can import other django modules
#from django.template import Template, Context
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'lovelace.settings'


from django.db.models import Q
from courses.models import UserAnswer, Evaluation, User, TaskPage
import datetime
sd = datetime.datetime(2013, 9, 1) # Start date
ed = datetime.datetime(2013, 12, 31) # End date
result_filename = "results_s2013.csv"

#useranswers = UserAnswer.objects.filter(evaluation__points__gt=0.0, answer_date__gt=sd, answer_date__lt=ed)
# noissa on nyt kaikki oikeat vastaukset, myös duplikaatit


# 1. kerätään kaikki useranswerit tietyltä ajalta
useranswers_all = UserAnswer.objects.filter(answer_date__gt=sd, answer_date__lt=ed)
#useranswers_correct = useranswers_all.filter(evaluation__points__gt=0.0)
# 2. kerätään kaikki uniikit userit tietyltä ajalta
unique_users = User.objects.filter(useranswer__answer_date__gt=sd, useranswer__answer_date__lt=ed).distinct()
# 3. kerätään kaikki uniikit tehtävät
tf = TaskPage.objects.filter(textfieldtask__usertextfieldtaskanswer__answer_date__gt=sd, textfieldtask__usertextfieldtaskanswer__answer_date__lt=ed).distinct()
rb = TaskPage.objects.filter(radiobuttontask__userradiobuttontaskanswer__answer_date__gt=sd, radiobuttontask__userradiobuttontaskanswer__answer_date__lt=ed).distinct()
cb = TaskPage.objects.filter(checkboxtask__usercheckboxtaskanswer__answer_date__gt=sd, checkboxtask__usercheckboxtaskanswer__answer_date__lt=ed).distinct()
f = TaskPage.objects.filter(filetask__userfiletaskanswer__answer_date__gt=sd, filetask__userfiletaskanswer__answer_date__lt=ed).distinct()

unique_tasks = list(tf) + list(rb) + list(cb) + list(f)

csvrows = []
csvrows.append([""]+[t.name for t in unique_tasks])

for usr in unique_users:
    row = []
    identifier = usr.userprofile.student_id or usr.username
    identifier = unicode(identifier)
    print "\n%s" % identifier
    row.append(identifier)
    for task in unique_tasks:
        task_tried = useranswers_all.filter(
            Q(usertextfieldtaskanswer__task=task) | 
            Q(userradiobuttontaskanswer__task=task) |
            Q(usercheckboxtaskanswer__task=task) |
            Q(userfiletaskanswer__task=task), user=usr)
        tried = bool(task_tried)
        done = "0" if tried else "-"
        if tried:
            task_success = task_tried.filter(evaluation__points__gt=0.0)
            done = "1" if bool(task_success) else "0"
        #print identifier, task, bool(task_tried), bool(task_success)
        print done,
        row.append(done)
    csvrows.append(row)

import csv
#import codecs
#with codecs.open('results.csv', 'wb', 'utf-8') as csvfile:
with open(result_filename, 'wv') as csvfile:
    csvwriter = csv.writer(csvfile)
    for row in csvrows:
        #print [type(s) for s in row]
        csvwriter.writerow([s.encode("utf-8") for s in row])


