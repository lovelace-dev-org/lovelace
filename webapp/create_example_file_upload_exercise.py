#!/usr/bin/env python
"""
Create an example file upload exercise for easy testing. With revisions and
translations.
"""

import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "lovelace.settings")

import django
django.setup()

from courses.models import FileUploadExercise, FileExerciseTest, FileExerciseTestStage,\
    FileExerciseTestCommand, FileExerciseTestExpectedStdout, FileExerciseTestExpectedStderr,\
    FileExerciseTestIncludeFile
from courses.models import Hint
from feedback.models import TextfieldFeedbackQuestion, ThumbFeedbackQuestion,\
    StarFeedbackQuestion, MultipleChoiceFeedbackQuestion, MultipleChoiceFeedbackAnswer

####
#### The feedback questions
####

text_feedback = TextfieldFeedbackQuestion.objects.create()

thumb_feedback = ThumbFeedbackQuestion.objects.create()

star_feedback = StarFeedbackQuestion.objects.create()

multi_feedback = MultipleChoiceFeedbackQuestion.objects.create()

choice1 = MultipleChoiceFeedbackAnswer.objects.create()
choice2 = MultipleChoiceFeedbackAnswer.objects.create()
choice3 = MultipleChoiceFeedbackAnswer.objects.create()
choice4 = MultipleChoiceFeedbackAnswer.objects.create()


####
#### The exercise
####

example_exercise = FileUploadExercise.objects.create()
example_exercise.name = ""
example_exercise.content = """
"""
example_exercise.question = ""
example_exercise.default_points = 5
example_exercise.manually_evaluated = True
example_exercise.ask_collaborators = True

example_exercise.feedback_questions = [text_feedback, thumb_feedback, star_feedback, multi_feedback]

example_exercise.tags = ["", "", "", "", "", ""]

####
#### The hints
####

hint1 = Hint.objects.create()
hint1.exercise = example_exercise
hint1.tries_to_unlock = 1
hint1.hint = """Duh?
"""

hint2 = Hint.objects.create()
hint2.exercise = example_exercise
hint2.tries_to_unlock = 10
hint2.hint = """Etkö ihan oikeasti osaa?
"""

hint3 = Hint.objects.create()
hint3.exercise = example_exercise
hint3.tries_to_unlock = 100
hint3.hint = """Idiootti.
"""

####
#### The include files (this exercise)
####

file1 = FileExerciseTestIncludeFile.objects.create()
file1.exercise = example_exercise
file1.name = ""
file1.purpose = ""
file1.fileinfo = ""

file2 = FileExerciseTestIncludeFile.objects.create()
file2.exercise = example_exercise
file2.name = ""
file2.purpose = ""
file2.fileinfo = ""

file3 = FileExerciseTestIncludeFile.objects.create()
file3.exercise = example_exercise
file3.name = ""
file3.purpose = ""
file3.fileinfo = ""

file4 = FileExerciseTestIncludeFile.objects.create()
file4.exercise = example_exercise
file4.name = ""
file4.purpose = ""
file4.fileinfo = ""


####
#### The include files (from instance's pool)
####

#i_file1 = ???
#i_file2 = ???

####
#### The tests
####

### Test 1

test1 = FileExerciseTest.objects.create()
test1.exercise = example_exercise

## Test 1 stages

t1_stage1 = FileExerciseStage.objects.create()
t1_stage2 = FileExerciseStage.objects.create()
t1_stage3 = FileExerciseStage.objects.create()
t1_stage4 = FileExerciseStage.objects.create()

# Test 1, stage 1 commands

t1_s1_cmd1 = FileExerciseCommand.objects.create()
t1_s1_cmd2 = FileExerciseCommand.objects.create()
t1_s1_cmd3 = FileExerciseCommand.objects.create()

# Test 1, stage 2 commands

t1_s1_cmd1 = FileExerciseCommand.objects.create()
t1_s1_cmd2 = FileExerciseCommand.objects.create()
t1_s1_cmd3 = FileExerciseCommand.objects.create()

# Test 1, stage 3 commands

t1_s1_cmd1 = FileExerciseCommand.objects.create()
t1_s1_cmd2 = FileExerciseCommand.objects.create()
t1_s1_cmd3 = FileExerciseCommand.objects.create()

# Test 1, stage 4 commands

t1_s1_cmd1 = FileExerciseCommand.objects.create()
t1_s1_cmd2 = FileExerciseCommand.objects.create()
t1_s1_cmd3 = FileExerciseCommand.objects.create()

### Test 2

test2 = FileExerciseTest.objects.create()
test2.exercise = example_exercise

## Test 2 stages

t2_stage1 = FileExerciseStage.objects.create()
t2_stage2 = FileExerciseStage.objects.create()

### Test 3

test3 = FileExerciseTest.objects.create()
test3.exercise = example_exercise

## Test 3 stages

t3_stage1 = FileExerciseStage.objects.create()
t3_stage2 = FileExerciseStage.objects.create()
