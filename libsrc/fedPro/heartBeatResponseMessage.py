from typing import Optional
from libsrc.fedPro.fedProMessage import MsgType
from libsrc.fedPro.fedProMessage import FedProMessage

class HeartbeatResponseMessage(FedProMessage):
    """Class representing a heartbeat response message in the Federate Protocol."""

    def __init__(self, instance: Optional[FedProMessage] = None):
        """
            Description:
                Initialize a heartbeat response message. If an existing FedProMessage instance is
                supplied, copy its header/payload fields; otherwise create a fresh response with
                default size and type (CTRL_HEARTBEAT_RESPONSE).
            Inputs:
                instance (FedProMessage|None): Optional source message whose fields are cloned.
            Outputs:
                None (constructor). Side-effects: sets header fields, payload, format string, and
                initializes heartbeat sequence number to 0.
            Exceptions:
                None expected; assumes instance, if provided, has the standard FedProMessage attributes.
        """
        super().__init__(MsgType.CTRL_HEARTBEAT_RESPONSE, 32)
        if instance is not None:
            self.my_msg_size = instance.my_msg_size
            self.my_msg_type = instance.my_msg_type
            self.my_sequence_num = instance.my_sequence_num
            self.my_session_id = instance.my_session_id
            self.my_last_received_msg = instance.my_last_received_msg
            self.my_payload = instance.my_payload
            self.my_format = ">IIQQ"
            self.my_heartbeat_sequence_num = 0
