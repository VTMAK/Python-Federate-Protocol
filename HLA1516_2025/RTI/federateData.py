from HLA1516_2025.RTI.handles import (AttributeHandle, FederateHandle, InteractionClassHandle,
                                    ObjectClassHandle, ObjectInstanceHandle, ParameterHandle)


class FederateData():
    def __init__(self):
        """
            Initialize federate data container with default network / state tracking values.

            Args:
                None
            Side Effects:
                Populates instance attributes with default values (addresses, flags, caches, maps).
            Notes:
                Holds runtime state shared with the ambassador; lists / dicts allow external inspection by tests.
        """
        self.my_fed_pro_addr : str = "127.0.0.1"
        self.my_fed_pro_port : int = 15164
        self.my_connection_lost : bool = False
        self.my_federate_resigned : bool = False
        self.my_report_federation_executions_received : bool = False
        self.my_report_federation_execution_members_received : bool = False
        self.name_reservation_returned : bool = False
        self.my_name_reservation_succeeded : bool = False
        self.my_federate_executions : list[FederateHandle] = []
        self.my_attr_name_handles : dict[ObjectClassHandle, dict[str, AttributeHandle]] = {} #may need to change type
        self.my_attr_handle_names : dict[ObjectClassHandle, dict[AttributeHandle, str]] = {} #may need to change type
        self.my_object_instance_name_handles : dict[FederateHandle, dict[str, tuple[ObjectInstanceHandle, ObjectClassHandle]]] = {}
        self.my_object_instance_handle_names : dict[FederateHandle, dict[ObjectInstanceHandle, str]] = {}
        self.my_object_instance_attrs : dict[ObjectInstanceHandle, dict[AttributeHandle, bytes]] = {}
        self.my_object_instance_classes : dict[ObjectInstanceHandle, ObjectClassHandle] = {}
        self.my_interaction_parameter_values : dict[FederateHandle, dict[InteractionClassHandle, dict[ParameterHandle, bytes]]] = {}


    def clear(self):
        """
            Reset all runtime state to initial defaults, clearing dynamic caches and status flags.

            Args:
                None
            Side Effects:
                Restores container attributes to default values; empties mutable maps/lists.
            Notes:
                Recreates some flags (e.g., report_federation_execution_not_exist) to ensure consistency.
        """
        self.my_fed_pro_addr : str = "127.0.0.1"
        self.my_fed_pro_port : int = 15164
        self.my_connection_lost : bool = False
        self.my_federate_resigned : bool = False
        self.name_reservation_returned : bool = False
        self.my_name_reservation_succeeded : bool = False
        self.my_report_federation_execution_not_exist : bool = False
        self.my_report_federation_executions_received : bool = False
        self.my_report_federation_execution_members_received : bool = False
        self.my_object_instance_name_handles.clear()
        self.my_object_instance_handle_names.clear()
        self.my_object_instance_attrs.clear()
        self.my_object_instance_classes.clear()
        self.my_interaction_parameter_values.clear()