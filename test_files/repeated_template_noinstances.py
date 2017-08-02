#!/usr/bin/env python3
import json

json_template_all = """
{
    "repeats": []
}
"""

final = json_template_all

#print(final)
print(json.dumps(json.loads(final)))
