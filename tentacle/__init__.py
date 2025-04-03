# !/usr/bin/python
# coding=utf-8
import sys

__package__ = "tentacle"
__version__ = "0.9.30"


def greeting(string, outputToConsole=True):
    """Format a string using preset variables.

    Parameters:
        string (str): The greeting to format as a string with placeholders using the below keywords.
                ex. 'Good {hr}! You are using {modver} with {pyver}.'
                {hr} - Gives the current time of day (morning, afternoon, evening)
                {pyver} - The python interpreter version.
                {modver} - This modules version.
        outputToConsole = Print the greeting.

    Returns:
        (str)

    Example: greeting('Good {hr}! You are using {modver} with {pyver}.')
    """
    import datetime

    h = datetime.datetime.now().hour
    hr = "morning" if 5 <= h < 12 else "afternoon" if h < 18 else "evening"

    pyver = "python v{}.{}.{}".format(
        sys.version_info[0], sys.version_info[1], sys.version_info[2]
    )

    modver = "tentacle v{}".format(__version__)

    result = string.format(hr=hr, pyver=pyver, modver=modver)

    if outputToConsole:
        print(result)
    return result


# --------------------------------------------------------------------------------------------

greeting("Good {hr}! You are using {modver} with {pyver}.")

# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
