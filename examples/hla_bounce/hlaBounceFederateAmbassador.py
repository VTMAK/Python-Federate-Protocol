"""
    Python Federate Protocol © 2025 by MAK Technologies is licensed under CC BY-ND 4.0.
    To view a copy of this license, visit https://creativecommons.org/licenses/by-nd/4.0/
"""
import math
import struct
from HLA1516_2025.RTI.typedefs import AttributeHandleValueMap, FederationExecutionInformationVector, ParameterHandleValueMap
from libsrc.rtiUtil.logger import *
from examples.hla_bounce.ballData import Ball
from HLA1516_2025.RTI.federateData import FederateData
from HLA1516_2025.RTI.federateAmbassador import FederateAmbassador
from HLA1516_2025.RTI.handles import AttributeHandle, InteractionClassHandle, ObjectInstanceHandle, ObjectClassHandle, FederateHandle, ParameterHandle, TransportationTypeHandle

class HlaBounceFederateAmbassador(FederateAmbassador):
    """
        Federate Ambassador wrapper for Federate Protocol operation.
    """
    def __init__(self, ball_controller, data : FederateData = FederateData()):
        """
            Construct a federate ambassador wrapper around shared federate state.

            Args:
                ball_controller: Controller providing ball management interface.
                data (FederateData): Optional pre-existing federate data container.
            Side Effects:
                Associates provided (or default) data with ambassador via self.my_data.
        """
        super().__init__(data)
        self.my_ball_controller = ball_controller

    def connectionLost(self, fault_description: str) -> None:
        """
            Handle loss of underlying communication channel; flag state and log cause.

            Args:
                fault_description (str): Human-readable reason for connection failure.
            Side Effects:
                Sets connection lost indicator.
        """
        log_incoming(f"Cause of connection loss: {fault_description}")
        self.my_connection_lost = True

    def reportFederationExecutions(self, report: FederationExecutionInformationVector) -> None:
        """
            Process and log a report listing active federation executions.

            Args:
                report (list): Iterable of entries (federation_name, time_implementation).
            Side Effects:
                Sets my_report_federation_executions_received True.
        """
        self.my_data.my_report_federation_executions_received = True
        for entry in report:
            log_incoming(f"Federation: {entry[0]}, Time Implementation: {entry[1]}")

    def reportFederationExecutionMembers(self, federation_name: str, report: FederationExecutionInformationVector) -> None:
        """
            Handle report of members (federates) participating in a named federation execution.

            Args:
                federation_name (str): Name of the federation execution.
                report (list): Iterable of (federate_name, federate_handle) pairs.
            Side Effects:
                Sets my_report_federation_execution_members_received True.
        """
        self.my_data.my_report_federation_execution_members_received = True
        log_incoming(f"Members of Federation Execution: {federation_name}")
        for entry in report:
            log_incoming(f"   Federate: {entry[0]}, Handle: {entry[1]}")

    def reportFederationExecutionDoesNotExist(self, federation_name: str) -> None:
        """
            Indicate attempted query on a non-existent federation execution.

            Args:
                federation_name (str): Name that failed lookup.
            Side Effects:
                Sets my_report_federation_execution_not_exist True.
        """
        self.my_data.my_report_federation_execution_not_exist = True
        log_incoming(f"Federation Execution Does Not Exist: {federation_name}")

    def federateResigned(self, reason: str) -> None:
        """
            Record that the federate has resigned and log the provided reason.

            Args:
                reason (str): Explanation for resignation.
            Side Effects:
                Sets my_federate_resigned True in shared data.
        """
        self.my_data.my_federate_resigned = True
        log_incoming(f"Federate resigned with reason: {reason}")

    def objectInstanceNameReservationSucceeded(self, the_object_name: str) -> None:
        """
            Callback invoked when object instance name reservation succeeds.

            Args:
                the_object_name (str): Reserved object instance name.
            Side Effects:
                Sets flags name_reservation_returned and my_name_reservation_succeeded True.
        """
        self.my_data.name_reservation_returned = True
        self.my_data.my_name_reservation_succeeded = True
        log_incoming(f"Object name reservation succeeded: {the_object_name}")

    def objectInstanceNameReservationFailed(self, the_object_name: str) -> None:
        """
            Callback invoked when object instance name reservation fails.

            Args:
                the_object_name (str): Attempted object instance name.
            Side Effects:
                Sets name_reservation_returned True and my_name_reservation_succeeded False.
        """
        self.my_data.name_reservation_returned = True
        self.my_data.my_name_reservation_succeeded = False
        log_incoming(f"Object name reservation failed: {the_object_name}")

    def discoverObjectInstance(self, instance_handle : ObjectInstanceHandle,  class_handle : ObjectClassHandle, object_name : str, producing_federate : FederateHandle) -> None:
        """
            Handle discovery of a remote object instance; update name <-> handle maps and class cache.

            Args:
                instance_handle (ObjectInstanceHandle): Unique object instance identifier.
                class_handle (ObjectClassHandle): Handle of the object's class.
                object_name (str): Name associated with the instance.
                producing_federate (FederateHandle): Originating federate handle.
            Side Effects:
                Updates shared data maps for name/handle/class lookups.
        """
        self.my_data.my_object_instance_name_handles.setdefault(producing_federate, {})
        self.my_data.my_object_instance_name_handles[producing_federate][object_name] = (instance_handle, class_handle)

        self.my_data.my_object_instance_handle_names.setdefault(producing_federate, {})
        self.my_data.my_object_instance_handle_names[producing_federate].setdefault(instance_handle, object_name)
        # Direct lookup to enable quick reflection mapping
        self.my_data.my_object_instance_classes[instance_handle] = class_handle
        self.my_data.my_object_instance_attrs[instance_handle] = {}
        log_incoming(f"Discovered Object Instance: {instance_handle}, Class: {class_handle}, Name: {object_name}, Producing Federate: {producing_federate}")

    def removeObjectInstance(self, object_instance_handle: ObjectInstanceHandle, _user_tag: bytes, producing_federate: FederateHandle) -> None:
        """
            Handle notification that an object instance has been removed; purge related cached state.

            Args:
                object_instance_handle (ObjectInstanceHandle): Handle of the removed instance.
                _user_tag (bytes): Optional user tag (unused).
                producing_federate (FederateHandle): Federate that owned/produced the instance.
            Side Effects:
                Updates removal tracking set and cleans associated name/class mappings.
        """
        removed = getattr(self.my_data, 'my_removed_instances', None)
        if removed is None:
            removed = set()
            setattr(self.my_data, 'my_removed_instances', removed)
        removed.add(object_instance_handle)
        # Cleanup name maps if present
        handle_to_name = self.my_data.my_object_instance_handle_names.get(producing_federate)
        if handle_to_name and object_instance_handle in handle_to_name:
            name = handle_to_name.pop(object_instance_handle)
            name_to_handles = self.my_data.my_object_instance_name_handles.get(producing_federate)
            #remove from handle names
            if name_to_handles:
                name_to_handles.pop(name, None)
        # Clean direct class map
        if object_instance_handle in self.my_data.my_object_instance_classes:
            self.my_data.my_object_instance_classes.pop(object_instance_handle, None)

        log_incoming(f"Removed Object Instance: {object_instance_handle}, Producing Federate: {producing_federate}")

    def receiveInteraction(self, interaction_class_handle : InteractionClassHandle, parameters: ParameterHandleValueMap, user_tag: bytes, transport_type : TransportationTypeHandle, producing_federate : FederateHandle) -> None:
        """
            Process an incoming interaction: log meta-data and cache parameter values by federate and interaction class.

            Args:
                interaction_class_handle (InteractionClassHandle): Interaction class identifier.
                user_tag (bytes): Optional user-supplied tag.
                transport_type (TransportationTypeHandle): Transport indicator.
                producing_federate (FederateHandle): Origin federate.
                parameters (dict | protobuf wrapper): Provides ListFields() of parameter entries.
            Side Effects:
                Populates nested my_interaction_parameter_values map with raw parameter bytes.
        """
        log_incoming(f"receiveInteraction - interaction class handle: {interaction_class_handle}, user_tag: {user_tag}, transport_type: {transport_type}, producing_federate: {producing_federate}")
        log_incoming("Parameters:")
        # Grabbing the first descriptor/field-descriptor pairs for ParameterHandleValueMap (We only expect one)
        handle_values = parameters.items()
        for handle, value in handle_values:
            # Process each attribute value 
            log_incoming(f"   handle: {handle}, value: {value}")
            self.my_data.my_interaction_parameter_values[producing_federate][interaction_class_handle][handle] = value

    def reflectAttributeValues(self, object_instance_handle: ObjectInstanceHandle, attributes: AttributeHandleValueMap, user_tag: bytes, transport_type: TransportationTypeHandle, producing_federate: FederateHandle) -> None:
        """
            Reflect updated attribute values for a discovered object instance.

            Args:
                object_instance_handle (ObjectInstanceHandle): Target object instance.
                user_tag (bytes): Optional tag.
                transport_type (TransportationTypeHandle): Transport indicator.
                producing_federate (FederateHandle): Source federate.
                attributes (dict | protobuf wrapper): Provides ListFields() with attribute/value entries.
            Side Effects:
                Updates my_object_instance_attrs with attribute handle -> raw value mapping.
        """
        log_incoming(f"reflectAttributeValues - object instance handle: {object_instance_handle}, user_tag: {user_tag}, transport_type: {transport_type}, producing_federate: {producing_federate}")
        # Process each attribute value
        log_incoming("Attributes:")
        if len(self.my_data.my_object_instance_attrs) is 0:
            self.my_data.my_object_instance_attrs[object_instance_handle] = {}
        temp_ball : Ball = Ball("")
        direction_first : tuple[bool, float] = (False, -1.0)
        speed_first : tuple[bool, float] = (False, -1.0)
        for handle, value in attributes.items():
            print("!!!!")
            self.my_data.my_object_instance_attrs[object_instance_handle][handle] = value
            print("!!!!")
            attr_name = self.my_data.my_attr_handle_names[self.my_data.my_object_instance_classes[object_instance_handle]][handle]
            match attr_name:
                case "Direction":
                    output = struct.unpack(">d", value)[0]
                    if speed_first[0]:
                        temp_ball.dx = speed_first[1] * math.cos(output)
                        temp_ball.dy = speed_first[1] * math.sin(output)
                        print(f"Received direction: {output}, resulting in dx: {temp_ball.dx}, dy: {temp_ball.dy}")
                    else:
                        direction_first = (True, output)
                        print(f"Received direction: {output}, waiting for speed")
                case "Speed":
                    output = float(struct.unpack(">h", value)[0])
                    if direction_first[0]:
                        temp_ball.dx = output * math.cos(direction_first[1])
                        temp_ball.dy = output * math.sin(direction_first[1])
                        print(f"Received speed: {output}, resulting in dx: {temp_ball.dx}, dy: {temp_ball.dy}")
                    else:
                        speed_first = (True, output)
                        print(f"Received speed: {output}, waiting for direction")
                case "XLocation":
                    temp_ball.x = (struct.unpack(">h", value)[0]) + 250
                    print(f"Received x location: {temp_ball.x}")
                case "YLocation":
                    temp_ball.y = (struct.unpack(">h", value)[0]) + 250
                    print(f"Received y location: {temp_ball.y}")
                case "Color":
                    temp_ball.color = struct.unpack(">B", value)[0]
                    print(f"Received color: {temp_ball.color}")
                case "Size":
                    temp_ball.scale = struct.unpack(">h", value)[0]
                    print(f"Received size: {temp_ball.scale}")
                case _:
                    pass
            print("!!!!")
        temp_ball.ball_id = object_instance_handle.hex()
        fresh_Ball = self.my_ball_controller.ball_data.get_ball(temp_ball.ball_id)
        if fresh_Ball is None:
            # Create new remote Ball if it doesn't exist
            self.my_ball_controller.ball_data.add_ball(temp_ball, is_local=False)
            log_incoming(f"Received new remote Ball {temp_ball.ball_id}")
            fresh_Ball = temp_ball
            self.my_ball_controller.list_refresh_needed = True
        else:
            fresh_Ball.x = temp_ball.x
            fresh_Ball.y = temp_ball.y
            fresh_Ball.dx = temp_ball.dx
            fresh_Ball.dy = temp_ball.dy
            fresh_Ball.color = temp_ball.color
            fresh_Ball.ball_id = temp_ball.ball_id

