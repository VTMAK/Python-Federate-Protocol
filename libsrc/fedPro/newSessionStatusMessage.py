import struct
from enum import Enum
from libsrc.fedPro.fedProMessage import MsgType, FedProMessage

class SessionStatus(Enum):
    """Enum representing the status of a session in the Federate Protocol."""
    UNSET = -1
    SUCCESS = 0
    UNSUPPORTED_PROTOCOL_VERSION = 1
    OUT_OF_RESOURCES = 2
    INTERNAL_ERROR = 99


class NewSessionStatusMessage(FedProMessage):
    """Class representing a new session status message in the Federate Protocol."""

    def __init__(self, instance: FedProMessage=FedProMessage(MsgType.INVALID, 0)):
        """
            Description:
                Construct a session status message from an existing FedProMessage or create a new
                one if the supplied instance is size 0 / invalid, defaulting status to
                INTERNAL_ERROR unless payload provides a status code.
            Inputs:
                instance (FedProMessage): Source message (default invalid placeholder) whose payload
                    may contain a 4-byte status integer.
            Outputs:
                None (constructor). Side-effects: sets header fields, my_status enum value.
            Exceptions:
                struct.error if payload size < 4 when unpacking; not explicitly handled.
        """
        if instance.my_msg_size is 0:
            super().__init__(MsgType.CTRL_NEW_SESSION_STATUS, 28)
            self.my_status : SessionStatus = SessionStatus.INTERNAL_ERROR
            return
        self.my_msg_size = instance.my_msg_size
        self.my_msg_type = instance.my_msg_type
        self.my_sequence_num = instance.my_sequence_num
        self.my_session_id = instance.my_session_id
        self.my_last_received_msg = instance.my_last_received_msg
        self.my_payload = instance.my_payload
        self.my_format = ">IIQQI"
        self.my_status : SessionStatus = SessionStatus.INTERNAL_ERROR
        if len(instance.my_payload) > 0:
            self.my_status = SessionStatus(int(struct.unpack(">I", instance.my_payload)[0]))

    def to_bytes(self):
        """
            Description:
                Serialize header plus status enum value into packed bytes.
            Inputs:
                None (uses internal header fields and my_status).
            Outputs:
                bytes for transmission/storage.
            Exceptions:
                struct.error if packing fails (unlikely with fixed types).
        """
        parent_bytes = super().package_bytes()
        return struct.pack('>' + parent_bytes[0] + 'I',\
        *parent_bytes[1], self.my_status.value)

    def from_bytes(self, buffer):
        """
            Description:
                Populate header fields via base class then extract 4-byte status code from payload
                slice and convert to SessionStatus enum.
            Inputs:
                buffer: Sequence like (size_bytes, payload_bytes, ... ) matching base from_bytes.
            Outputs:
                None; updates my_status.
            Exceptions:
                struct.error if payload insufficient for status integer.
        """
        super().from_bytes(buffer)

        self.my_status = SessionStatus(int(struct.unpack(">I", buffer[1][20:])[0]))

    def __str__(self):
        """
            Description:
                Produce a string summarizing base header info and session status enum.
            Inputs:
                None.
            Outputs:
                (str) formatted description.
            Exceptions:
                None.
        """
        out_str = super().__str__()
        out_str += "Session status: " + str(self.my_status) + "\n"
        return out_str

    def clear(self):
        """
            Description:
                Reset message header fields and status enum to class (enum type fallback).
            Inputs:
                None.
            Outputs:
                None.
            Exceptions:
                None.
        """
        super().clear()
        self.my_status = SessionStatus(-1)
