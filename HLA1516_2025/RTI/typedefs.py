"""
    Python Federate Protocol © 2025 by MAK Technologies is licensed under CC BY-ND 4.0.
    To view a copy of this license, visit https://creativecommons.org/licenses/by-nd/4.0/
"""
from operator import add
from HLA1516_2025.RTI.enums import Enums
from HLA1516_2025.RTI.handles import AttributeHandle, ParameterHandle

FederationExecutionInformation = tuple[str, str]
FederationExecutionInformationVector = list[FederationExecutionInformation]

AttributeHandleSet = set[AttributeHandle]

AttributeHandleValueMap = dict[AttributeHandle, bytes]
ParameterHandleValueMap = dict[ParameterHandle, bytes]

class ConfigurationResult():
    configuration_used : bool = False
    address_used : bool = False
    additional_settings_result : Enums.AdditionalSettingsResultCode = Enums.AdditionalSettingsResultCode.SETTINGS_IGNORED
    message : str = ""

    def __init__(self, config_used: bool = False,
                addr_used: bool = False,
                add_settings: Enums.AdditionalSettingsResultCode = Enums.AdditionalSettingsResultCode.SETTINGS_IGNORED,
                message: str = ""):
        self.configuration_used = config_used
        self.address_used = addr_used
        self.additional_settings_result = add_settings
        self.message = message