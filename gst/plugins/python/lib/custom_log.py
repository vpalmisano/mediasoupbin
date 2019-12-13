# log
import os, logging

def getLogger(name):
    level = min(int(os.environ.get('PYTHON_DEBUG', 0)), 4)
    logging.basicConfig(level=[
        logging.CRITICAL,
        logging.ERROR,
        logging.WARNING,
        logging.INFO,
        logging.DEBUG,
    ][level])
    logger = logging.getLogger(name)
    return logger

logger = getLogger('log')