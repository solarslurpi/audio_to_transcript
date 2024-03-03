import logging
import colorlog
import json
import os

def setup_logger():
    """Set up the logger with colorized output"""
    # Create a logger object
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)  # Set the logging level

 # Define log format
    log_format = (
        "%(log_color)s[%(levelname)s]%(reset)s "
        "%(log_color)s%(module)s:%(lineno)d%(reset)s - "
        "%(message_log_color)s%(message)s"
    )
    colors = {
        'DEBUG': 'green',
        'INFO': 'yellow',
        'WARNING': 'purple',
        'ERROR': 'red',
        'CRITICAL': 'bold_red',
    }

    # Create a stream handler (console output)
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.DEBUG)  # Set the logging level for the handler

    # Apply the colorlog ColoredFormatter to the handler
    formatter = colorlog.ColoredFormatter(log_format, log_colors=colors, reset=True,
                                          secondary_log_colors={
                                              'message': {'ERROR': 'red', 'INFO': 'yellow', 'debug': 'green'}
                                          })

    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    return logger


# Setup the logger
# setup_logger()

# # Example usage
# if __name__ == "__main__":
#     logger = logging.getLogger(__name__)
#     logger.info("This is an info message.")
#     logger.error("This is an error message.")
#     logger.ok("This operation was successful.")
