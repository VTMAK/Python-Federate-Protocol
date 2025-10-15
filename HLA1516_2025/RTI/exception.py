"""
    Python Federate Protocol © 2025 by MAK Technologies is licensed under CC BY-ND 4.0.
    To view a copy of this license, visit https://creativecommons.org/licenses/by-nd/4.0/
"""
class BaseException(Exception):
    def __init__(self, message):
        super().__init__(message)
        self._msg = message
    def what(self):
        return self._msg


class FederateNotExecutionMember(BaseException):
    pass
class RTIinternalError(BaseException):
    pass