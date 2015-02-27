#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A very sophisticated Python module that allows the user to print
'Hello, world!' to the screen (or any other place stdout points to).

Instructions:
    $ python hello_world.py
"""

import sys

class HelloWorld():
    """This class allows the user to print 'Hello, world!' to the screen."""
    
    def __init__(self):
        """Initializes the internal values of the object so, that
        'Hello, world!' may be printed to the screen."""
        self._text = "Hello, world!\n"
    
    def printHelloWorld(self, must_hello_world_be_printed=True):
        """This method prints 'Hello, world!' to the screen, if the user
        really wants to allow that functionality to be accessed."""
        if must_hello_world_be_printed == True:
            print(self._text, end='')
        elif must_hello_world_be_printed == False:
            pass

def main():
    """The main program, that prints 'Hello, world!' to the screen and
    after that, exits the program."""
    helloWorldObject = HelloWorld()
    helloWorldObject.printHelloWorld(True)    # Prints 'Hello, world!'
    sys.exit()

if __name__ == "__main__":
    main()
