"""
    Python Federate Protocol © 2025 by MAK Technologies is licensed under CC BY-ND 4.0.
    To view a copy of this license, visit https://creativecommons.org/licenses/by-nd/4.0/
"""
import struct
from libsrc.fedPro.fedProMessage import MsgType
from libsrc.fedPro.fedProMessage import FedProMessage
from FedProProtobuf import FederateAmbassador_pb2

class CallbackResponseMessage(FedProMessage):
    """Class representing a callback response message sent to RTI in the Federate Protocol."""

    def __init__(self, sequence_num=-1, succeeded=True):
        """
            Description:
                Initialize a callback response message with sequence number and success state.
            Inputs:
                sequence_num (int): Sequence number to assign to the outgoing response (default -1).
                succeeded (bool): Whether the callback succeeded; drives response payload content.
            Outputs:
                None (constructor). Side-effects: sets header fields and response data.
            Exceptions:
                Relies on protobuf object creation; errors would surface if protobuf classes unavailable.
        """
        super().__init__(MsgType.HLA_CALLBACK_RESPONSE, 24)
        self.my_format = ">IIQII"
        self.my_response_type = 0
        self.my_succeeded = succeeded
        self.my_sequence_num = sequence_num
        self.set_response_data(succeeded)
        return

    def set_response_data(self, succeeded=True):
        """
            Description:
                Populate the protobuf response message fields based on success/failure flag.
            Inputs:
                succeeded (bool): If True sets callbackSucceeded; else sets callbackFailed placeholder.
            Outputs:
                None. Side-effects: updates my_response_data (protobuf) and my_response_type.
            Exceptions:
                Access to protobuf attributes (callbackSucceeded / callbackFailed) assumes generated
                fields exist; attribute errors would occur if schema changes.
        """
        # Create a basic success response
        self.my_response_data = FederateAmbassador_pb2.CallbackResponse()
        if succeeded:
            # Mark as success (protobuf field presence implied)  # type: ignore[attr-defined]
            self.my_response_type = 0  # callbackSucceeded field number
            print("Creating callbackSucceeded response")
        else:
            # For failure, we'd need ExceptionData, but for now keep it simple
            print("Creating basic callback response (no failure handling yet)")
            self.my_response_type = 1  # callbackFailed field number  # type: ignore[attr-defined]

    def to_bytes(self):
        """
            Description:
                Serialize the response message to a packed bytes structure including header and
                serialized protobuf payload.
            Inputs:
                None (uses instance fields: my_format, my_msg_size, sequence/session info, etc.).
            Outputs:
                bytes representing the full wire format for transmission.
            Exceptions:
                struct.error if packing with an unexpected format; protobuf serialization errors if
                response payload invalid.
        """
        response_payload = self.my_response_data.SerializeToString()  # type: ignore[attr-defined]
        pack_format = (self.my_format + f'{len(response_payload)}s')
        pbytes = struct.pack(pack_format, self.my_msg_size, self.my_sequence_num,
                            self.my_session_id, self.my_last_received_msg, int(self.my_msg_type),
                            response_payload)
        return pbytes

    def __str__(self):
        """
            Description:
                Produce a human-readable multi-line summary of response header and data.
            Inputs:
                None (uses internal state including my_response_type, my_succeeded, my_response_data).
            Outputs:
                (str) formatted details for logging/debug.
            Exceptions:
                None expected; relies on protobuf object's default __str__.
        """
        out_str = super().__str__()
        out_str += "-------------------------------\n"
        out_str += f"\nResponse Type: {self.my_response_type}"
        out_str += f"\nSucceeded: {self.my_succeeded}"
        if self.my_response_data:
            out_str += f"\nResponse Data: {self.my_response_data}"
        out_str += "\n-----------------------------\n"
        return out_str