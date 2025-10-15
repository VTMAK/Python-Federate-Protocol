"""
    Python Federate Protocol © 2025 by MAK Technologies is licensed under CC BY-ND 4.0.
    To view a copy of this license, visit https://creativecommons.org/licenses/by-nd/4.0/
"""
import time
from HLA1516_2025.RTI import enums
from libsrc.rtiUtil.logger import *
from HLA1516_2025.RTI.handles import *
from libsrc.fedPro import fedProMessage
from libsrc.rtiUtil import exception, msgSocket
from HLA1516_2025.RTI.federateAmbassador import FederateAmbassador
from libsrc.fedProWrapper.federateAmbassadorFedPro import FederateAmbassadorFedPro
from libsrc.fedPro import callbackRequestMessage, callResponseMessage, heartBeatMessage,  newSessionMessage
from libsrc.fedPro import callbackResponseMessage, callRequestMessage, heartBeatResponseMessage,  newSessionStatusMessage
from FedProProtobuf.RTIambassador_pb2 import CallResponse
from FedProProtobuf.FederateAmbassador_pb2 import CallbackRequest



FEDPRO_VERSION = 1

the_call_response_ref = CallResponse()

class FedProMsgHandler:
    """
    Base class for RTI Ambassador implementations using FedPro protocol.
    Based on the C++ rtiAmbassadorFedProBase class.
    """
#=================================================Initialize=======================================================================================
    def __init__(self):
        """
            Description:
                Initialize core FedPro handler state, including socket, session tracking, message type dispatch tables, and heartbeat management fields.
            Inputs:
                self: FedProHandler instance being constructed.
            Outputs:
                Populates instance attributes (socket, sequence numbers, mappings, queues, heartbeat timers).
            Exceptions:
                None.
        """
        self.federate_ambassador_handler : FederateAmbassadorFedPro
        self.my_socket : msgSocket.MsgSocket = msgSocket.MsgSocket()
        self.my_session_id : int = 0
        self.my_sequence_num : int = 0
        self.my_session_status : newSessionStatusMessage.SessionStatus = newSessionStatusMessage.SessionStatus.UNSET
        self.my_last_received_message_number : int = 0
        self.my_callback_functions: dict[int, Any] = {}
        
        self.my_enable_callback_requests : bool = True
        self.my_is_connection_ok : bool = False
        
        self.handle_types = {
            'federate': FederateHandle,
            'object_class': ObjectClassHandle,
            'attribute': AttributeHandle,
            'interaction_class': InteractionClassHandle,
            'parameter': ParameterHandle,
            'object_instance': ObjectInstanceHandle,
            'message_retraction': MessageRetractionHandle,
            'transportation_type': TransportationTypeHandle,
            'dimension': DimensionHandle,
            'region': RegionHandle
        }

        self.msg_types = {
        fedProMessage.MsgType.CTRL_NEW_SESSION_STATUS: [newSessionStatusMessage.NewSessionStatusMessage, self.process_new_session_status],
        fedProMessage.MsgType.CTRL_HEARTBEAT_RESPONSE: [heartBeatResponseMessage.HeartbeatResponseMessage, self.process_heartbeat_response],
        fedProMessage.MsgType.CTRL_SESSION_TERMINATED: [fedProMessage.FedProMessage], # No specific class, use base\
        fedProMessage.MsgType.HLA_CALL_RESPONSE: [callResponseMessage.CallResponseMessage, self.process_call_response],
        fedProMessage.MsgType.HLA_CALLBACK_REQUEST: [callbackRequestMessage.CallbackRequestMessage, self.process_callback_request]
        }

        # Message processing attributes
        self.my_poll_result : int = -2
        self.my_heartbeat_timeout : float = 0.0
        self.my_heartbeat_interval : float = 60.0
        self.my_queue_callback_requests : bool = True
        self.my_last_received_message_number : int = 0
        self.my_heartbeat_timeout_period : float = 180.0
        self.my_expected_response_request_number : int = 0
        self.my_expected_response_type : int = fedProMessage.MsgType.UNKNOWN
        self.my_callback_request_queue : list[callbackRequestMessage.CallbackRequestMessage] = []
        self.my_heartbeat_message : heartBeatMessage.HeartbeatMessage = heartBeatMessage.HeartbeatMessage()
        self.my_fedPro_response : newSessionStatusMessage.NewSessionStatusMessage|heartBeatResponseMessage.HeartbeatResponseMessage|callResponseMessage.CallResponseMessage|callbackRequestMessage.CallbackRequestMessage = newSessionStatusMessage.NewSessionStatusMessage()
