#!/usr/bin/env python3
import json
import random

REPEAT_COUNT = 2

json_template_single = """
{{
    "variables": {{
        "bananas": "{bananas}",
        "oranges": "{oranges}"
    }},
    "answers": [
        {{
            "correct": true,
            "answer_str": "{correct}",
            "is_regex": true,
            "comment": "It seems to me you know how to calculate sums! Great!"
        }},
        {{
            "correct": false,
            "answer_str": "[^\\\\d\\\\s]",
            "is_regex": true,
            "hint": "The answer consists of numbers."
        }}
    ]
}}
"""

json_template_all = """
{{
    "repeats": [
        {repeats}
    ]
}}
"""

repeats = []
for i in range(REPEAT_COUNT):
    bananas = random.randint(0, 1000)
    oranges = random.randint(0, 1000)

    total_fruits = bananas + oranges
    correct = r"^\\s*{total_fruits}\\s*$".format(total_fruits=total_fruits)

    output = json_template_single.format(bananas=bananas, oranges=oranges, correct=correct)
    repeats.append(output)

final = json_template_all.format(repeats=",".join(repeats))

#print(final)
print(json.dumps(json.loads(final)))

