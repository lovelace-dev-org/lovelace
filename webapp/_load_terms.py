import pickle
import sys
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "lovelace.settings")

import django
django.setup()

from django.db import transaction
from reversion import revisions as reversion
from courses.models import Term, CourseInstance


def select_instance():
    instances = CourseInstance.objects.all().order_by('id').values_list('id', 'name_fi')

    if len(instances) == 0:
        print("Error: No course instances. Create a course instance first.", file=sys.stderr) 
        sys.exit(1)

    ids = set()
    for iid, name_fi in instances:
        ids.add(int(iid))
        print("{id}: {name}".format(id=iid, name=name_fi))

    while True:
        try:
            selection = int(input("Select instance id: "))
        except ValueError:
            continue
        else:
            if selection in ids:
                break
    return selection


def load_terms(filename):
    try:
        dump_fd = open(filename, "rb")
    except IOError as e:
        print("Error: Couldn't open file {}.".format(filename), file=sys.stderr)
        sys.exit(1)

    try:
        terms = pickle.load(dump_fd)
    except Exception as e:
        print("Error: Couldn't open file {}.".format(filename), file=sys.stderr)
        sys.exit(1)

    # Create a set out of terms to prevent name collisions
    terms_ = set((k, v) for k, v in dict(terms).items())
    return terms_
        

def main(filename):
    terms = load_terms(filename)
    print("{} terms loaded.".format(len(terms)))
    instance = CourseInstance.objects.get(id=select_instance())

    with transaction.atomic(), reversion.create_revision():
        for n, d in terms:
            new_term = Term(instance=instance, name_fi=n, description_fi=d)
            new_term.save()


if __name__ == "__main__":
    try:
        filename = sys.argv[1]
    except IndexError:
        print("Usage: _load_terms.py [termfile]", file=sys.stderr)
        sys.exit(1)
    else:
        main(filename)
