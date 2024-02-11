import logging
import colorlog
class LoggerBase:
    def  __init__(self):
        pass
    
    @staticmethod
    def setup_logger(name=None):
        """Set up the logger with colorized output."""
        # Since this logger is for logging the status of the transcription task, let's name it if no
        # name is provided.  This way we avoid clutter with the root logger.
        logger_name = 'TranscriptionLogger' if name is None else name
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.DEBUG)  # Set the logging level

        # Check if the logger already has handlers to avoid duplicate messages
        if not logger.handlers:
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
                                                secondary_log_colors={'message': colors})

            stream_handler.setFormatter(formatter)
            logger.addHandler(stream_handler)

        return logger