
from logging import Formatter
from logging import Handler
from logging import Logger
from logging import StreamHandler
from logging.handlers import RotatingFileHandler


def make_file_logger(logfile, maxBytes=int(1e7), backupCount=10):
    """Create a logger that mimics the format of Products.LongRequestLogger"""
    if isinstance(logfile, Logger):
        # The Logger is already set up.
        return logfile

    logger = Logger('slowlog')

    if isinstance(logfile, Handler):
        # The Handler is already set up.
        handler = logfile
    else:
        if hasattr(logfile, 'write'):
            # Write to an open file.
            handler = StreamHandler(logfile)
        else:
            # Create a rotating file handler.
            handler = RotatingFileHandler(logfile,
                                          maxBytes=maxBytes,
                                          backupCount=backupCount)
        fmt = Formatter('%(asctime)s - %(message)s')
        handler.setFormatter(fmt)

    logger.addHandler(handler)
    return logger
