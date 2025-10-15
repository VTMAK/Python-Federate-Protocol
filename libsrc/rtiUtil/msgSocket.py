"""
    Python Federate Protocol © 2025 by MAK Technologies is licensed under CC BY-ND 4.0.
    To view a copy of this license, visit https://creativecommons.org/licenses/by-nd/4.0/
"""
from os import error
import struct, socket
from libsrc.rtiUtil.logger import *
from libsrc.rtiUtil import exception
from libsrc.fedPro import fedProMessage

# Wrapper class for a socket used to send and receive fedPro-style messages

class MsgSocket:

    def __init__(self, a_socket = None):
        """
            Description: Initialize message socket wrapper with optional pre-created socket.
            Inputs:
                a_socket (socket.socket | None): Existing connected socket or None to defer connection.
            Outputs: None
            Exceptions: None
        """
        self.my_socket = a_socket
        self.my_queue_callbacks = True
        self.my_last_error = ""
        self.my_recv_buffer = []
        self.my_msg_buffer = []


    def __eq__(self, value):
        """
            Description: Placeholder equality comparison (unimplemented).
            Inputs:
                value (Any): Other object for comparison.
            Outputs: None (currently no return behavior)
            Exceptions: None
        """
        pass

    def connect_socket(self, socket_address):
        """
            Description: Establish TCP connection to remote (host, port) tuple.
            Inputs:
                socket_address (tuple[str,int] | str): Target address accepted by socket.create_connection.
            Outputs: bool indicating if socket object is non-None after attempt.
            Exceptions: Propagates socket-related exceptions from create_connection.
        """
        self.my_socket = socket.create_connection(socket_address)
        return self.my_socket is not None

    def send_message(self, msg):
        """
            Description: Serialize and transmit a fedPro-style message object.
            Inputs:
                msg: Object providing to_bytes() -> bytes for network send.
            Outputs: True on success.
            Exceptions: On socket.error stores error text and re-raises.
        """
        try:
            self.my_socket.sendall(msg.to_bytes())
        except socket.error as e:
            self.my_last_error = str(e)
            log_error("Socket error while sending message: " + self.my_last_error)
            raise e
        return True

    def flush(self):
        """
            Description: Placeholder flush (no-op implementation).
            Inputs: None
            Outputs: int (always 0 currently)
            Exceptions: None
        """
        return 0

    def recv_message_with_src(self, buffptr, src):
        """
            Description: Placeholder to receive message and source metadata (not implemented).
            Inputs:
                buffptr: Buffer pointer / container (unused).
                src: Source address holder (unused).
            Outputs: None
            Exceptions: None
        """
        pass

    def close_socket(self):
        """
            Description: Close underlying socket if present.
            Inputs: None
            Outputs: None
            Exceptions: Propagates socket.close exceptions.
        """
        self.my_socket.close()

    def state(self):
        """
            Description: Placeholder for socket state retrieval.
            Inputs: None
            Outputs: None (unimplemented)
            Exceptions: None
        """
        pass

    def print_state(self, stream):
        """
            Description: Build human-readable state string (currently not written to stream).
            Inputs:
                stream: Intended output stream (unused).
            Outputs: None
            Exceptions: None
        """
        aState = "Socket State:\n"
        aState += "  State: {}\n".format(self.state())
        errCatch = self.last_error()
        if (errCatch is not ""):
            aState += "  Last Error: {}\n".format(errCatch)

    def last_error(self):
        """
            Description: Retrieve last stored error message.
            Inputs: None
            Outputs: str error description (may be empty).
            Exceptions: None
        """
        return self.my_last_error

    def enable_bundling(self, max_bundle_size):
        """
            Description: Stub for enabling message bundling (coalescing multiple messages).
            Inputs:
                max_bundle_size: Maximum bytes per bundle (unused).
            Outputs: None
            Exceptions: None
        """
        pass

    def disable_bundling(self):
        """
            Description: Stub for disabling message bundling.
            Inputs: None
            Outputs: None
            Exceptions: None
        """
        pass

    def enable_compression(self, compression_level):
        """
            Description: Stub for enabling compression.
            Inputs:
                compression_level: Desired compression level (unused).
            Outputs: None
            Exceptions: None
        """
        pass

    def inet_socket(self):
        """
            Description: Access the underlying raw socket object.
            Inputs: None
            Outputs: socket.socket or None
            Exceptions: None
        """
        return self.my_socket

    def fillBuffer(self, size=4):
        """
            Description: Receive up to 'size' bytes and append to internal receive buffer list.
            Inputs:
                size (int): Number of bytes to attempt to read (default 4).
            Outputs: bool True if bytes appended; False on socket timeout.
            Exceptions: Other socket errors propagate.
        """
        try:
            self.my_recv_buffer.append(self.my_socket.recv(size))
            return True
        except socket.timeout:
            return False

    def get_message(self, wait_interval: float = 3.0) -> fedProMessage.FedProMessage:
        """
            Description: Assemble and return the next complete FedProMessage from buffered socket segments.
            Inputs:
                wait_interval (float): Seconds to wait for initial length bytes before timing out.
            Outputs: FedProMessage instance (INVALID type if incomplete).
            Exceptions:
                Exception.FedProSocketError: If underlying socket missing.
                socket.timeout: If initial length/header not received in time.
                Exception.FedProMessageError: If received size mismatch indicates corruption.
                Other socket/OSError errors: Propagated after storing last error.
        """
        if self.my_socket is None:
            raise exception.FedProSocketError("Socket is None, cannot get message")
        try:
            # Grab size, poll until size requirement is met
            self.my_socket.settimeout(wait_interval)
            chomp = 4
            msg_length = 0
            rcv_msg = fedProMessage.FedProMessage((fedProMessage.MsgType.INVALID * -1), 0)
            if self.fillBuffer(chomp):
                # If we have less that 3 segments of reveived data in the buf, this is the first pass of the loop
                if len(self.my_recv_buffer) < 3:
                    msg_length : int = struct.unpack(">I", self.my_recv_buffer[0])[0]
                    #is checking for a minimum message length enough of a check?
                    if msg_length >= 24:
                        # try to grab the rest of the message
                        self.fillBuffer(msg_length - 4)
                        # going to need to return the message in nibbles
                        rcv_msg.from_bytes(self.my_recv_buffer)
                else:
                    rcv_msg.from_bytes(self.my_recv_buffer)

                # Handle msg size vs expected size
                if msg_length == sum(len(item) for item in self.my_recv_buffer):
                    self.my_recv_buffer.clear()
                    return rcv_msg
                elif msg_length < sum(len(item) for item in self.my_recv_buffer):
                    # This should never happen, but if it does, but just in case python socket breaks
                    print(f"Received message larger than expected: {msg_length} bytes, buffer has {sum(len(item) for item in self.my_recv_buffer)} bytes")
                    raise exception.FedProMessageError("Received message larger than expected")
                else:
                    print(f"Received message too short: {msg_length} bytes, expected {sum(len(item) for item in self.my_recv_buffer)} bytes")
                    chomp = msg_length - (sum(len(item) for item in self.my_recv_buffer))

        except error as e:
            self.my_last_error = str(e)
            print("Error while getting message: " + self.my_last_error)
            raise e
        
        return fedProMessage.FedProMessage(fedProMessage.MsgType.INVALID, 0)