#================================================================================================================================================
#===========================================Socket Connection===================================================================================================
    def connect_socket(self, socket_address : tuple[str, int] = ("localhost", 15164)) -> bool:
        """
            Description:
                Establish a TCP connection to the RTI host and update internal connection status.
            Inputs:
                self: FedProHandler instance.
                socket_address (tuple[str,int]): Hostname/IP and port to connect to (default localhost:15164).
            Outputs:
                Returns True on successful connection; False otherwise. Updates internal connection status flag.
            Exceptions:
                OSError, ConnectionError are caught; function logs error and returns False.
        """
        try:
            success = self.my_socket.connect_socket(socket_address)
            self.set_connection_status(success)
            return success
        except (OSError, ConnectionError) as e:
            log_error(f"ERROR: Failed to connect to RTI: {e}")
            self.set_connection_status(False)
            return False
        
    def initializeSession(self, fedAmb: FederateAmbassador)-> bool:
        """
            Description:
                Initialize a new FedPro session by opening a socket (if not already), sending a NewSession request, and constructing a federate ambassador for callbacks upon success.
            Inputs:
                self: FedProHandler instance.
                fedAmb (FederateAmbassadorFedPro): Federate ambassador instance supplying address/port configuration.
            Outputs:
                Returns True if a status response is received (even if error flagged later), False if connection attempt fails.
            Exceptions:
                None explicitly raised; errors logged. Returns False on socket failure.
        """
        if self.my_socket.inet_socket():
            log_outgoing("Socket Connection Already Made")
            return False
        server_address = (fedAmb.my_data.my_fed_pro_addr, fedAmb.my_data.my_fed_pro_port)
        check_socket = self.connect_socket(server_address)
        if check_socket:
            a_new_session_message = newSessionMessage.NewSessionMessage()
            a_new_session_message.my_protocol_version = FEDPRO_VERSION
            received_status_msg = self.send_and_wait(a_new_session_message, fedProMessage.MsgType.CTRL_NEW_SESSION_STATUS)
            if received_status_msg:
                log_incoming("Connection Status Response Received")
                self.my_session_id = self.my_fedPro_response.my_session_id
                self.federate_ambassador_handler = FederateAmbassadorFedPro(self, fedAmb, self.my_session_id)
                return True
            log_error("Failed to receive connection status response")
            return True
        return False

