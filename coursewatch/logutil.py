import logging

class StyleAdapter(logging.LoggerAdapter):
    def __init__(self, logger, extra=None):
        super().__init__(logger, extra or {})

    def log(self, level, msg, *args, **kwargs):
        return super().log(level, msg.format(*args), **kwargs)

def get_logger(name):
    return StyleAdapter(logging.getLogger(name))
