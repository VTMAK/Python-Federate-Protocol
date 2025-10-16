"""
    Python Federate Protocol © 2025 by MAK Technologies is licensed under CC BY-ND 4.0.
    To view a copy of this license, visit https://creativecommons.org/licenses/by-nd/4.0/
"""
from typing import Any
from libsrc.rtiUtil.logger import *
from HLA1516_2025.RTI.federateAmbassador import FederateAmbassador
from HLA1516_2025.RTI.handles import AttributeHandle, ParameterHandle
from HLA1516_2025.RTI.typedefs import AttributeHandleValueMap, ParameterHandleValueMap
from HLA1516_2025.RTI.handles import FederateHandle, InteractionClassHandle, ObjectClassHandle, ObjectInstanceHandle, TransportationTypeHandle

import os
import sys
# Set the top directory to be two levels higher than the current directory
current_dir = os.path.dirname(os.path.abspath(__file__))
top_dir = os.path.dirname(current_dir)
sys.path.insert(0, top_dir)
from FedProProtobuf import FederateAmbassador_pb2

the_callback_request_ref = FederateAmbassador_pb2.CallbackRequest()

class FederateAmbassadorFedPro():
    """Federate Ambassador wrapper implementing callback dispatch and RTI interaction."""

    def __init__(self, FedPro_Message_Handler, Federate_Ambassador: FederateAmbassador, session_id: int):
        """
            Description:
                Initialize the Federate Ambassador FedPro wrapper, establishing callback mapping and session context.
            Args:
                FedPro_Message_Handler: FedPro message handler instance used for callback registration.
                Federate_Ambassador (FederateAmbassador): Underlying federate ambassador implementation.
                session_id (int): Active session identifier for correlation.
            Outputs:
                Populates internal state (session id, ambassador ref, callback dispatch table, log path).
            Exceptions:
                None (assumes provided rti_ambassador is valid and protobuf enum field numbers resolve).
        """
        self.my_Federate_Ambassador : FederateAmbassador = Federate_Ambassador
        self.my_FedPro_Message_Handler = FedPro_Message_Handler
        self.my_session_id = session_id
        self.my_callback_functions: dict[int, Any] = {}
        self.log_file_path = (
            "C:/Users/jregan/Dev/jregan-FedPro/testFederates/python/"
            "FederateProtocol/FederateProtocol_Python/simple_callback_log.txt"
        )

        cb = FederateAmbassador_pb2.CallbackRequest()
        self.my_FedPro_Message_Handler.add_callback_request_callback(cb.CONNECTIONLOST_FIELD_NUMBER, self.connection_lost)
        self.my_FedPro_Message_Handler.add_callback_request_callback(cb.REPORTFEDERATIONEXECUTIONS_FIELD_NUMBER, self.report_federation_executions)
        self.my_FedPro_Message_Handler.add_callback_request_callback(cb.REPORTFEDERATIONEXECUTIONMEMBERS_FIELD_NUMBER, self.report_federation_execution_members)
        self.my_FedPro_Message_Handler.add_callback_request_callback(cb.REPORTFEDERATIONEXECUTIONDOESNOTEXIST_FIELD_NUMBER, self.report_federation_execution_does_not_exist)
        self.my_FedPro_Message_Handler.add_callback_request_callback(cb.FEDERATERESIGNED_FIELD_NUMBER, self.federate_resigned)
        self.my_FedPro_Message_Handler.add_callback_request_callback(cb.OBJECTINSTANCENAMERESERVATIONFAILED_FIELD_NUMBER, self.object_name_reservation_failed)
        self.my_FedPro_Message_Handler.add_callback_request_callback(cb.OBJECTINSTANCENAMERESERVATIONSUCCEEDED_FIELD_NUMBER, self.object_instance_name_reservation_succeeded)
        self.my_FedPro_Message_Handler.add_callback_request_callback(cb.DISCOVEROBJECTINSTANCE_FIELD_NUMBER, self.discover_object_instance)
        self.my_FedPro_Message_Handler.add_callback_request_callback(cb.REMOVEOBJECTINSTANCE_FIELD_NUMBER, self.remove_object_instance)
        self.my_FedPro_Message_Handler.add_callback_request_callback(cb.REFLECTATTRIBUTEVALUES_FIELD_NUMBER, self.reflect_attribute_values)
        self.my_FedPro_Message_Handler.add_callback_request_callback(cb.RECEIVEINTERACTION_FIELD_NUMBER, self.receive_interaction)
        self.my_FedPro_Message_Handler.add_callback_request_callback(-99, self.unknown_callback)

    def connection_lost(self, message, sequence_number: int):
        """
            Description:
                Dispatch handler invoked when connectionLost callback arrives; extracts fault and delegates to base.
            Args:
                message (Any): Callback envelope containing connectionLost.faultDescription.
                sequence_number (int): Correlation id for response.
            Outputs:
                Calls base connectionLost processor and sends success response.
            Exceptions:
                None (any unexpected access triggers generic Exception caught by caller path if added similarly to others).
        """
        fault = message.connectionLost.faultDescription
        log_incoming("Connection Lost")
        self.my_Federate_Ambassador.connectionLost(fault)
        self.my_FedPro_Message_Handler.send_callback_response(sequence_number, True)

    def report_federation_executions(self, message, sequence_number: int):
        """
            Description:
                Parse federation execution info list and forward simplified report to base ambassador.
            Args:
                message (Any): Callback envelope with reportFederationExecutions sub-message.
                sequence_number (int): Callback correlation id.
            Outputs:
                Invokes self.reportFederationExecutions(list_of_entries) and sends success/failure response.
            Exceptions:
                Catches all Exceptions; logs and responds with failure.
        """
        try:
            federations = message.reportFederationExecutions
            log_incoming(f"DtFederateAmbassadorWrapper::reportFederationExecutions")
            info_set = federations.report
            size = len(info_set.federationExecutionInformation)
            
            report = []
            for i in range(size):
                info = info_set.federationExecutionInformation[i]
                federation_name = info.federationExecutionName
                logical_time_impl = info

                # Create federation execution information entry
                rti_entry = (federation_name, logical_time_impl)
                report.append(rti_entry)
            self.my_Federate_Ambassador.reportFederationExecutions(report)
            
            self.my_FedPro_Message_Handler.send_callback_response(sequence_number, True)
            
        except Exception as e:
            log_error(f"Error in report_federation_executions: {e}")
            self.my_FedPro_Message_Handler.send_callback_response(sequence_number, False)

    def report_federation_execution_members(self, message, sequence_number: int):
        """
            Description:
                Extract list of federation execution members and forward to base ambassador for logging/state.
            Args:
                message (Any): Callback envelope containing reportFederationExecutionMembers.
                sequence_number (int): Correlation id.
            Outputs:
                Calls self.reportFederationExecutionMembers(name, report_list) then responds.
            Exceptions:
                Broad exception catch logs error then sends failure response.
        """
        federation_members = message.reportFederationExecutionMembers
        
        try:
            log_incoming(f"DtFederateAmbassadorWrapper::reportFederationExecutions")
            report = []
            federation_name = federation_members.federationName
            info_set = federation_members.report
            size = len(info_set.federationExecutionMemberInformation)
            
            for i in range(size):
                info = info_set.federationExecutionMemberInformation[i]
                federate_name = info.federateName
                federate_type = info.federateType
                
                # Create federation execution member information entry
                rti_entry = (federate_name, federate_type)
                report.append(rti_entry)
            
            self.my_Federate_Ambassador.reportFederationExecutionMembers(federation_name, report)
            self.my_FedPro_Message_Handler.send_callback_response(sequence_number, True)
            
        except Exception as e:
            log_error(f"Error in report_federation_execution_members: {e}")
            self.my_FedPro_Message_Handler.send_callback_response(sequence_number, False)

    def report_federation_execution_does_not_exist(self, message, sequence_number: int):
        """
            Description:
                Notify base that a queried federation execution does not exist.
            Args:
                message (Any): Callback containing reportFederationExecutionDoesNotExist.federationName.
                sequence_number (int): Correlation id.
            Outputs:
                Invokes self.reportFederationExecutionDoesNotExist(name) and sends response.
            Exceptions:
                Catches all and logs failure.
        """
        try:
            federation_name = message.reportFederationExecutionDoesNotExist.federationName
            
            log_incoming(f"Federation does not exist: {federation_name}")
            
            self.my_Federate_Ambassador.reportFederationExecutionDoesNotExist(federation_name)            
            self.my_FedPro_Message_Handler.send_callback_response(sequence_number, True)
            
        except Exception as e:
            log_error(f"Error in report_federation_execution_does_not_exist: {e}")
            self.my_FedPro_Message_Handler.send_callback_response(sequence_number, False)

    def federate_resigned(self, message, sequence_number: int):
        """
            Description:
                Handle notification that federate resigned; forward reason to base ambassador.
            Args:
                message (Any): Callback with federateResigned.reasonForResignDescription.
                sequence_number (int): Correlation id.
            Outputs:
                Calls self.federateResigned(reason) and responds.
            Exceptions:
                Catches all exceptions; on failure logs and sends negative response.
        """
        try:
            reason = message.federateResigned.reasonForResignDescription
            
            self.my_Federate_Ambassador.federateResigned(reason)
            
            self.my_FedPro_Message_Handler.send_callback_response(sequence_number, True)
            
        except Exception as e:
            log_error(f"Error in federate_resigned: {e}")
            self.my_FedPro_Message_Handler.send_callback_response(sequence_number, False)
    
    def object_instance_name_reservation_succeeded(self, message, sequence_number: int):
        """
            Description:
                Process positive result of object instance name reservation.
            Args:
                message (Any): Callback with objectInstanceNameReservationSucceeded.objectInstanceName.
                sequence_number (int): Correlation id.
            Outputs:
                Delegates to self.objectInstanceNameReservationSucceeded(name); sends success/failure response.
            Exceptions:
                Broad catch-all logs and replies failure.
        """
        try:
            object_name = message.objectInstanceNameReservationSucceeded.objectInstanceName
            
            self.my_Federate_Ambassador.objectInstanceNameReservationSucceeded(object_name)
            
            self.my_FedPro_Message_Handler.send_callback_response(sequence_number, True)
            
        except Exception as e:
            log_error(f"Error in object_name_reservation_succeeded: {e}")
            self.my_FedPro_Message_Handler.send_callback_response(sequence_number, False)

    def object_name_reservation_failed(self, message, sequence_number: int):
        """
            Description:
                Process negative result of object instance name reservation attempt.
            Args:
                message (Any): Callback with objectInstanceNameReservationFailed.objectInstanceName.
                sequence_number (int): Correlation id.
            Outputs:
                Delegates to self.objectInstanceNameReservationFailed(name) and sends response.
            Exceptions:
                Broad catch; logs failure message.
        """
        try:
            object_name = message.objectInstanceNameReservationFailed.objectInstanceName

            self.my_Federate_Ambassador.objectInstanceNameReservationFailed(object_name)
            
            self.my_FedPro_Message_Handler.send_callback_response(sequence_number, True)
            
        except Exception as e:
            log_error(f"Error in object_name_reservation_failed: {e}")
            self.my_FedPro_Message_Handler.send_callback_response(sequence_number, False)

    def discover_object_instance(self, message, sequence_number: int):
        """
            Description:
                Decode discoverObjectInstance data and register the instance via base discovery handler.
            Args:
                message (Any): Callback containing discoverObjectInstance sub-message.
                sequence_number (int): Correlation id.
            Outputs:
                Calls self.discoverObjectInstance(handle, class_handle, name, producing_federate) then responds.
            Exceptions:
                Catches all; logs and sends failure response.
        """
        try:
            discover_object_instance = message.discoverObjectInstance
            discObjInst : ObjectInstanceHandle = ObjectInstanceHandle(discover_object_instance.objectInstance.data)
            discClassHandle : ObjectClassHandle = ObjectClassHandle(discover_object_instance.objectClass.data)
            discObjName : str = discover_object_instance.objectInstanceName
            rtiFedHandle : FederateHandle = FederateHandle(discover_object_instance.producingFederate.data)
            self.my_Federate_Ambassador.discoverObjectInstance(discObjInst, discClassHandle, discObjName, rtiFedHandle)
            self.my_FedPro_Message_Handler.send_callback_response(sequence_number, True)
        except Exception as e:

            log_error(f"Error in discover_object_instance: {e}")
            self.my_FedPro_Message_Handler.send_callback_response(sequence_number, False)


    def remove_object_instance(self, message, sequence_number: int):
        """
            Description:
                Handle removal notification for an object instance and delegate to base cleanup logic.
            Args:
                message (Any): Callback including removeObjectInstance sub-message.
                sequence_number (int): Correlation id.
            Outputs:
                Calls self.removeObjectInstance(handle, user_tag, producing_federate) and sends result.
            Exceptions:
                Broad exception handler logs errors and sends failure result.
        """
        try:
            remove_object = message.removeObjectInstance
            objInst : ObjectInstanceHandle = ObjectInstanceHandle(remove_object.objectInstance.data)
            fedHandle : FederateHandle = FederateHandle(remove_object.producingFederate.data)
            userTag : bytes = remove_object.userSuppliedTag

            self.my_Federate_Ambassador.removeObjectInstance(objInst, userTag, fedHandle)
            
            self.my_FedPro_Message_Handler.send_callback_response(sequence_number, True)
            
        except Exception as e:
            log_error(f"Error in remove_object_instance: {e}")
            self.my_FedPro_Message_Handler.send_callback_response(sequence_number, False)

    def receive_interaction(self, message, sequence_number: int):
        """
            Description:
                Process an interaction (parameter set) and delegate to base handler after preparing caches.
            Args:
                message (Any): Callback with receiveInteraction sub-message.
                sequence_number (int): Correlation id.
            Outputs:
                Populates nested parameter value cache structures then invokes self.receiveInteraction(...).
            Exceptions:
                Broad catch logs and replies failure.
        """
        try:
            reflect_parameter_values = message.receiveInteraction
            interaction_class_handle : InteractionClassHandle = reflect_parameter_values.interactionClass.data
            _user_tag = reflect_parameter_values.userSuppliedTag
            transport_type : TransportationTypeHandle = reflect_parameter_values.transportationType.data
            producing_federate : FederateHandle = FederateHandle(reflect_parameter_values.producingFederate.data)
            self.my_Federate_Ambassador.my_data.my_interaction_parameter_values[producing_federate] = {}
            self.my_Federate_Ambassador.my_data.my_interaction_parameter_values[producing_federate][interaction_class_handle] = {}
            parameter_values = reflect_parameter_values.parameterValues
            phvpm : ParameterHandleValueMap = {}
            for param in parameter_values.ListFields()[0][1]:
                phvpm[ParameterHandle(param.parameterHandle.data)] = param.value
            self.my_Federate_Ambassador.receiveInteraction(interaction_class_handle, phvpm, _user_tag, transport_type, producing_federate)

            self.my_FedPro_Message_Handler.send_callback_response(sequence_number, True)
        except Exception as e:
            log_error(f"Error in receive_interaction_values: {e}")
            self.my_FedPro_Message_Handler.send_callback_response(sequence_number, False)

    def reflect_attribute_values(self, message, sequence_number: int):
        """
            Description:
                Process attribute reflection update and delegate to base reflectAttributeValues handler.
            Args:
                message (Any): Callback with reflectAttributeValues sub-message.
                sequence_number (int): Correlation id.
            Outputs:
                Invokes self.reflectAttributeValues(object_handle, tag, transport_type, federate, attribute_values) then responds.
            Exceptions:
                Broad catch logs error and marks failure.
        """
        try:
            reflect_attribute_values = message.reflectAttributeValues
            object_instance_handle : ObjectInstanceHandle = reflect_attribute_values.objectInstance.data
            user_tag = reflect_attribute_values.userSuppliedTag
            transport_type : TransportationTypeHandle = reflect_attribute_values.transportationType.data
            producing_federate : FederateHandle = FederateHandle(reflect_attribute_values.producingFederate.data)
            attribute_values = reflect_attribute_values.attributeValues
            ahvpm : AttributeHandleValueMap = {}
            for attr in attribute_values.ListFields()[0][1]:
                ahvpm[AttributeHandle(attr.attributeHandle.data)] = attr.value
            self.my_Federate_Ambassador.reflectAttributeValues(object_instance_handle, ahvpm, user_tag, transport_type, producing_federate)

            self.my_FedPro_Message_Handler.send_callback_response(sequence_number, True)
        except Exception as e:
            log_error(f"Error in reflect_attribute_values: {e}")
            self.my_FedPro_Message_Handler.send_callback_response(sequence_number, False)

    def unknown_callback(self, message, sequence_number: int):
        """
            Description:
                Diagnostic handler for unrecognized callback types; logs detailed separators and warning.
            Args:
                message (Any): Original unhandled callback envelope.
            Outputs:
                Returns True to indicate handling (prevent further escalation).
            Exceptions:
                None.
        """
        log_incoming("===================================")
        log_incoming("===================================")
        log_incoming(message)
        log_incoming("===================================")
        log_incoming("===================================")
        log_warning(f"WARNING: Unknown callback type: {message.my_hla_msg_type}")
        self.my_FedPro_Message_Handler.send_callback_response(sequence_number, False)
        return True
