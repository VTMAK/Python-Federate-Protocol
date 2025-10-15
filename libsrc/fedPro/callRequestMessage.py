import struct
from libsrc.fedPro.fedProMessage import MsgType
from libsrc.fedPro.fedProMessage import FedProMessage

class CallRequestMessage(FedProMessage):
    """Class representing a callback request message in the Federate Protocol."""
    def __init__(self, request_data):
        """
            Description:
                Initialize a call request with serialized RTI ambassador protobuf payload.
            Inputs:
                request_data: Protobuf message (RTIambassador_pb2.*) supporting ListFields() and
                    SerializeToString(). First populated field determines request type.
            Outputs:
                None (constructor). Side-effects: sets my_request_type, my_request_data, adjusts
                my_msg_size and my_format to include payload length.
            Exceptions:
                Attribute errors if request_data lacks expected protobuf methods; no explicit handling.
        """
        super().__init__(MsgType.HLA_CALL_REQUEST, 24)
        self.my_format = ">IIQII"
        self.my_request_type = request_data.ListFields()[0][0].number
        msg_buff = request_data.SerializeToString()
        self.my_request_data = request_data
        if (msg_buff != 0):
            self.my_msg_size += len(msg_buff)
            self.my_format += f'{len(msg_buff)}s'
        

    def to_bytes(self):
        """
            Description:
                Pack header and serialized protobuf payload into a bytes object for transmission
                or storage.
            Inputs:
                None (uses internal state: my_format, header fields, my_request_data).
            Outputs:
                bytes representing the full message.
            Exceptions:
                struct.error if my_format is inconsistent; protobuf serialization errors possible.
        """
        pbytes = struct.pack(self.my_format, self.my_msg_size, self.my_sequence_num,\
        self.my_session_id, self.my_last_received_msg, int(self.my_msg_type),\
            self.my_request_data.SerializeToString())
        return pbytes

    def from_bytes(self, buffer):
        """
            Description:
                Populate this message instance from a raw buffer containing header and (implicitly)
                a protobuf payload (payload itself not re-parsed here).
            Inputs:
                buffer: Iterable where buffer[0] contains 4-byte size, buffer[1] contains remaining
                    header+payload bytes; expects at least 24 bytes for header.
            Outputs:
                None. Side-effects: sets header fields and request type.
            Exceptions:
                struct.error if buffer slices are shorter than required length.
        """
        byte_ins = struct.unpack('>IIQII', bytes(buffer[1][0:24]))
        self.my_msg_size = struct.unpack(">I", buffer[0])[0]
        self.my_sequence_num = byte_ins[0]
        self.my_session_id = byte_ins[1]
        self.my_last_received_msg = byte_ins[2]
        self.my_msg_type = MsgType(int(byte_ins[3]))
        self.my_request_type = byte_ins[4]

    def __str__(self):
        """
            Description:
                Produce a human-readable string describing message header and payload request type
                plus inline protobuf message if present.
            Inputs:
                None (relies on internal state and my_request_data presence).
            Outputs:
                (str) formatted multi-line description.
            Exceptions:
                None expected; my_request_data string conversion delegated to protobuf object.
        """
        out_str = super().__str__()
        out_str += "-------------------------------\n"
        out_str += f"\nRequest Type: {self.my_request_type}"
        if self.my_request_data:
            out_str += f"\nRequest Data: {self.my_request_data}"
        out_str += "\n-----------------------------\n"
        return out_str
