"""
    Python Federate Protocol © 2025 by MAK Technologies is licensed under CC BY-ND 4.0.
    To view a copy of this license, visit https://creativecommons.org/licenses/by-nd/4.0/
"""
import struct
from FedProProtobuf import FederateAmbassador_pb2
from libsrc.fedPro.fedProMessage import MsgType
from libsrc.fedPro.fedProMessage import FedProMessage

class CallbackRequestMessage(FedProMessage):
    """Class representing a callback request message received from RTI in the Federate Protocol."""
    
    def __init__(self, instance: FedProMessage):
        """
            Description:
                Construct a CallbackRequestMessage either as an empty placeholder (if the provided
                instance is invalid) or by copying header fields and decoding the embedded protobuf
                CallbackRequest payload to extract the HLA message type.
            Inputs:
                instance (FedProMessage): An incoming, already-parsed FedProMessage whose payload may
                    contain a serialized FederateAmbassador_pb2.CallbackRequest.
            Outputs:
                None (initializer). Side-effects: initializes internal fields such as my_msg_size,
                my_msg_type, my_hla_msg_type, my_request_buf, etc.
            Exceptions:
                Potential struct unpacking or protobuf parsing errors (DecodeError) could occur if the
                payload is malformed; these are not explicitly caught here.
        """
        if instance.my_msg_type == MsgType.INVALID or instance.my_msg_size == 0:
            super().__init__(MsgType.HLA_CALLBACK_REQUEST, 24)
            self.my_hla_msg_type = (-1)
            self.my_request_buf = ()
            return
        else:
            self.my_msg_size = instance.my_msg_size
            self.my_msg_type = instance.my_msg_type
            self.my_sequence_num = instance.my_sequence_num
            self.my_session_id = instance.my_session_id
            self.my_last_received_msg = instance.my_last_received_msg
            self.my_hla_msg_type = (-1)
            if len(instance.my_payload) >= 4:
                payload = struct.unpack(f'>{len(instance.my_payload)}s', instance.my_payload)
                callback_request = FederateAmbassador_pb2.CallbackRequest()
                if payload[0] != 0:
                    callback_request.ParseFromString(payload[0])
                    self.my_hla_msg_type = callback_request.ListFields()[0][0].number
                    self.my_request_buf = callback_request
            else:
                self.my_request_buf = None
        self.my_format = ">IIQII"

    def from_bytes(self, buffer):
        """
            Description:
                Populate this message instance from a low-level (size, header, payload) buffer
                representation and decode an embedded CallbackRequest protobuf.
            Inputs:
                buffer (Iterable): Expected format: buffer[0] -> 4-byte size, buffer[1] -> raw bytes
                    containing header + optional payload starting at offset 20.
            Outputs:
                self (CallbackRequestMessage) for chaining.
            Side-effects:
                Mutates internal message header fields and decodes my_request_buf if payload present.
            Exceptions:
                struct.error if buffer segments are shorter than expected.
                Protobuf DecodeError if payload cannot be parsed (not caught explicitly).
        """
        self.my_msg_size = struct.unpack(">I", buffer[0])[0]
        byte_ins = struct.unpack('>IQII', bytes(buffer[1][0:20]))
        self.my_sequence_num = byte_ins[0]
        self.my_session_id = byte_ins[1]
        self.my_last_received_msg = byte_ins[2]
        self.my_msg_type = MsgType.HLA_CALL_RESPONSE
        self.my_hla_msg_type = (-1)
        self.my_request_buf = ()
        if self.my_msg_size > 24:
            #I
            payload = struct.unpack(f'>I{len(buffer[1][24:])}s', buffer[1][20:])
            callback_request = FederateAmbassador_pb2.CallbackRequest()
            if payload[0] != 0:
                callback_request.ParseFromString(payload[1])
                self.my_hla_msg_type = callback_request.ListFields()[0][0].number
                self.my_request_buf = callback_request
                return self
            else:
                print("Empty payload received.")
        return self
    
    def pullfields(self, response, field_holder="", spacer=""):
        """
            Description:
                Recursively walk a protobuf message (and any nested messages) collecting formatted
                lines describing each populated field and its value.
            Inputs:
                response: A protobuf message object supporting ListFields().
                field_holder (str): Accumulator string for recursive aggregation (default empty).
                spacer (str): Indentation string that grows with nesting depth.
            Outputs:
                (str) Aggregated multi-line human-readable description of all fields.
            Exceptions:
                Assumes response has ListFields; AttributeError possible if not a protobuf message.
        """
        for field_desc, field_value in response.ListFields():
            
            if hasattr(field_value, "ListFields"):
                spacer += "    "
                field_holder += (f"{spacer}Field: {field_desc.name} | Value: \n{self.pullfields(field_value, field_holder, spacer)}")
            field_holder += (f"{spacer}Field: {field_desc.name} | Value: {field_value}\n")
        return field_holder
    
    def __str__(self):
        """
            Description:
                Produce a human-readable multi-line string including base message header, derived HLA
                callback type, and recursively listed protobuf payload fields.
            Inputs:
                None (instance method uses internal state: my_hla_msg_type, my_request_buf).
            Outputs:
                (str) Combined formatted description.
            Exceptions:
                If my_request_buf is None or lacks ListFields, pullfields may raise; original code
                assumes a valid parsed protobuf object.
        """
        out_str = super().__str__()
        out_str += "\n============================\n"
        out_str += "HLA Call Response Message Type: " + str(self.my_hla_msg_type) + "\n"
        out_str += self.pullfields(self.my_request_buf)
        out_str += "============================\n"
        return out_str