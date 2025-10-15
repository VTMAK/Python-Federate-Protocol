import struct
import libsrc.fedPro.fedProMessage as FedProMsg
from libsrc.fedPro.fedProMessage import FedProMessage

class HeartbeatMessage(FedProMessage):
    """Class representing a heartbeat message in the Federate Protocol."""

    def __init__(self):
        """
            Description:
                Initialize a heartbeat message with default header values and format string.
            Inputs:
                None.
            Outputs:
                None (constructor). Side-effects: sets message type, size, and format.
            Exceptions:
                None expected.
        """
        super().__init__(FedProMsg.MsgType.CTRL_HEARTBEAT, 24)
        self.my_format = ">IIQQ"
        # Initialize protocol version expected by clear(); kept for symmetry with related messages.
        self.my_protocol_version = 0

    def __str__(self):
        """
            Description:
                Provide human-readable representation of heartbeat header fields.
            Inputs:
                None (instance state only).
            Outputs:
                (str) formatted header string.
            Exceptions:
                None.
        """
        out_str = super().__str__()
        return out_str

    def clear(self):
        """
            Description:
                Reset base message fields and heartbeat-specific protocol version.
            Inputs:
                None.
            Outputs:
                None.
            Exceptions:
                None.
        """
        super().clear()
        self.my_protocol_version = 0

    def from_tuple(self, _buffer):
        """
            Description:
                Placeholder for tuple-based population (not implemented).
            Inputs:
                buffer: Expected tuple-like source (unused presently).
            Outputs:
                None.
            Exceptions:
                Not implemented; pass ensures silent no-op.
        """
        return None

    def from_bytes(self, buffer):
        """
            Description:
                Populate heartbeat fields from a raw bytes buffer containing packed header.
            Inputs:
                buffer (bytes|bytearray): Must contain at least struct size for '>IIQQ' (24 bytes).
            Outputs:
                None; updates my_msg_size, my_sequence_num, my_session_id.
            Exceptions:
                struct.error if buffer length insufficient.
        """
        byte_ins = struct.unpack('>IIQQ', buffer)
        self.my_msg_size = byte_ins[0]
        self.my_sequence_num = byte_ins[1]
        self.my_session_id = byte_ins[2]
