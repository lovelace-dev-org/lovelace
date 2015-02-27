import sys

b = bytes(c for c in range(256))
cp437_string = b.decode('ibm437')

sys.stdout.buffer.write(b)
