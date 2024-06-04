import logging

class LogLevelCap(logging.Filter):

    def filter(self, record):
        return record.startswith("[DEBUG]") or record.startswith("[INFO]")
