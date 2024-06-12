"""Handle type hinting compatibility between Python 2 and 3.
This is a workaround as `typing` is not a built in module in Python 2.
"""

TYPE_CHECKING = False  # Used for compatibility with the typing module
