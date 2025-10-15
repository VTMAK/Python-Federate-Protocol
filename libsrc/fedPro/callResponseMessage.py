
import os
import sys
import struct
from libsrc.fedPro.fedProMessage import MsgType
from libsrc.fedPro.fedProMessage import FedProMessage
# Set the top directory to be two levels higher than the current directory
current_dir = os.path.dirname(os.path.abspath(__file__))
top_dir = os.path.dirname(current_dir)
sys.path.insert(0, top_dir)
from FedProProtobuf import RTIambassador_pb2

class CallResponseMessage(FedProMessage):
    """Class representing a callback request message in the Federate Protocol."""
    
    def __init__(self, instance: FedProMessage = FedProMessage(MsgType.INVALID, 0)):
        """
            Description:
                Initialize a call response message from another FedProMessage instance. If the
                provided instance is invalid/empty, create an empty response shell with size 24 and
                sentinel values. Otherwise copy header fields and parse the embedded CallResponse
                protobuf to determine HLA message type.
            Inputs:
                instance (FedProMessage): Source message containing header + payload (default invalid).
            Outputs:
                None (constructor). Side-effects: sets my_hla_msg_type, my_response_buf, and header
                related members.
            Exceptions:
                struct.error / protobuf DecodeError possible if payload malformed; not explicitly caught.
        """
        self.my_format = ">IIQII"
        if instance.my_msg_type == MsgType.INVALID or instance.my_msg_size == 0:
            super().__init__(MsgType.HLA_CALL_RESPONSE, 24)
            self.my_hla_msg_type = (-1)
            self.my_response_buf = ()
            return
        else:
            self.my_msg_size = instance.my_msg_size
            self.my_msg_type = instance.my_msg_type
            self.my_sequence_num = instance.my_sequence_num
            self.my_session_id = instance.my_session_id
            self.my_last_received_msg = instance.my_last_received_msg
            self.my_hla_msg_type = (-1)
            if len(instance.my_payload) >= 4:
                payload = struct.unpack(f'>I{len(instance.my_payload[4:])}s', instance.my_payload)
                call_response = RTIambassador_pb2.CallResponse()
                if payload[0] != 0:
                    call_response.ParseFromString(payload[1])  # type: ignore[attr-defined]
                    self.my_hla_msg_type = call_response.ListFields()[0][0].number  # type: ignore[attr-defined]
                    self.my_response_buf = call_response
            else:
                self.my_response_buf = None
    
    
    def from_bytes(self, buffer):
        """
            Description:
                Populate this call response from a raw buffer (size + header + payload), parsing an
                embedded CallResponse protobuf if present.
            Inputs:
                buffer: Sequence where buffer[0] holds 4-byte size, buffer[1] contains raw bytes
                    starting with 20-byte header followed by optional payload.
            Outputs:
                self (CallResponseMessage) for chaining.
            Exceptions:
                struct.error if buffer layout invalid; protobuf parsing errors uncaught.
        """
        self.my_msg_size = struct.unpack(">I", buffer[0])[0]
        byte_ins = struct.unpack('>IQII', bytes(buffer[1][0:20]))
        self.my_sequence_num = byte_ins[0]
        self.my_session_id = byte_ins[1]
        self.my_last_received_msg = byte_ins[2]
        self.my_msg_type = MsgType.HLA_CALL_RESPONSE
        self.my_hla_msg_type = (-1)
        self.my_response_buf = ()
        if self.my_msg_size > 24:
            #I
            payload = struct.unpack(f'>I{len(buffer[1][24:])}s', buffer[1][20:])
            call_response = RTIambassador_pb2.CallResponse()
            if payload[0] != 0:
                call_response.ParseFromString(payload[1])  # type: ignore[attr-defined]
                self.my_hla_msg_type = call_response.ListFields()[0][0].number  # type: ignore[attr-defined]
                self.my_response_buf = call_response
                return self
            else:
                print("Empty payload received.")
        return self

    def pullfields(self, response, field_holder="", spacer=""):
        """
            Description:
                Recursively traverse a protobuf message and accumulate a textual listing of all
                populated fields and their values (including nested messages).
            Inputs:
                response: A protobuf message supporting ListFields().
                field_holder (str): Initial accumulator string (default empty).
                spacer (str): Indentation prefix (grows with nesting).
            Outputs:
                (str) aggregated formatted description of message fields.
            Exceptions:
                AttributeError if response lacks ListFields; not caught.
        """
        for field_desc, field_value in response.ListFields():
            
            if hasattr(field_value, "ListFields"):
                spacer += "   "
                field_holder += (f"{spacer}Field: {field_desc.name} | Value: \n{self.pullfields(field_value, field_holder, spacer)}")
            field_holder += (f"{spacer}Field: {field_desc.name} | Value: {field_value}\n")
        return field_holder
    
    def __str__(self):
        """
            Description:
                Build a human-readable representation of the response including header info, decoded
                HLA call response type, and detailed protobuf fields.
            Inputs:
                None (uses internal state: my_hla_msg_type, my_response_buf).
            Outputs:
                (str) multi-line formatted summary.
            Exceptions:
                pullfields may raise if my_response_buf is None or not a protobuf message.
        """
        out_str = super().__str__()
        out_str += "\n============================\n"
        out_str += "HLA Call Response Message Type: " + str(self.my_hla_msg_type) + "\n"
        out_str += self.pullfields(self.my_response_buf)
        out_str += "============================\n"
        return out_str