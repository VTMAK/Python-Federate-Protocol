"""
    Python Federate Protocol © 2025 by MAK Technologies is licensed under CC BY-ND 4.0.
    To view a copy of this license, visit https://creativecommons.org/licenses/by-nd/4.0/
"""
class RtiConfiguration:

    def __init__(self):
        """
            Description: Initialize configuration with default loopback RTI address and empty metadata.
            Inputs: None
            Outputs: None
            Exceptions: None
        """
        self.configuration_name = ""
        self.rti_address = list()
        self.rti_address.append("127.0.0.1")
        self.rti_address.append(5000)  # Assuming rtiAddress is a tuple of (ipAddress, port)
        self.additional_settings = ""

    def createConfiguration(self):
        """
            Description: Factory helper returning a fresh default configuration.
            Inputs: None
            Outputs: RtiConfiguration new instance.
            Exceptions: None
        """
        creation = RtiConfiguration()
        return creation

    def withConfigurationName(self, configurationName):
        """
            Description: Build new configuration with specified name (immutable pattern).
            Inputs:
                configurationName (str): Desired configuration name.
            Outputs: RtiConfiguration new instance with name set.
            Exceptions: None
        """
        creation = RtiConfiguration()
        creation.configuration_name = configurationName
        return creation

    def withRtiAddress(self, rtiAddress):
        """
            Description: Build new configuration using provided RTI address [ip, port].
            Inputs:
                rtiAddress (list|tuple): Address container; element 0 ip string, 1 port int.
            Outputs: RtiConfiguration new instance with address set.
            Exceptions: None (no validation performed).
        """
        creation = RtiConfiguration()
        creation.rti_address = rtiAddress
        return creation

    def withAdditionalSettings(self, additionalSettings):
        """
            Description: Build new configuration with additional settings string.
            Inputs:
                additionalSettings (str): Free-form settings text.
            Outputs: RtiConfiguration new instance with additional_settings set.
            Exceptions: None
        """
        creation = RtiConfiguration()
        creation.additional_settings = additionalSettings
        return creation
    
    def setAddr(self, addr):
        """
            Description: Mutate IP address of existing configuration.
            Inputs:
                addr (str): New IP address.
            Outputs: None
            Exceptions: IndexError if rti_address malformed.
        """
        self.rti_address[0] = addr
    
    def setPort(self, port):
        """
            Description: Mutate port of existing configuration.
            Inputs:
                port (int): New port number.
            Outputs: None
            Exceptions: IndexError if rti_address malformed.
        """
        self.rti_address[1] = port

    def configurationName(self):
        """
            Description: Accessor for configuration name.
            Inputs: None
            Outputs: str configuration name.
            Exceptions: None
        """
        return self.configuration_name

    def rtiAddress(self):
        """
            Description: Accessor for RTI address list [ip, port].
            Inputs: None
            Outputs: list containing IP and port.
            Exceptions: None
        """
        return self.rti_address

    def additionalSettings(self):
        """
            Description: Accessor for additional settings string.
            Inputs: None
            Outputs: str additional settings.
            Exceptions: None
        """
        return self.additional_settings