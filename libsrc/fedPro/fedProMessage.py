import struct
from enum import Enum

class MsgType(int, Enum):
    """Enumeration of the message types used in the Federate Protocol."""
    UNKNOWN = 0

    #Session Management
    CTRL_NEW_SESSION = 1,
    CTRL_NEW_SESSION_STATUS = 2,
    CTRL_HEARTBEAT = 3,
    CTRL_HEARTBEAT_RESPONSE = 4
    CTRL_TERMINATE_SESSION = 6,
    CTRL_SESSION_TERMINATED = 7,

    #Reconnection
    CTRL_RESUME_REQUEST = 10,
    CTRL_RESUME_STATUS = 11,

    #HLA Calls and Callbacks
    HLA_CALL_REQUEST = 20,
    HLA_CALL_RESPONSE = 21,
    HLA_CALLBACK_REQUEST = 22,
    HLA_CALLBACK_RESPONSE = 23,

    INVALID = 99

class FedProMessage():
    """Base class for all Federate Protocol messages."""

    def __init__(self, msg_type : int = MsgType.UNKNOWN, msg_size = 24):
        """
            Description:
                Construct a base FedPro message with initial header values and empty payload.
            Inputs:
                msg_type (int|MsgType): Enumerated message type value (default MsgType.UNKNOWN).
                msg_size (int): Total message size in bytes (default 24 for header-only messages).
            Outputs:
                None (constructor). Side-effects: Initializes header fields and empty payload.
            Exceptions:
                None expected.
        """
        self.my_format : str = ">IIQQ"
        self.my_msg_type : int = msg_type
        self.my_msg_size : int = msg_size
        self.my_session_id : int = 0
        self.my_sequence_num : int = 0
        self.my_last_received_msg : int = 0
        self.my_payload : bytes = b''

    def __str__(self):
        """
            Description:
                Produce a formatted multi-line string for logging/debug of header fields.
            Inputs:
                None (instance state only).
            Outputs:
                (str) formatted header summary.
            Exceptions:
                None.
        """
        out_str = ""
        out_str = "Federate Protocol Message -\n"
        out_str += f"Message Type: {str(self.my_msg_type)}\n"
        out_str += f"Message Size: {str(self.my_msg_size)}\n"
        out_str += f"Session Id:   {str(self.my_session_id)}\n"
        out_str += f"Sequence Num: {str(self.my_sequence_num)}\n"
        out_str += f"Last Received Message: {str(self.my_last_received_msg)}\n"
        return out_str

    def package_bytes(self):
        """
            Description:
                Provide struct packing information (format string and member list) for header.
            Inputs:
                None.
            Outputs:
                (tuple) -> (format_string: str, member_list: list[int]).
            Exceptions:
                None.
        """
        a_format = 'IIQQ'
        a_member_list = [self.my_msg_size, self.my_sequence_num,\
        self.my_session_id, int(self.my_msg_type)]
        return (a_format, a_member_list)

    def to_bytes(self):
        """
            Description:
                Serialize the header fields to a packed bytes object using network byte order.
            Inputs:
                None.
            Outputs:
                bytes representing the serialized header.
            Exceptions:
                struct.error if values don't match format expectations (unlikely given fixed ints).
        """
        byte_outs = struct.pack('>IIQQ', self.my_msg_size, self.my_sequence_num,\
        self.my_session_id, int(self.my_msg_type))
        return byte_outs

    def from_bytes(self, buffer):
        """
            Description:
                Populate internal fields from a raw buffer (header + optional payload).
            Inputs:
                buffer: Sequence where buffer[0] contains a 4-byte size field and buffer[1] contains
                    at least 20 bytes of header plus optional payload; subsequent buffer items are
                    concatenated to form the rest of the payload.
            Outputs:
                None; updates internal fields and payload if size > 24.
            Exceptions:
                struct.error if buffer segments are too short; not caught here.
        """
        self.my_msg_size = struct.unpack(">I", buffer[0])[0]
        byte_ins = struct.unpack('>IQII', bytes((buffer[1])[0:20]))
        self.my_sequence_num = byte_ins[0]
        self.my_session_id = byte_ins[1]
        self.my_last_received_msg = byte_ins[2]
        self.my_msg_type = MsgType(int(byte_ins[3]))
        if self.my_msg_size > 24:
            self.my_payload = buffer[1][20:] + b''.join(buffer[2:])

    def clear(self):
        """
            Description:
                Reset header fields and payload to default/empty values (object reuse helper).
            Inputs:
                None.
            Outputs:
                None.
            Exceptions:
                None.
        """
        self.my_msg_type = MsgType(0)
        self.my_msg_size = 0
        self.my_session_id = 0
        self.my_sequence_num = 0
        self.my_last_received_msg = 0