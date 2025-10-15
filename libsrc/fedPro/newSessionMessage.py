import struct
import libsrc.fedPro.fedProMessage as FedProMsg
from libsrc.fedPro.fedProMessage import FedProMessage

class NewSessionMessage(FedProMessage):
    """Class representing a new session control message in the Federate Protocol."""

    def __init__(self):
        """
            Description:
                Initialize a new session control message with protocol version and format.
            Inputs:
                None.
            Outputs:
                None (constructor). Side-effects: sets type, size, protocol version, format.
            Exceptions:
                None.
        """
        super().__init__(FedProMsg.MsgType.CTRL_NEW_SESSION, 28)
        self.my_protocol_version = 1
        self.my_format = ">IIQQI"

    def __str__(self):
        """
            Description:
                Build a human-readable representation including protocol version.
            Inputs:
                None.
            Outputs:
                (str) formatted string.
            Exceptions:
                None.
        """
        out_str = super().__str__()
        out_str += "Session Protocol Version: " + str(self.my_protocol_version) + "\n"
        return out_str

    def clear(self):
        """
            Description:
                Reset header fields and protocol version to defaults.
            Inputs:
                None.
            Outputs:
                None.
            Exceptions:
                None.
        """
        super().clear()
        self.my_protocol_version = 0

    def to_bytes(self):
        """
            Description:
                Serialize the message to bytes (header + protocol version) using packing.
            Inputs:
                None (uses internal state fields).
            Outputs:
                bytes representing the packed message.
            Exceptions:
                struct.error if packing format mismatch.
        """
        parent_bytes = super().package_bytes()
        return struct.pack('>' + parent_bytes[0] + 'I',\
        *parent_bytes[1], self.my_protocol_version)

    def from_tuple(self, buffer):
        """
            Description:
                Populate fields from a tuple-like buffer containing header and version pieces.
            Inputs:
                buffer: Sequence with indices mapping to size, seq num, session id parts, etc.
            Outputs:
                None; updates internal fields.
            Exceptions:
                struct.error or IndexError if buffer lacks expected elements.
        """
        self.my_msg_size = buffer[0]
        self.my_sequence_num = buffer[1]
        # Combine two 32-bit parts into a 64-bit session id
        self.my_session_id = (buffer[2] << 32) | buffer[3]
        # Protocol version assumed int at buffer[4]
        self.my_protocol_version = buffer[4]

    def from_bytes(self, buffer):
        """
            Description:
                Populate fields from a raw bytes buffer containing full packed structure.
            Inputs:
                buffer (bytes|bytearray): Must match '>IIQQI' layout.
            Outputs:
                None; assigns header and protocol version.
            Exceptions:
                struct.error if buffer length incorrect.
        """
        byte_ins = struct.unpack('>IIQQI', buffer)
        self.my_msg_size = byte_ins[0]
        self.my_sequence_num = byte_ins[1]
        self.my_session_id = byte_ins[2]
        self.my_protocol_version = byte_ins[3]