#==========================================================================================================================================================================
#===========================================Message and Request Handling===================================================================================================
    def send_and_wait(self, request:fedProMessage.FedProMessage, expected_response_type:int, timeout: float=10)->bool:
        """
            Description:
                Send a FedPro request message and block (polling) until matching response type or timeout.
            Inputs:
                self: fedProHandler instance.
                request (FedProMessage): Outgoing message with header fields to be completed.
                expected_response_type (int): MsgType enum value expected in response.
                timeout (float, default 10): Maximum time in seconds to wait.
            Outputs:
                True if response received (poll result > 0); False if send fails or no response within timeout.
            Exceptions:
                Raises OSError/ConnectionError upstream after logging; may raise FedProMessageError if send fails.
        """
        try:
            # Send request
            if self.send_message(request) == -1:
                raise exception.FedProMessageError("Socket failed to send message")
            # Wait for response
            if request.my_msg_type is fedProMessage.MsgType.CTRL_HEARTBEAT:
                return self.poll_for_call_response(timeout, expected_response_type, True) > 0
            else:
                return self.poll_for_call_response(timeout, expected_response_type) > 0
        except (OSError, ConnectionError) as e:
            log_error(f"ERROR: Failed in send_and_wait: {e}")
            raise e
        
    
    def poll_for_call_response(self, max_wait: float, response: int, heartbeat: bool = False) -> int:
        """
            Description:
                Poll the socket for an expected response message, updating internal tracking and interpreting results.
            Inputs:
                self: fedProHandler instance.
                max_wait (float): Maximum seconds to poll.
                response (int): Expected MsgType or special EXCEPTIONDATA field number.
                heartbeat (bool, default False): Indicator for heartbeat-specific semantics (currently unused directly).
            Outputs:
                Returns poll result: 1 success, 0 timeout or mismatch, -1 error. Updates my_poll_result.
            Exceptions:
                None thrown; errors logged and reflected via return value.
        """
        self.my_expected_response_request_number = self.my_last_received_message_number + 1
        self.my_expected_response_type = response

        read_ok = self.read_and_process(0.0, max_wait) >= 0
        got_response = (self.my_expected_response_type is fedProMessage.MsgType.UNKNOWN or self.my_expected_response_type is the_call_response_ref.EXCEPTIONDATA_FIELD_NUMBER)
        while read_ok and not got_response: #read_and_process returns a message and we either get the message we're looking for or we aren't timed out (add timeout stuff)
            read_ok = self.read_and_process(0.0, max_wait) >= 0
            got_response =  (self.my_expected_response_type is fedProMessage.MsgType.UNKNOWN or self.my_expected_response_type is the_call_response_ref.EXCEPTIONDATA_FIELD_NUMBER)

        if self.my_expected_response_type is the_call_response_ref.EXCEPTIONDATA_FIELD_NUMBER:
            log_warning("Error Received from RTI")
            self.my_poll_result = -1
        elif got_response:
            self.my_poll_result = 1
        else:
            if read_ok:
                log_error("Read Error when waiting for message")
            else:
                log_error("Timeout waiting for message")
            self.my_poll_result = 0
        
        self.my_expected_response_request_number = 0
        self.my_expected_response_type = fedProMessage.MsgType.UNKNOWN
        return self.my_poll_result

    def process_heartbeat_response(self, heartbeat: heartBeatResponseMessage.HeartbeatResponseMessage):
        """
            Description:
                Handle an incoming heartbeat response, updating timeout and clearing expected response tracking if matched.
            Inputs:
                self: fedProHandler instance.
                heartbeat (HeartbeatResponseMessage): Parsed heartbeat response message.
            Outputs:
                Updates heartbeat timeout, my_fedPro_response, and possibly expected response tracking fields.
            Exceptions:
                Raises AttributeError/TypeError upstream after logging if message malformed.
        """
        try:
            if hasattr(heartbeat, 'my_msg_type') and heartbeat.my_msg_type != fedProMessage.MsgType.CTRL_HEARTBEAT_RESPONSE:
                log_warning(f"WARNING: Expected heartbeat response, got {heartbeat.my_msg_type}")
            
            self.my_heartbeat_timeout = time.time() + self.my_heartbeat_timeout_period
            self.my_fedPro_response = heartbeat

            # Check if this is the response we are looking for, change flags if true
            if self.my_expected_response_type == heartbeat.my_msg_type and self.my_expected_response_request_number == heartbeat.my_sequence_num:
                self.my_expected_response_request_number = 0
                self.my_expected_response_type = fedProMessage.MsgType.UNKNOWN
            elif self.my_expected_response_type is fedProMessage.MsgType.UNKNOWN:
                log_warning(f"Received Unexpected Heartbeat: Response Number {heartbeat.my_sequence_num} Request Number { heartbeat.my_msg_type}")
            else:
                log_warning(f"Waiting for response {self.my_expected_response_type} for request #{self.my_expected_response_request_number}\n\
                    but received #{heartbeat.my_sequence_num} of type {heartbeat.my_msg_type}")
                
        except (AttributeError, TypeError) as e:
            log_error(f"ERROR: Failed to process heartbeat response: {e}")
            raise e

    def process_new_session_status(self, newsession: newSessionStatusMessage.NewSessionStatusMessage):
        """
            Description:
                Process New Session Status response; update session id/status and clear expected response tracking if matched.
            Inputs:
                self: fedProHandler instance.
                newsession (NewSessionStatusMessage): Parsed session status response.
            Outputs:
                Updates my_fedPro_response, my_session_id, my_session_status; returns True if matched expected response else False.
            Exceptions:
                Raises AttributeError/TypeError or FedProMessageError on unexpected message conditions.
        """
        try:
            if hasattr(newsession, 'my_msg_type') and newsession.my_msg_type != fedProMessage.MsgType.CTRL_NEW_SESSION_STATUS:
                log_warning(f"WARNING: Expected New Session Status, got {newsession.my_msg_type}")
            self.my_fedPro_response = newsession
            self.my_session_id = newsession.my_session_id
            self.my_session_status = newsession.my_status

            # Check if this is the response we are looking for, change flags if true
            if self.my_expected_response_type == newsession.my_msg_type and self.my_expected_response_request_number == newsession.my_sequence_num:
                self.my_expected_response_request_number = 0
                self.my_expected_response_type = fedProMessage.MsgType.UNKNOWN
                return True
            elif self.my_expected_response_type is fedProMessage.MsgType.UNKNOWN:
                log_warning(f"Received Unexpected Call Response: Response Number {newsession.my_sequence_num} Request Type { newsession.my_msg_type}")
                raise exception.FedProMessageError(f"Unexpected Call Response: Response Number {newsession.my_sequence_num} Request Type { newsession.my_msg_type}")
            else:
                log_warning(f"Waiting for response {self.my_expected_response_type} for request #{self.my_expected_response_request_number}\n\
                    but received #{newsession.my_sequence_num} of type {newsession.my_msg_type}")
                return False
        except (AttributeError, TypeError) as e:
            log_error(f"ERROR: Failed to process new session status: {e}")
            raise e
    
    def process_call_response(self, callresponse: callResponseMessage.CallResponseMessage):
        """
            Description:
                Process a call response message, validating expected type/sequence and handling exception data signaling.
            Inputs:
                self: fedProHandler instance.
                callresponse (CallResponseMessage): Parsed call response.
            Outputs:
                Returns True if matches expected response; False on mismatch; updates tracking fields accordingly.
            Exceptions:
                Raises AttributeError/TypeError or FedProMessageError when invalid; logs errors before raising.
        """
        try:
            if hasattr(callresponse, 'my_msg_type') and callresponse.my_msg_type != fedProMessage.MsgType.HLA_CALL_RESPONSE:
                log_warning(f"WARNING: Expected Call response, got {callresponse.my_msg_type}")
                raise exception.FedProMessageError(f"Unexpected message type: {callresponse.my_msg_type}")
            
            self.my_fedPro_response = callresponse

            if callresponse.my_hla_msg_type > 1 and self.my_expected_response_type == callresponse.my_hla_msg_type \
                and self.my_expected_response_request_number == callresponse.my_sequence_num:
                self.my_expected_response_request_number = 0
                self.my_expected_response_type = fedProMessage.MsgType.UNKNOWN
                return True
            elif self.my_expected_response_type is fedProMessage.MsgType.UNKNOWN:
                log_warning(f"Received Unexpected Call Response: Response Number {callresponse.my_sequence_num} Request Number { callresponse.my_hla_msg_type}")
                raise exception.FedProMessageError(f"Unexpected Call Response: Response Number {callresponse.my_sequence_num} Request Number { callresponse.my_hla_msg_type}")
            elif callresponse.my_hla_msg_type is the_call_response_ref.EXCEPTIONDATA_FIELD_NUMBER:
                if callresponse.my_sequence_num is self.my_expected_response_request_number:
                    log_warning("Received Exception Data")
                    self.my_expected_response_type = the_call_response_ref.EXCEPTIONDATA_FIELD_NUMBER
                else:
                    log_warning(f"Expected Request type: \n {self.my_expected_response_type}")
                    return False
            else:
                log_error(f"Waiting for response {self.my_expected_response_type} for request #{self.my_expected_response_request_number} but received #{callresponse.my_sequence_num} of type {callresponse.my_hla_msg_type}")
                return False
        except (AttributeError, TypeError) as e:
            log_error(f"ERROR: Failed to process call response: {e}")
            raise e

    def process_callback_request(self, callbackrequest: callbackRequestMessage.CallbackRequestMessage):
        """
            Description:
                Handle an incoming callback request: queue or dispatch immediately based on configuration.
            Inputs:
                self: fedProHandler instance.
                callbackrequest (CallbackRequestMessage): Parsed callback request message.
            Outputs:
                Returns True if processed immediately; False if queued.
            Exceptions:
                Raises AttributeError/TypeError or RTIinternalError on malformed message or missing ambassador.
        """
        try:
            if hasattr(callbackrequest, 'my_msg_type') and callbackrequest.my_msg_type != fedProMessage.MsgType.HLA_CALLBACK_REQUEST:
                log_warning(f"WARNING: Expected callback request, got {callbackrequest.my_msg_type}")
            
            self.my_fedPro_response = callbackrequest
            result_pass : bool = False
            if self.my_queue_callback_requests:
                # Add to callback queue
                if callbackrequest.my_hla_msg_type is CallbackRequest.FEDERATERESIGNED_FIELD_NUMBER or \
                callbackrequest.my_hla_msg_type is CallbackRequest.CONNECTIONLOST_FIELD_NUMBER:
                    if self.my_expected_response_type is fedProMessage.MsgType.UNKNOWN:
                        log_error("Received Callback Request for Federate Resigned or Connection Lost")
                self.my_callback_request_queue.append(callbackrequest)
                self.my_expected_response_request_number = callbackrequest.my_sequence_num + 1
                result_pass =  False
            else:
                if self.federate_ambassador_handler:
                    self.my_sequence_num = callbackrequest.my_sequence_num
                    self.handle_callback_request(callbackrequest)
                    result_pass = True
                else:
                    log_error(f"Received callback request but don't have a federate ambassador:\n{callbackrequest}")
                    raise exception.RTIinternalError("No federate ambassador to process callback request")
            return result_pass
        except (AttributeError, TypeError) as e:
            log_error(f"ERROR: Failed to process callback request: {e}")
            raise e

    def read_and_process(self, min_time: float = 0.0, max_time: float = 15.0) -> int:
        """
            Description:
                Poll the underlying socket for incoming messages within bounded time; dispatch recognized FedPro messages.
            Inputs:
                self: fedProHandler instance.
                min_time (float, default 0.0): Minimum number of seconds to wait.
                max_time (float, default 15.0): Maximum number of seconds before returning.
            Outputs:
                Returns number of processed messages; -1 on error or disconnected state.
            Exceptions:
                Catches OSError, ConnectionError, AttributeError; logs and returns -1 instead of raising.
        """
        try:
            if not self.is_connected():
                log_error("ERROR: Not connected to RTI")
                return -1
            
            current_time = time.time()
            min_time_to_use = max(min_time, 0.0)
            max_stop_time = current_time + (max_time if max_time > min_time_to_use else min_time_to_use)
            min_stop_time = current_time + min_time_to_use
            got_message = False
            message_count = 0

            # Process messages within time constraints
            while self.is_connected() and not got_message:
                current_time = time.time()
                if current_time >= min_stop_time and (got_message or current_time >= max_stop_time):
                    log_info("Processing wait completed")
                    break
                if len(self.my_socket.my_msg_buffer) > 0:
                    log_info("Message buffer has data, processing immediately")
                    message = self.my_socket.my_msg_buffer.pop(0)
                else:
                    message = self.my_socket.get_message(max_time / 3) # 100ms timeoutself.my_socket.get_message(timeout)

                if message.my_msg_type is not fedProMessage.MsgType.INVALID and message.my_msg_size >= 0:
                    if (self.msg_types.get(message.my_msg_type) is None):
                        raise exception.FedProMessageError(f"Unexpected message type: {message.my_msg_type}")

                    # Cast the message to be the correct type
                    message = self.msg_types[message.my_msg_type][0](message)
                    # Call the appropriate handler
                    self.my_last_received_message_number = message.my_sequence_num
                    if (len(self.msg_types[message.my_msg_type]) > 1):
                        got_message = self.msg_types[message.my_msg_type][1](message)
                    self.my_sequence_num += 1
                    message_count += 1

            return message_count
        except (OSError, ConnectionError, AttributeError) as e:
            log_error(f"ERROR: Failed in read_and_process: {e}")
            return -1
    
    def send_message(self, request : fedProMessage.FedProMessage, sending_callback_response : bool = False) -> int:
        """
            Description:
                Populate common header fields on an outbound message and transmit via socket if connected.
            Inputs:
                self: fedProHandler instance.
                request (FedProMessage): Message to send (session, sequence, last-received fields will be set/updated).
                sending_callback_response (bool, default False): If True, preserves original sequence number.
            Outputs:
                Returns bytes sent (>=0) or -1 on failure / not connected.
            Exceptions:
                None raised; logs on error and returns -1.
        """
        request.my_session_id = self.my_session_id
        if not sending_callback_response:
            request.my_sequence_num = self.my_sequence_num

        request.my_last_received_msg = self.my_last_received_message_number
        if self.is_connected():

            return self.my_socket.send_message(request)
        else:
            log_error("ERROR: Not connected to RTI, cannot send message")
            return -1
        
