import logging

class LogLevelCap(logging.Filter):

    def filter(self, record):
        return record.levelno <= logging.INFO
