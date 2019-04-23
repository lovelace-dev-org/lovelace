# not needed, django-model-path-converter takes care of this

from courses.models import Course, CourseInstance, User



class RevisionConverter:
    regex = "\d+|head"
    
    