#====================================================================================================================
#=========================================RTI State Management=======================================================
        
    def get_connection_status(self) -> bool:
        """
            Description:
                Retrieve current connection status flag.
            Inputs:
                self: fedProHandler instance.
            Outputs:
                Boolean indicating if handler considers socket connected.
            Exceptions:
                None.
        """
        return self.my_is_connection_ok
    
    def set_connection_status(self, status: bool):
        """
            Description:
                Update internal connection status flag.
            Inputs:
                self: fedProHandler instance.
                status (bool): New connection state.
            Outputs:
                Assigns my_is_connection_ok.
            Exceptions:
                None.
        """
        self.my_is_connection_ok = status
    
    def is_connected(self) -> bool:
        """
            Description:
                Determine if logical connection is active and underlying socket object exists.
            Inputs:
                self: fedProHandler instance.
            Outputs:
                True if connection status flag set and socket + internal socket attribute not None.
            Exceptions:
                None.
        """
        return self.get_connection_status() and self.my_socket and self.my_socket.my_socket is not None
    
#=====================================================================================================================

    def add_callback_request_callback(self, request_field_number : int, callback_request_method: Any):
        """
            Description:
                Register a callback function for a specific callback request type.
            Inputs:
                self: Ambassador wrapper instance.
                request_field_number (int): CallbackRequest field number to associate.
                callback_request_method (Any): Function to invoke for this callback type.
            Outputs:
                Updates my_callback_functions mapping.
            Exceptions:
                None.
        """
        if request_field_number in self.my_callback_functions:
            log_warning(f"Overwriting existing callback for field number {request_field_number}")
        self.my_callback_functions[request_field_number] = callback_request_method

    def remove_callback_request_callback(self, request_field_number : int):
        """
            Description:
                Unregister a previously set callback function for a specific callback request type.
            Inputs:
                self: Ambassador wrapper instance.
                request_field_number (int): CallbackRequest field number to disassociate.
            Outputs:
                Removes entry from my_callback_functions mapping if exists.
            Exceptions:
                None.
        """
        if request_field_number in self.my_callback_functions:
            del self.my_callback_functions[request_field_number]
        else:
            log_warning(f"No existing callback for field number {request_field_number} to remove")

    def handle_callback_request(self, message: Any):
        """
            Description:
                Entry point for generic callback messages arriving from transport; dispatch based on type.
            Inputs:
                self: Ambassador wrapper instance.
                message (Any): Envelope expected to possess my_hla_msg_type, my_request_buf, my_sequence_num.
            Outputs:
                Invokes matched handler if recognized; otherwise does nothing.
            Exceptions:
                None (missing attributes simply short-circuit). Handler exceptions propagate unless internally caught.
        """
        log_incoming("Got callback message: ")
        if hasattr(message, 'my_hla_msg_type'):
            callback_case = self.my_callback_functions.get(message.my_hla_msg_type)
            if callback_case is None:
                callback_case = self.my_callback_functions.get(-99) # Unknown callback handler
            callback_case(message.my_request_buf, message.my_sequence_num)
            return
            

    def send_callback_response(self, sequence_number : int = -1, succeded=True):
        """
            Description:
                Send an acknowledgement / result for a processed callback to the RTI ambassador.
            Inputs:
                self: Ambassador wrapper instance.
                sequence_number (int, default -1): Correlation identifier from inbound callback.
                succeded (bool, default True): Indicates success or failure of handling.
            Outputs:
                Emits a callbackResponseMessage over my_rti_ambassador.
            Exceptions:
                None (any send errors are assumed to be handled upstream or logged by ambassador).
        """
        response_message = callbackResponseMessage.CallbackResponseMessage(sequence_number, succeded)
        if succeded:
            log_outgoing(f"Sent callback succeeded response for sequence {sequence_number} with success")
        else:
            log_error(f"Sent callback failure response for sequence {sequence_number} with failure")
        self.send_message(response_message, True)

    def __del__(self):
        """
            Description:
                Destructor hook attempting clean disconnect from RTI on object deletion.
            Inputs:
                self: fedProHandler instance.
            Outputs:
                Invokes disconnect() best-effort; ignores common cleanup errors.
            Exceptions:
                Suppresses OSError, ConnectionError, AttributeError during teardown.
        """
        try:
            self.disconnect()
        except (OSError, ConnectionError, AttributeError):
            pass
