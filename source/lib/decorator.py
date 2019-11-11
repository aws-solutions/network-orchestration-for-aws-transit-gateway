import time
from random import randint
from functools import wraps
from lib.logger import Logger

# initialise logger
logger = Logger(loglevel='info')


def try_except_retry(count=3, multiplier=2):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            _count = count
            _seconds = randint(5, 10)
            while _count >= 1:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    logger.warning("{}, Trying again in {} seconds".format(e, _seconds))
                    time.sleep(_seconds)
                    _count -= 1
                    _seconds *= multiplier
                    if _count == 0:
                        logger.error("Retry attempts failed, raising the exception.")
                        raise
            return func(*args, **kwargs)
        return wrapper
    return decorator
