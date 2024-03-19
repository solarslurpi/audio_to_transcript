###########################################################################################
# Author: HappyDay Johnson
# Version: 0.01
# Date: 2024-03-20
# Summary: workflow_error_code centralizes error handling in the transcription
# workflow using an `async_error_handler` decorator. The decorator wraps asynchronous functions,
# capturing exceptions and logging detailed error information including stack traces. It
# simplifies error management by automatically handling try/except blocks, enriching error messages
# with operation-specific details, and optionally re-raising exceptions for further handling.
# Additionally, it defines custom exceptions for granular control over workflow-related errors,
# facilitating clearer debugging and error resolution strategies.
#
# License Information: MIT License
#
# Copyright (c) 2024 HappyDay Johnson
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
###########################################################################################

import traceback
from functools import wraps

from logger_code import LoggerBase


async def handle_error(error_message: str=None, operation=None, raise_exception=True):
    """
    Logs an error message with optional operation context and raises a generic exception if specified.

    This function assembles an error message from provided details and logs it using the system's
    logger. If `raise_exception` is True, it raises a generic Exception with the constructed error
    message, allowing for standardized error handling across asynchronous functions.

    Args:
        error_message (str, optional): The error message to log. Defaults to None, which results in 'Error: Unknown'.
        operation (str, optional): The operation during which the error occurred. Defaults to None, indicating an unknown operation.
        raise_exception (bool, optional): Whether to raise an exception after logging the error. Defaults to True.

    Raises:
        Exception: A generic exception with the error message, if `raise_exception` is True.
    """
    logger = LoggerBase.setup_logger('handle_error')
    # Dynamically construct parts of the message based on non-None values
    parts = [
        f"Operation: {operation}" if operation else "Operation: Unknown",
        f"Error: {error_message}" if error_message else "Error: Unknown"
    ]
    err_msg = ". ".join(filter(None, parts))
    logger.error(err_msg)
    # If raise_exception is True, raise a custom exception after logging and updating the status
    if raise_exception:
        exception_message = err_msg
        raise Exception(exception_message) # pylint: disable=broad-exception-raised

def async_error_handler(error_message=None, raise_exception=True):
    """
    Decorator that wraps asynchronous functions for standardized error handling and logging.

    This decorator catches exceptions thrown by the decorated asynchronous function, logs a detailed error
    message including a stack trace, and optionally re-raises the exception. It allows for enriching the
    error message with a custom message or uses the exception's message if none is provided. The detailed
    error message is then logged through a centralized error handling function (`handle_error`), which also
    takes care of logging the operation name and deciding whether to raise a generic exception based on the
    decorator's parameters.

    Args:
        error_message (str, optional): Custom error message to use instead of the exception's message. Defaults to None.
        raise_exception (bool, optional): Whether to re-raise the caught exception after logging. Defaults to True.

    Returns:
        function: A wrapper function that incorporates error handling into the decorated asynchronous function.

    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:    # pylint: disable=broad-exception-caught
                tb_str = traceback.format_exc()
                evolved_error_message = error_message if error_message else str(e)
                detailed_error_message = f"{evolved_error_message}\nTraceback:\n{tb_str}"

                await handle_error(
                    error_message=detailed_error_message,
                    operation=func.__name__,
                    raise_exception=raise_exception
                )

                if raise_exception:
                    raise e
        return wrapper
    return decorator


# TODO: Not sure using the rest of this:
class WorkflowError(Exception):
    """Base class for errors related to workflow operations."""
    def __init__(self, message="An error occurred during workflow operation.", system_error=None):
        if system_error:
            message += f" System Error: {system_error}"
        super().__init__(message)

class WorkflowOperationError(WorkflowError):
    """Specific errors during workflow file operations."""
    def __init__(self, operation=None, detail=None, system_error=None):
        message = "A transcription operation error occurred."
        if operation:
            message = f"Failed to {operation} during transcription operation."
        if detail:
            message += f" Detail: {detail}."
        super().__init__(message, system_error=system_error)
