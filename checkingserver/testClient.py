import bjsonrpc

test1 = {"args": ['python *.py'],
        "input": [],
        "inputfiles" : {},
        }

codes = {"foo.py": "print 'hello World'"}
references = {"hello.py": "print 'Hello World!'"}
tests = [test1]

c = bjsonrpc.connect()
print c.call.checkWithReference(codes, references, tests)
