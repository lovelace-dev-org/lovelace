import random
CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"\
    "abcdefghijklmnopqrstuvwxyz"\
    "0123456789"
print("".join(random.choice(CHARS) for c in range(80)))
