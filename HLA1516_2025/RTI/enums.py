from enum import IntEnum

"""
    Python Federate Protocol © 2025 by MAK Technologies is licensed under CC BY-ND 4.0.
    To view a copy of this license, visit https://creativecommons.org/licenses/by-nd/4.0/
"""

class Enums():
    class AdditionalSettingsResultCode(IntEnum):
        SETTINGS_IGNORED = 0
        SETTINGS_FAILED_TO_PARSE = 1
        SETTINGS_APPLIED = 2
    class CallbackModel(IntEnum):
        HLA_IMMEDIATE = 0
        HLA_EVOKED = 1

    class OrderType(IntEnum):
        RECEIVE = 0
        TIMESTAMP = 1

    class ResignAction(IntEnum):
        UNCONDITIONALLY_DIVEST_ATTRIBUTES = 0
        DELETE_OBJECTS = 1
        CANCEL_PENDING_OWNERSHIP_ACQUISITIONS = 2
        DELETE_OBJECTS_THEN_DIVEST = 3
        CANCEL_THEN_DELETE_THEN_DIVEST = 4
        NO_ACTION = 5
