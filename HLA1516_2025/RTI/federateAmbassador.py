"""
    Python Federate Protocol © 2025 by MAK Technologies is licensed under CC BY-ND 4.0.
    To view a copy of this license, visit https://creativecommons.org/licenses/by-nd/4.0/
"""
from __future__ import annotations
from typing import Any
from HLA1516_2025.RTI.federateData import FederateData
from HLA1516_2025.RTI.typedefs import AttributeHandleValueMap, FederationExecutionInformationVector, ParameterHandleValueMap
from HLA1516_2025.RTI.handles import InteractionClassHandle, ObjectInstanceHandle, ObjectClassHandle, FederateHandle, TransportationTypeHandle, AttributeHandle, ParameterHandle

class FederateAmbassador:
    """
        Base class for user-defined FederateAmbassador implementations.
        All methods are no-ops by default; override as needed.
        
        Each callback method corresponds to a specific RTI service or event,
        allowing the federate to respond appropriately.
        
        Methods are named and numbered according to the HLA 1516-2010 standard sections.
    """

    def __init__(self, data : FederateData = FederateData()):
        self.my_data : FederateData = data

    def connectionLost(self, fault_description: str) -> None:
        """
            4.4
            Description:
                Notification that the connection to the RTI has been lost.
            Args:
                fault_description (str): Text describing the fault supplied by the RTI / transport.
            Returns:
                None
            Raises:
                FederateInternalError
        """

    def reportFederationExecutions(self, report: FederationExecutionInformationVector) -> None:
        """
            4.8
            Description:
                Provides a report of currently available federation executions.
            Args:
                report (FederationExecutionInformationVector): Collection of federation execution info structures.
            Returns:
                None
            Raises:
                FederateInternalError
        """

    def reportFederationExecutionMembers(self, federation_name: str, report: FederationExecutionInformationVector) -> None:
        """
            4.10
            Description:
                Provides membership details for a named federation execution.
            Args:
                federation_name (str): The name of the federation execution.
                report (FederationExecutionInformationVector): Vector containing member information.
            Returns:
                None
            Raises:
                FederateInternalError
        """

    def reportFederationExecutionDoesNotExist(self, federation_name: str) -> None:
        """
            4.11
            Description:
                Indicates a query referenced a federation execution name that does not exist.
            Args:
                federation_name (str): The queried federation execution name.
            Returns:
                None
            Raises:
                FederateInternalError
        """

    def federateResigned(self, reason: str) -> None:
        """
            4.13
            Description:
                Notification that this federate has been resigned (forced resignation or acknowledgment).
            Args:
                reason (str): Human-readable reason for the resignation.
            Returns:
                None
            Raises:
                FederateInternalError
        """

    def objectInstanceNameReservationSucceeded(self, the_object_name: str) -> None:
        """
            6.3
            Description:
                Callback indicating that a requested object instance name reservation succeeded.
            Args:
                the_object_name (str): The object instance name that was reserved.
            Returns:
                None
            Raises:
                FederateInternalError
        """

    def objectInstanceNameReservationFailed(self, the_object_name: str) -> None:
        """
            6.3
            Description:
                Callback indicating that a requested object instance name reservation failed.
            Args:
                the_object_name (str): The object instance name that failed to reserve.
            Returns:
                None
            Raises:
                FederateInternalError
        """

    def discoverObjectInstance(self, instance_handle: ObjectInstanceHandle, class_handle: ObjectClassHandle, object_name: str, producing_federate: FederateHandle) -> None:
        """
            6.9
            Description:
                Notifies discovery of a remote object instance.
            Args:
                instance_handle (ObjectInstanceHandle): Handle of the discovered instance.
                class_handle (ObjectClassHandle): Class handle of the object.
                object_name (str): Name of the discovered object instance.
                producing_federate (FederateHandle): Handle of the producing federate.
            Returns:
                None
            Raises:
                FederateInternalError
        """

    def removeObjectInstance(self, object_instance_handle: ObjectInstanceHandle, user_tag: bytes, producing_federate: FederateHandle) -> None:
        """
            6.17
            Description:
                Notifies removal (delete) of an object instance.
            Args:
                object_instance_handle (ObjectInstanceHandle): Handle of the removed object instance.
                user_tag (bytes): User-supplied tag data.
                producing_federate (FederateHandle): Handle of the producing federate.
            Returns:
                None
            Raises:
                FederateInternalError
        """

    def receiveInteraction(self, interaction_class_handle: InteractionClassHandle, parameters: ParameterHandleValueMap, user_tag: bytes, transport_type: TransportationTypeHandle, producing_federate: FederateHandle) -> None:
        """
            6.13
            Description:
                Delivers an interaction to the federate.
            Args:
                interaction_class_handle (InteractionClassHandle): Handle of the interaction class.
                user_tag (bytes): User tag associated with the send.
                transport_type (TransportationTypeHandle): Transport used.
                producing_federate (FederateHandle): Handle of the producing federate (if available).
                parameters (Any): Collection/map of interaction parameters.
            Returns:
                None
            Raises:
                FederateInternalError
        """

    def reflectAttributeValues(self, object_instance_handle: ObjectInstanceHandle, attributes: AttributeHandleValueMap, user_tag: bytes, transport_type: TransportationTypeHandle, producing_federate: FederateHandle) -> None:
        """
            6.11
            Description:
                Reflects updated attribute values for a known object instance.
            Args:
                object_instance_handle (ObjectInstanceHandle): Handle of the object instance.
                user_tag (bytes): User-supplied tag from the update.
                transport_type (TransportationTypeHandle): Transport used for delivery.
                producing_federate (FederateHandle): Handle of the producing federate.
                attributes (Any): Attribute handle-value pairs or structure.
            Returns:
                None
            Raises:
                FederateInternalError
        """
