"""
    Python Federate Protocol © 2025 by MAK Technologies is licensed under CC BY-ND 4.0.
    To view a copy of this license, visit https://creativecommons.org/licenses/by-nd/4.0/
"""
import time
from libsrc.rtiUtil.logger import *
from urllib import response
from HLA1516_2025.RTI.enums import Enums
import HLA1516_2025.RTI.exception as RtiException 
import libsrc.rtiUtil.exception as Exception 
from HLA1516_2025.RTI.rtiAmbassador import RtiAmbassador
from libsrc.fedPro import fedProMessage, heartBeatMessage
from HLA1516_2025.RTI.rtiConfiguration import RtiConfiguration
from libsrc.fedProWrapper.fedProMessageHandler import FedProMsgHandler
from libsrc.fedPro.callRequestMessage import CallRequestMessage
from HLA1516_2025.RTI.federateAmbassador import FederateAmbassador
from FedProProtobuf import RTIambassador_pb2, datatypes_pb2
from HLA1516_2025.RTI.typedefs import ConfigurationResult
from libsrc.fedProWrapper.fedProMessageHandler import the_call_response_ref
from HLA1516_2025.RTI.handles import AttributeHandle, FederateHandle, ObjectClassHandle,  ObjectInstanceHandle, InteractionClassHandle, ParameterHandle

class Configuration:
    def __init__(self):
        self.federate_name : str = ""
        self.federate_type : str = ""
        self.federation_name : str = ""
        self.plain_text_password : str = ""
        self.fom_modules : list[str] = []
        self.use_mom = False
        self.subscribe_universally = False
        self.callback_model = Enums.CallbackModel.HLA_EVOKED

_the_connect_with_configuration_response = RTIambassador_pb2.CallResponse()

class RtiAmbassadorFedPro(RtiAmbassador):
    """RTI ambassador uses FedProMessageHandler to communicate with the RTI via FedPro protocol."""
#=====================================================Initialize===============================================================
    def __init__(self):
        """
            Description:
                Initialize RTI Ambassador FedPro wrapper, constructing message handler and caching structures for handles.
            Inputs:
                self: RtiAmbassadorFedPro instance being created.
            Outputs:
                Populates internal dictionaries/maps, message handler, and default timing/connection fields.
            Exceptions:
                None.
        """
        super().__init__()
        self.my_msg_handler = FedProMsgHandler()
        self.my_obj_instance_attrs : dict[ObjectInstanceHandle, AttributeHandle] = {}
        self.my_federate_handle : FederateHandle
        # maybe add a dict for interactions/parameters
        self.rti_connection : bool = False
        self.my_is_connection_ok : bool = False
        self.my_wait_time : float = 10.0        
        self.my_obj_name_handles : dict[str, ObjectClassHandle] = {}
        self.my_obj_handle_names : dict[ObjectClassHandle, str] = {}
        self.my_interaction_name_handles : dict[str, InteractionClassHandle] = {}
        self.my_interaction_handle_names : dict[InteractionClassHandle, str] = {}
        self.my_parameter_name_handles : dict[InteractionClassHandle, dict[str, ParameterHandle]] = {}
#===============================================================================================================================

#=====================================================RTI Services===============================================================
    def connect(self, federateAmbassador: FederateAmbassador, configuration: RtiConfiguration)->ConfigurationResult:
        """
            Description:
                Establish a FedPro session and perform RTI connect with provided configuration; returns connection result details.
            Inputs:
                self: rtiAmbassadorFedPro instance.
                federateAmbassador (federateAmbassadorFedPro): Federate ambassador containing network address/port.
                configuration (RtiConfiguration): RTI configuration parameters (address, name, additional settings).
            Outputs:
                Returns ConfigurationResult protobuf (populated) on success; sets internal connection flags.
            Exceptions:
                Raises FedProSocketError if session initialization fails; RTIinternalError if response not received.
        """

        log_outgoing(f"DtRtiAmbassadorFedPro::connect\nrtiAddr: {federateAmbassador.my_data.my_fed_pro_addr} : {str(federateAmbassador.my_data.my_fed_pro_port)}\
            \nconfigName:  {configuration.configuration_name}\nadditional settings: {configuration.additional_settings}")
        
        # Setup socket connection
        if self.my_msg_handler.initializeSession(federateAmbassador):
            log_info("FedPro Client Socket Initialized")
        else:
            raise Exception.FedProSocketError("Failed to initialize FedPro Client Socket")
        
        heartbeat = self.my_msg_handler.send_and_wait(heartBeatMessage.HeartbeatMessage(), fedProMessage.MsgType.CTRL_HEARTBEAT_RESPONSE, 10)
        
        call_request = RTIambassador_pb2.CallRequest()
        conn_request = call_request.connectWithConfigurationRequest
        rti_configuration = conn_request.rtiConfiguration
        rti_configuration.rtiAddress = configuration.rti_address[0]
        rti_configuration.rtiAddress += ":"
        rti_configuration.rtiAddress += str(configuration.rti_address[1])
        rti_configuration.configurationName = configuration.configuration_name
        rti_configuration.additionalSettings = configuration.additional_settings
        # Set FedPro payload in call request message
        call_request_msg = CallRequestMessage(call_request)
        self.rti_connection = self.my_msg_handler.send_and_wait(call_request_msg, the_call_response_ref.CONNECTWITHCONFIGURATIONRESPONSE_FIELD_NUMBER, 30)
        if self.rti_connection:
            self.my_is_connection_ok = True
            conn_result = ConfigurationResult()
            conn_result.addressUsed = self.my_msg_handler.my_fedPro_response.my_response_buf.connectWithCredentialsResponse.configurationResult.addressUsed
            conn_result.configurationUsed = self.my_msg_handler.my_fedPro_response.my_response_buf.connectWithCredentialsResponse.configurationResult.configurationUsed
            conn_result.additionalSettingsResultCode = self.my_msg_handler.my_fedPro_response.my_response_buf.connectWithCredentialsResponse.configurationResult.additionalSettingsResultCode
            conn_result.message = self.my_msg_handler.my_fedPro_response.my_response_buf.connectWithCredentialsResponse.configurationResult.message
            return conn_result
        else:
            log_error("ERROR: Failed to get connection response from RTI")
            self.my_is_connection_ok = False
            raise RtiException.RTIinternalError("Failed to connect to RTI Ambassador")

    # !ADD connect with credentials

    # !ADD create federation execution with single FOM module


    def create_fed_ex(self, federation_name: str, fom_modules: list):
        """
            Description:
                Create a federation execution with one or more FOM module URLs.
            Inputs:
                self: rtiAmbassadorFedPro instance.
                federation_name (str): Name of the federation execution to create.
                fom_modules (list[str]): Iterable of FOM module URLs.
            Outputs:
                None directly; logs success or raises on failure.
            Exceptions:
                Raises RTIinternalError for connection issues, unexpected responses, or creation failure.
        """
        
        if not self.my_is_connection_ok:
            raise RtiException.RTIinternalError("RTI Ambassador is not connected")
        if self.my_msg_handler.federate_ambassador_handler is None:
            raise RtiException.RTIinternalError("RTI Ambassador connection is not initialized")
        
        log_outgoing(f"DtRtiAmbassadorFedPro::create_fed_ex\nfederationName: {federation_name}\nfomModules: ")
        log_outgoing(fom_modules)

        call_request = RTIambassador_pb2.CallRequest()
        create_request = call_request.createFederationExecutionWithModulesRequest
        create_request.federationName = federation_name
        for module in fom_modules:
            fom = create_request.fomModules.fomModule.add()
            fom.url = module

        call_request_msg = CallRequestMessage(call_request)
        if self.my_msg_handler.send_and_wait(call_request_msg, the_call_response_ref.CREATEFEDERATIONEXECUTIONWITHMODULESRESPONSE_FIELD_NUMBER, 10):
            log_incoming("Federation execution created successfully")
        else:
            log_warning(self.my_msg_handler.my_fedPro_response)
            if self.my_msg_handler.my_poll_result == -1:
                if self.my_msg_handler.my_fedPro_response.my_response_buf.exceptionData.exceptionName == "FederationExecutionAlreadyExists":
                    log_warning("Federation execution already exists")
                else:
                    log_error("ERROR: Failed to create federation execution")
                    raise RtiException.RTIinternalError("Failed to create federation execution")
            else:
                log_error("ERROR: Failed to create federation execution, Unexpected or No responses received")
                raise RtiException.RTIinternalError("Failed to create federation execution")

    # !ADD create federation execution with multiple FOM modules and MIM module

    # !ADD Destroy a federation execution

    # !ADD List all federation executions

    # !ADD Join a federation with no name specified

    def join_fed_ex(self, federate_name: str, federate_type: str, federation_name: str, fom_modules: list)-> FederateHandle:
        """
            Description:
                Join a federation execution with specified federate name/type and additional FOM modules.
            Inputs:
                self: rtiAmbassadorFedPro instance.
                federate_name (str): Federate name (unique or reserved).
                federate_type (str): Federate type classification string.
                federation_name (str): Target federation execution name.
                fom_modules (list[str]): Additional FOM module URLs to include.
            Outputs:
                Returns FederateHandle on success; caches handle internally.
            Exceptions:
                Raises RTIinternalError on failure or missing/invalid response.
        """

        log_outgoing("\nDtRtiAmbassadorFedPro::join_fed_ex\nfederateName: " + federate_name\
            + "\nfederateType: " + federate_type + "\nfederationName: " + federation_name + "\n")
        
        call_request = RTIambassador_pb2.CallRequest()
        join_request = call_request.joinFederationExecutionWithNameAndModulesRequest
        join_request.federateName = federate_name
        join_request.federateType = federate_type
        join_request.federationName = federation_name
        for module in fom_modules:
            fom = join_request.additionalFomModules.fomModule.add()
            fom.url = module

        call_request_msg = CallRequestMessage(call_request)
        if self.my_msg_handler.send_and_wait(call_request_msg, the_call_response_ref.JOINFEDERATIONEXECUTIONWITHNAMEANDMODULESRESPONSE_FIELD_NUMBER, 10):
            log_incoming("Federation execution joined successfully")
            self.my_federate_handle = FederateHandle(self.my_msg_handler.my_fedPro_response.my_response_buf.joinFederationExecutionWithNameAndModulesResponse.result.federateHandle.data)
            return self.my_federate_handle
        else:
            log_warning(self.my_msg_handler.my_fedPro_response)
            if self.my_msg_handler.my_poll_result == -1:
                log_warning("ERROR: Failed to join federation execution")
            else:
                log_error("ERROR: Failed to join federation execution, Unexpected or No responses received")
            raise RtiException.RTIinternalError("Failed to create federation execution")

    # !ADD resign a Federation Execution

    # !ADD register sync point

    # !ADD register sync point with synchronization set

    # !ADD sync point achieved

    # !ADD request federation save

    # !ADD request federation save with time

    # !ADD federate save begun

    # !ADD federate save complete

    # !ADD federate save not complete

    # !ADD abort federation save

    # !ADD query federation save status

    # !ADD request federation restore

    # !ADD federate restore complete

    # !ADD federate restore not complete

    # !ADD abourt federation restore

    # !ADD query federation restore status

    def get_object_class_handle(self, object_class_name: str)-> ObjectClassHandle:
        """
            Description:
                Retrieve (and cache) the ObjectClassHandle for a named object class via remote call if not already cached.
            Inputs:
                self: rtiAmbassadorFedPro instance.
                object_class_name (str): HLA object class name.
            Outputs:
                Returns ObjectClassHandle instance; caches forward and reverse name mappings.
            Exceptions:
                Raises RTIinternalError when remote request fails or no valid response returned.
        """
        log_outgoing("\nDtRtiAmbassadorFedPro::get_object_class_handle\nobjectClassName: " + object_class_name + "\n")

        object_class_handle = self.my_obj_name_handles.get(object_class_name)
        if object_class_handle is not None:
            log_info(f"Found cached object handle {object_class_handle}.")
            return object_class_handle
        
        call_request = RTIambassador_pb2.CallRequest()
        get_object_class_handle_request = call_request.getObjectClassHandleRequest
        get_object_class_handle_request.objectClassName = object_class_name

        call_request_msg = CallRequestMessage(call_request)
        if self.my_msg_handler.send_and_wait(call_request_msg, the_call_response_ref.GETOBJECTCLASSHANDLERESPONSE_FIELD_NUMBER, 6):            
            object_class_handle = ObjectClassHandle(self.my_msg_handler.my_fedPro_response.my_response_buf.getObjectClassHandleResponse.result.data)
            self.my_obj_name_handles[object_class_name] = object_class_handle
            self.my_obj_handle_names[self.my_obj_name_handles[object_class_name]] = object_class_name
            self.my_msg_handler.federate_ambassador_handler.my_Federate_Ambassador.my_data.my_attr_handle_names[object_class_handle] = {}
            self.my_msg_handler.federate_ambassador_handler.my_Federate_Ambassador.my_data.my_attr_name_handles[object_class_handle] = {}
            log_incoming("+++++++++++")
            log_incoming("Object class handle retreived successfully")
            log_incoming(f"{object_class_name}:{self.my_obj_name_handles[object_class_name]}")
            log_incoming("+++++++++++")
            return self.my_obj_name_handles[object_class_name]
        else:
            log_warning(self.my_msg_handler.my_fedPro_response)
            if self.my_msg_handler.my_poll_result == -1:
                log_warning("ERROR: Failed Get object class handle, exception received")
            else:
                log_error("ERROR: Failed Get object class handle, Unexpected or No responses received")
            raise RtiException.RTIinternalError("Failed to get object class handle")


    # !ADD unpublish object class

    def get_attribute_handle(self, class_handle: ObjectClassHandle, attr_name: str)-> AttributeHandle:
        """
            Description:
                Resolve attribute handle for a given attribute name within an object class, using cache or remote query.
            Inputs:
                self: rtiAmbassadorFedPro instance.
                class_handle (ObjectClassHandle): Target object class handle.
                attr_name (str): Attribute name to resolve.
            Outputs:
                AttributeHandle (cached or newly fetched) for the named attribute.
            Exceptions:
                Raises RTIinternalError when remote resolution fails or unexpected/no response.
        """
        log_outgoing("\nDtRtiAmbassadorFedPro::get_attribute_handle\nattrName: " + attr_name + "\n")

        attr_handle_map = self.my_msg_handler.federate_ambassador_handler.my_Federate_Ambassador.my_data.my_attr_name_handles.get(class_handle)
        if attr_handle_map is not None:
            attr_handle = attr_handle_map.get(attr_name)
            if attr_handle is not None:
                log_info(f"Found cached object handle {attr_handle}.")
                return attr_handle
        call_request = RTIambassador_pb2.CallRequest()
        get_attribute_handle_request = call_request.getAttributeHandleRequest
        get_attribute_handle_request.objectClass.data = class_handle.data
        get_attribute_handle_request.attributeName = attr_name

        call_request_msg = CallRequestMessage(call_request)
        
        if self.my_msg_handler.send_and_wait(call_request_msg, the_call_response_ref.GETATTRIBUTEHANDLERESPONSE_FIELD_NUMBER, 6):
            log_incoming(f"{attr_name}:{self.my_msg_handler.my_fedPro_response.my_response_buf}")
            log_incoming(f"{self.my_msg_handler.my_fedPro_response.my_response_buf.getAttributeHandleResponse.result.data}")
            log_incoming("Object class handle retreived successfully")
            attribute_handle = AttributeHandle(self.my_msg_handler.my_fedPro_response.my_response_buf.getAttributeHandleResponse.result.data)
            self.my_msg_handler.federate_ambassador_handler.my_Federate_Ambassador.my_data.my_attr_handle_names[class_handle][attribute_handle] = attr_name
            self.my_msg_handler.federate_ambassador_handler.my_Federate_Ambassador.my_data.my_attr_name_handles[class_handle][attr_name] = attribute_handle
            return attribute_handle
        else:
            log_warning(self.my_msg_handler.my_fedPro_response)
            if self.my_msg_handler.my_poll_result == -1:
                log_warning("ERROR: Failed to create federation execution, exception received")

            else:
                log_error("ERROR: Failed to create federation execution, Unexpected or No responses received")
            raise RtiException.RTIinternalError("Failed to get attribute handle")
        

    def get_interaction_class_handle(self, interaction_name: str)-> InteractionClassHandle:
        """
            Description:
                Resolve interaction class handle by name, retrieving from cache or performing remote lookup.
            Inputs:
                self: rtiAmbassadorFedPro instance.
                interaction_name (str): Interaction class name.
            Outputs:
                InteractionClassHandle for the named interaction.
            Exceptions:
                Raises RTIinternalError on failure or missing response.
        """
        log_outgoing("\nDtRtiAmbassadorFedPro::get_interaction_class_handle\ninteractionClassName: " + interaction_name + "\n")

        interaction_class_handle = self.my_interaction_name_handles.get(interaction_name)
        if interaction_class_handle is not None:
            log_info(f"Found cached interaction handle {interaction_class_handle}.")
            return interaction_class_handle
        
        call_request = RTIambassador_pb2.CallRequest()
        get_interaction_class_handle_request = call_request.getInteractionClassHandleRequest
        get_interaction_class_handle_request.interactionClassName = interaction_name

        call_request_msg = CallRequestMessage(call_request)
        
        if self.my_msg_handler.send_and_wait(call_request_msg, the_call_response_ref.GETINTERACTIONCLASSHANDLERESPONSE_FIELD_NUMBER, 6):
            interaction_class_handle = InteractionClassHandle(self.my_msg_handler.my_fedPro_response.my_response_buf.getInteractionClassHandleResponse.result.data)
            self.my_interaction_name_handles[interaction_name] = interaction_class_handle
            self.my_interaction_handle_names[self.my_interaction_name_handles[interaction_name]] = interaction_name
            self.my_parameter_name_handles[interaction_class_handle] = {}

            log_incoming("Interaction class handle retreived successfully")
            log_incoming(f"{interaction_name}:{self.my_interaction_name_handles[interaction_name]}")
            return self.my_interaction_name_handles[interaction_name]
        else:
            log_warning(self.my_msg_handler.my_fedPro_response)
            if self.my_msg_handler.my_poll_result == -1:
                log_warning("ERROR: Failed Get interaction class handle, exception received")
            else:
                log_error("ERROR: Failed Get interaction class handle, Unexpected or No responses received")
            raise RtiException.RTIinternalError("Failed to get interaction class handle")
        
    def get_parameter_handle(self, interaction_handle: InteractionClassHandle, param_name: str)-> ParameterHandle:  
        """
            Description:
                Fetch (or return cached) parameter handle for a given interaction parameter.
            Inputs:
                self: rtiAmbassadorFedPro instance.
                interaction_handle (InteractionClassHandle): Handle of parent interaction class.
                param_name (str): Parameter name to resolve.
            Outputs:
                ParameterHandle corresponding to param_name.
            Exceptions:
                Raises RTIinternalError on remote failure or absent response.
        """
        log_outgoing("\nDtRtiAmbassadorFedPro::get_parameter_handle\nparamName: " + param_name + "\n")

        param_handle_map = self.my_parameter_name_handles.get(interaction_handle)
        if param_handle_map is not None:
            param_handle = param_handle_map.get(param_name)
            if param_handle is not None:
                log_info(f"Found cached parameter handle {param_handle}.")
                return param_handle

        call_request = RTIambassador_pb2.CallRequest()
        get_parameter_handle_request = call_request.getParameterHandleRequest
        get_parameter_handle_request.interactionClass.data = interaction_handle.data
        get_parameter_handle_request.parameterName = param_name

        call_request_msg = CallRequestMessage(call_request)
        
        if self.my_msg_handler.send_and_wait(call_request_msg, the_call_response_ref.GETPARAMETERHANDLERESPONSE_FIELD_NUMBER, 6):
            self.my_parameter_name_handles[interaction_handle][param_name] = ParameterHandle(self.my_msg_handler.my_fedPro_response.my_response_buf.getParameterHandleResponse.result.data)
            log_incoming(f"{param_name}:{self.my_parameter_name_handles[interaction_handle][param_name]}")
            log_incoming("Parameter handle retreived successfully")
            return self.my_parameter_name_handles[interaction_handle][param_name]
        else:
            log_warning(self.my_msg_handler.my_fedPro_response)
            if self.my_msg_handler.my_poll_result == -1:
                log_warning("ERROR: Failed to get parameter handle, exception received")

            else:
                log_error("ERROR: Failed to get parameter handle, Unexpected or No responses received")
            raise RtiException.RTIinternalError("Failed to get parameter handle")
    
    def subscribe_object_class_attributes(self, class_handle: ObjectClassHandle, attr_set: list[AttributeHandle], active=True):
        """
            Description:
                Subscribe (actively or passively) to a set of attributes for an object class.
            Inputs:
                self: rtiAmbassadorFedPro instance.
                class_handle (ObjectClassHandle): Target object class.
                attr_set (dict[str, AttributeHandle]): Mapping of attribute names to handles.
                active (bool, default True): Whether subscription is active; False for passive.
            Outputs:
                None on success (logs confirmation); raises on failure.
            Exceptions:
                Raises RTIinternalError if subscription fails or lacks response.
        """
        log_outgoing("DtRtiAmbassadorFedPro::subscribe_object_class_attributes\nclassHandle: ")
        log_outgoing(class_handle)
        log_outgoing("attributeSet: ")
        log_outgoing(attr_set)

        call_request = RTIambassador_pb2.CallRequest()
        if active:
            sub_attr_request = call_request.subscribeObjectClassAttributesRequest
            sub_attr_response = the_call_response_ref.SUBSCRIBEOBJECTCLASSATTRIBUTESRESPONSE_FIELD_NUMBER
        else:
            sub_attr_request = call_request.subscribeObjectClassAttributesPassivelyRequest
            sub_attr_response = the_call_response_ref.SUBSCRIBEOBJECTCLASSATTRIBUTESPASSIVELYRESPONSE_FIELD_NUMBER
        sub_attr_request.objectClass.data = class_handle
        for attr_handle in attr_set:
            temp_req = sub_attr_request.attributes.attributeHandle.add()
            temp_req.data = attr_handle.data

        call_request_msg = CallRequestMessage(call_request)        
        if self.my_msg_handler.send_and_wait(call_request_msg, sub_attr_response, 8):
            log_incoming("Subscribed to object class attributes successfully")
        else:
            log_warning(self.my_msg_handler.my_fedPro_response)
            if self.my_msg_handler.my_poll_result == -1:
                log_warning("ERROR: Failed to subscribe to object class attributes, exception received")
            else:
                log_error("ERROR: Failed to subscribe to object class attributes, Unexpected or No responses received")
            raise RtiException.RTIinternalError("Failed to subscribe to object class attributes, no response received")

    def publish_object_class_attributes(self, class_handle: ObjectClassHandle, attr_set: list[AttributeHandle]):
        """
            Description:
                Publish an attribute set for the specified object class to advertise ownership/updates.
            Inputs:
                self: rtiAmbassadorFedPro instance.
                class_handle (ObjectClassHandle): Object class to publish attributes for.
                attr_set (dict[str, AttributeHandle]): Mapping of attribute names to handles.
            Outputs:
                True on early return when attr_set empty; otherwise None (logs success) or raises on failure.
            Exceptions:
                Raises RTIinternalError on publish failure or no response.
        """
        log_outgoing("\nDtRtiAmbassadorFedPro::publish_object_class_attributes\nclassHandle: ")
        log_outgoing(class_handle)
        log_outgoing("\nattributeSet: ")
        log_outgoing(attr_set)
        
        if not attr_set:
            log_warning("WARNING: Attempting to publish empty attribute set!")
            return False
        
        call_request = RTIambassador_pb2.CallRequest()
        pub_attr_request = call_request.publishObjectClassAttributesRequest

        pub_attr_request.objectClass.data = class_handle.data
        for attr_handle in attr_set:
            temp_req = pub_attr_request.attributes.attributeHandle.add()
            temp_req.data = attr_handle
            
        call_request_msg = CallRequestMessage(call_request)
        
        if self.my_msg_handler.send_and_wait(call_request_msg, the_call_response_ref.PUBLISHOBJECTCLASSATTRIBUTESRESPONSE_FIELD_NUMBER, 8):
            log_incoming("Object class attributes published successfully")
        else:
            log_warning(self.my_msg_handler.my_fedPro_response)
            if self.my_msg_handler.my_poll_result == -1:
                log_error("ERROR: Failed to publish object class attributes, exception received")
            else:
                log_error("ERROR: Failed to publish object class attributes, Unexpected or No responses received")
            raise RtiException.RTIinternalError("Failed to publish object class attributes, no response received")

    # !ADD unsubscribe/unpublish object class attributes

    def subscribe_interaction_class(self, interaction_handle: InteractionClassHandle):
        """
            Description:
                Subscribe to receive interactions of a given class.
            Inputs:
                self: rtiAmbassadorFedPro instance.
                interaction_handle (InteractionClassHandle): Interaction class handle.
            Outputs:
                None; logs success or raises on failure.
            Exceptions:
                Raises RTIinternalError when subscription fails or no response.
        """
        log_outgoing("\nDtRtiAmbassadorFedPro::subscribe_interaction_class\ninteractionHandle: ")
        log_outgoing(interaction_handle)
        
        call_request = RTIambassador_pb2.CallRequest()
        sub_interaction_request = call_request.subscribeInteractionClassRequest
        sub_interaction_request.interactionClass.data = interaction_handle.data
        sub_interaction_response = the_call_response_ref.SUBSCRIBEINTERACTIONCLASSRESPONSE_FIELD_NUMBER
        
        call_request_msg = CallRequestMessage(call_request)
        
        if self.my_msg_handler.send_and_wait(call_request_msg, sub_interaction_response, 6):
            log_incoming("Subscribed to interaction class successfully")
        else:
            log_warning(self.my_msg_handler.my_fedPro_response)
            if self.my_msg_handler.my_poll_result == -1:
                log_error("ERROR: Failed to subscribe to interaction class, exception received")
            else:
                log_error("ERROR: Failed to subscribe to interaction class, Unexpected or No responses received")
            raise RtiException.RTIinternalError("Failed to subscribe to interaction class, no response received")


    def publish_interaction_class(self, interaction_handle: InteractionClassHandle):
        """
            Description:
                Publish an interaction class so this federate may send it.
            Inputs:
                self: rtiAmbassadorFedPro instance.
                interaction_handle (InteractionClassHandle): Interaction class to publish.
            Outputs:
                None; logs success or raises on failure.
            Exceptions:
                Raises RTIinternalError if publish attempt fails or no response.
        """
        log_outgoing("\nDtRtiAmbassadorFedPro::publish_interaction_class\ninteractionHandle: ")
        log_outgoing(interaction_handle)
        
        call_request = RTIambassador_pb2.CallRequest()
        pub_interaction_request = call_request.publishInteractionClassRequest
        pub_interaction_request.interactionClass.data = interaction_handle.data
        
        call_request_msg = CallRequestMessage(call_request)
        
        if self.my_msg_handler.send_and_wait(call_request_msg, the_call_response_ref.PUBLISHINTERACTIONCLASSRESPONSE_FIELD_NUMBER, 6):
            log_incoming("Interaction class published successfully")
        else:
            log_warning(self.my_msg_handler.my_fedPro_response)
            if self.my_msg_handler.my_poll_result == -1:
                log_error("ERROR: Failed to publish interaction class, exception received")
            else:
                log_error("ERROR: Failed to publish interaction class, Unexpected or No responses received")
            raise RtiException.RTIinternalError("Failed to publish interaction class, no response received")


    # !ADD unpublish interaction class



    def reserve_object_instance_name(self, object_instance_name: str):
        """
            Description:
                Reserve a unique object instance name within the federation execution.
            Inputs:
                self: rtiAmbassadorFedPro instance.
                object_instance_name (str): Desired object instance name.
            Outputs:
                None; logs success or raises on failure.
            Exceptions:
                Raises RTIinternalError on reservation failure or absent response.
        """
        log_outgoing(f"\nDtRtiAmbassadorFedPro::reserve_object_instance_name\nobjectInstanceName: {object_instance_name}\n")
        
        call_request = RTIambassador_pb2.CallRequest()
        reserve_request = call_request.reserveObjectInstanceNameRequest
        reserve_request.objectInstanceName = object_instance_name
        
        call_request_msg = CallRequestMessage(call_request)
        
        if self.my_msg_handler.send_and_wait(call_request_msg, the_call_response_ref.RESERVEOBJECTINSTANCENAMERESPONSE_FIELD_NUMBER, 8):
            log_incoming("Object Instance Name Reserved successfully")
        else:
            log_warning(self.my_msg_handler.my_fedPro_response)
            if self.my_msg_handler.my_poll_result == -1:
                log_error("ERROR: Failed to Reserve Object Instance Name, exception received")
            else:
                log_error("ERROR: Failed to Reserve Object Instance Name, Unexpected or No responses received")
            raise RtiException.RTIinternalError("Failed to Reserve Object Instance Name")


    def  register_object_instance(self, object_class_handle: ObjectClassHandle, object_instance_name: str="")-> ObjectInstanceHandle:
        """
            Description:
                Register a new object instance of a specified class with an optional (required here) name.
            Inputs:
                self: rtiAmbassadorFedPro instance.
                object_class_handle (ObjectClassHandle): Class handle of the object to register.
                object_instance_name (str, optional): Name for the instance; required by this implementation.
            Outputs:
                Returns ObjectInstanceHandle for the newly registered instance.
            Exceptions:
                Raises RTIinternalError on invalid response, missing name, or registration failure.
        """
        log_outgoing(f"\nDtRtiAmbassadorFedPro::register_object_instance\nobjectClassHandle: {object_class_handle}")
        if object_instance_name:
            log_outgoing(f"objectInstanceName: {object_instance_name}\n")
        
        call_request = RTIambassador_pb2.CallRequest()

        if object_instance_name is not "":
            register_request = call_request.registerObjectInstanceWithNameRequest
            # Debug: Check the structure before setting values
            register_request.objectClass.data = object_class_handle.data
            register_request.objectInstanceName = object_instance_name
            
            call_request_msg = CallRequestMessage(call_request)
            register_response = self.my_msg_handler.send_and_wait(call_request_msg, the_call_response_ref.REGISTEROBJECTINSTANCEWITHNAMERESPONSE_FIELD_NUMBER, 15)
        else:
            raise RtiException.RTIinternalError("Registering object instance without a name is not supported in this implementation.")
        
        if register_response:
            inst_handle = ObjectInstanceHandle(self.my_msg_handler.my_fedPro_response.my_response_buf.registerObjectInstanceWithNameResponse.result.data)
            log_incoming("Object Instance Registered successfully")
            log_incoming(f"Handle: {inst_handle}")
            return inst_handle
        else:
            log_warning(self.my_msg_handler.my_fedPro_response)
            if self.my_msg_handler.my_poll_result == -1:
                log_error("ERROR: Failed to register object instance, exception received")
            else:
                log_error("ERROR: Failed to register object instance, Unexpected or No responses received")
            raise RtiException.RTIinternalError("Failed to register object instance due to missing/invalid response")
# ===================================================================

# ===================================================================

    def destroy_federation_execution(self, federation_name: str)-> bool:
        """
            Description:
                Destroy a federation execution identified by name.
            Inputs:
                self: rtiAmbassadorFedPro instance.
                federation_name (str): Name of the federation execution to destroy.
            Outputs:
                True on success; False if None response (with error logged).
            Exceptions:
                Propagates any unexpected Exception after logging; raises if not connected.
        """
        if not self.my_is_connection_ok:
            raise RtiException.RTIinternalError("RTI Ambassador is not connected")
        
        log_outgoing(f"DtRtiAmbassadorFedPro::destroy_federation_execution\nfederationName: {federation_name}")
        
        try:
            call_request = RTIambassador_pb2.CallRequest()
            destroy_request = call_request.destroyFederationExecutionRequest
            destroy_request.federationName = federation_name
            
            call_request_msg = CallRequestMessage(call_request)
            destroy_response = self.my_msg_handler.send_and_wait(call_request_msg, the_call_response_ref.DESTROYFEDERATIONEXECUTIONRESPONSE_FIELD_NUMBER, 6)
            
            if destroy_response is None:
                log_error("ERROR: Received None response for destroy federation execution")
                return False
                
            log_incoming("Federation execution destroyed successfully.")
            return True
            
        except Exception as e:
            log_error(f"Exception during destroy_federation_execution: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            raise e

    def list_federation_executions(self)-> bool:
        """
            Description:
                Request and list all active federation executions from the RTI.
            Inputs:
                self: rtiAmbassadorFedPro instance.
            Outputs:
                True on success; False if None response.
            Exceptions:
                Raises RTIinternalError if not connected; propagates unexpected exceptions.
        """
        if not self.my_is_connection_ok:
            raise RtiException.RTIinternalError("RTI Ambassador is not connected")
        
        log_outgoing("DtRtiAmbassadorFedPro::list_federation_executions")
        
        try:
            call_request = RTIambassador_pb2.CallRequest()
            list_request = call_request.listFederationExecutionsRequest
            list_request.SetInParent()
            
            call_request_msg = CallRequestMessage(call_request)
            list_response = self.my_msg_handler.send_and_wait(call_request_msg, the_call_response_ref.LISTFEDERATIONEXECUTIONSRESPONSE_FIELD_NUMBER, 3)
            
            if list_response is None:
                log_error("ERROR: Received None response for list federation executions")
                return False
                
            log_incoming("Federation executions listed successfully.")
            return True
            
        except Exception as e:
            log_error(f"Exception during list_federation_executions: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            raise e

    def resign_federation_execution(self, resign_action: str = "NO_ACTION")-> bool:
        """
            Description:
                Resign from a federation execution using a specified resign action strategy.
            Inputs:
                self: rtiAmbassadorFedPro instance.
                resign_action (str, default 'NO_ACTION'): Action keyword controlling resource divestiture.
            Outputs:
                True on success; False on None response.
            Exceptions:
                Raises RTIinternalError if not connected; propagates unexpected exceptions.
        """
        if not self.my_is_connection_ok:
            raise RtiException.RTIinternalError("RTI Ambassador is not connected")
        
        log_outgoing("DtRtiAmbassadorFedPro::resign_federation_execution")
        
        try:
            call_request = RTIambassador_pb2.CallRequest()
            resign_request = call_request.resignFederationExecutionRequest
            
            # Map resign action string to enum value
            resign_actions = {
                "NO_ACTION": 0,
                "UNCONDITIONALLY_DIVEST_ATTRIBUTES": 1,
                "DELETE_OBJECTS": 2,
                "CANCEL_PENDING_OWNERSHIP_ACQUISITIONS": 3,
                "DELETE_OBJECTS_THEN_DIVEST": 4,
                "CANCEL_THEN_DELETE_THEN_DIVEST": 5
            }
            
            resign_request.resignAction = resign_actions.get(resign_action, 0)
            
            call_request_msg = CallRequestMessage(call_request)
            resign_response = self.my_msg_handler.send_and_wait(call_request_msg, the_call_response_ref.RESIGNFEDERATIONEXECUTIONRESPONSE_FIELD_NUMBER, 3)
            
            if resign_response is None:
                log_error("ERROR: Received None response for resign federation execution")
                return False
                
            log_incoming("Resigned from federation execution successfully.")
            return True
            
        except Exception as e:
            log_error(f"Exception during resign_federation_execution: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            raise e

    def unpublish_object_class(self, class_handle: ObjectClassHandle)-> bool:
        """
            Description:
                Withdraw publication of an object class.
            Inputs:
                self: rtiAmbassadorFedPro instance.
                class_handle (ObjectClassHandle): Handle of object class to unpublish.
            Outputs:
                True on success; False on None response.
            Exceptions:
                Raises RTIinternalError if not connected; propagates unexpected exceptions.
        """
        if not self.my_is_connection_ok:
            raise RtiException.RTIinternalError("RTI Ambassador is not connected")
        
        log_outgoing(f"DtRtiAmbassadorFedPro::unpublish_object_class")
        
        try:
            call_request = RTIambassador_pb2.CallRequest()
            unpublish_request = call_request.unpublishObjectClassRequest
            unpublish_request.objectClass.data = class_handle.data
            
            call_request_msg = CallRequestMessage(call_request)
            unpublish_response = self.my_msg_handler.send_and_wait(call_request_msg, the_call_response_ref.UNPUBLISHOBJECTCLASSRESPONSE_FIELD_NUMBER, 3)
            
            if unpublish_response is None:
                log_error("ERROR: Received None response for unpublish object class")
                return False
                
            log_incoming("Object class unpublished successfully.")
            return True
            
        except Exception as e:
            log_error(f"Exception during unpublish_object_class: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            raise e

    def unpublish_interaction_class(self, class_handle: InteractionClassHandle)-> bool:
        """
            Description:
                Withdraw publication of an interaction class.
            Inputs:
                self: rtiAmbassadorFedPro instance.
                class_handle (InteractionClassHandle): Interaction class handle to unpublish.
            Outputs:
                True on success; False on None response.
            Exceptions:
                Raises RTIinternalError if not connected; propagates on unexpected exception.
        """
        if not self.my_is_connection_ok:
            raise RtiException.RTIinternalError("RTI Ambassador is not connected")
        
        log_outgoing(f"DtRtiAmbassadorFedPro::unpublish_interaction_class")
        
        try:
            call_request = RTIambassador_pb2.CallRequest()
            unpublish_request = call_request.unpublishInteractionClassRequest
            unpublish_request.interactionClass.data = class_handle.data
            
            call_request_msg = CallRequestMessage(call_request)
            unpublish_response = self.my_msg_handler.send_and_wait(call_request_msg, the_call_response_ref.UNPUBLISHINTERACTIONCLASSRESPONSE_FIELD_NUMBER, 3)
            
            if unpublish_response is None:
                log_error("ERROR: Received None response for unpublish interaction class")
                return False
                
            log_incoming("Interaction class unpublished successfully.")
            return True
            
        except Exception as e:
            log_error(f"Exception during unpublish_interaction_class: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            raise e

    def unsubscribe_object_class(self, class_handle: ObjectClassHandle)-> bool:
        """
            Description:
                Remove subscription to a previously subscribed object class.
            Inputs:
                self: rtiAmbassadorFedPro instance.
                class_handle (ObjectClassHandle): Object class to unsubscribe from.
            Outputs:
                True on success; False if None response.
            Exceptions:
                Raises RTIinternalError if not connected; propagates unexpected exceptions.
        """
        if not self.my_is_connection_ok:
            raise RtiException.RTIinternalError("RTI Ambassador is not connected")
        
        log_outgoing(f"DtRtiAmbassadorFedPro::unsubscribe_object_class")
        
        try:
            call_request = RTIambassador_pb2.CallRequest()
            unsubscribe_request = call_request.unsubscribeObjectClassRequest
            unsubscribe_request.objectClass.data = class_handle.data
            
            call_request_msg = CallRequestMessage(call_request)
            unsubscribe_response = self.my_msg_handler.send_and_wait(call_request_msg, the_call_response_ref.UNSUBSCRIBEOBJECTCLASSRESPONSE_FIELD_NUMBER, 3)
            if unsubscribe_response is None:
                log_error("ERROR: Received None response for unsubscribe object class")
                return False
                
            log_incoming("Object class unsubscribed successfully.")
            return True
            
        except Exception as e:
            log_error(f"Exception during unsubscribe_object_class: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            raise e

    def unsubscribe_interaction_class(self, class_handle: InteractionClassHandle)-> bool:
        """
            Description:
                Remove subscription for an interaction class.
            Inputs:
                self: rtiAmbassadorFedPro instance.
                class_handle (InteractionClassHandle): Interaction class handle.
            Outputs:
                True on success; False if None response.
            Exceptions:
                Raises RTIinternalError if not connected; returns False on caught exception.
        """
        if not self.my_is_connection_ok:
            raise RtiException.RTIinternalError("RTI Ambassador is not connected")
        
        log_outgoing(f"DtRtiAmbassadorFedPro::unsubscribe_interaction_class")
        
        try:
            call_request = RTIambassador_pb2.CallRequest()
            unsubscribe_request = call_request.unsubscribeInteractionClassRequest
            unsubscribe_request.interactionClass.data = class_handle.data
            
            call_request_msg = CallRequestMessage(call_request)
            unsubscribe_response = self.my_msg_handler.send_and_wait(call_request_msg, the_call_response_ref.UNSUBSCRIBEINTERACTIONCLASSRESPONSE_FIELD_NUMBER, 3)
            
            if unsubscribe_response is None:
                log_error("ERROR: Received None response for unsubscribe interaction class")
                return False
                
            log_incoming("Interaction class unsubscribed successfully.")
            return True
            
        except Exception as e:
            log_error(f"Exception during unsubscribe_interaction_class: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            return False

    def send_interaction(self, interaction_class_handle: InteractionClassHandle, parameter_values: dict[ParameterHandle, bytes], user_supplied_tag: bytes = b"")-> bool:
        """
            Description:
                Send an interaction with parameter values and optional user-supplied tag.
            Inputs:
                self: rtiAmbassadorFedPro instance.
                interaction_class_handle (InteractionClassHandle): Interaction class to send.
                parameter_values (dict[ParameterHandle, bytes]): Mapping of parameter handles to raw values.
                user_supplied_tag (bytes, optional): Optional annotation payload.
            Outputs:
                True on success; False on failure or None response.
            Exceptions:
                Raises RTIinternalError if not connected; returns False on processing exception.
        """
        if not self.my_is_connection_ok:
            raise RtiException.RTIinternalError("RTI Ambassador is not connected")
        
        log_outgoing(f"DtRtiAmbassadorFedPro::send_interaction")
        log_outgoing(f"parameterValues count: {len(parameter_values)}")
        log_outgoing(f"userSuppliedTag size: {len(user_supplied_tag)}")
        
        try:
            call_request = RTIambassador_pb2.CallRequest()
            send_request = call_request.sendInteractionRequest
            send_request.interactionClass.data = interaction_class_handle.data
            if user_supplied_tag:
                send_request.userSuppliedTag = user_supplied_tag

            
            # Add parameter handle-value pairs
            for param_handle, param_value in parameter_values.items():
                handle_value = send_request.parameterValues.parameterHandleValue.add()
                
                handle_value.parameterHandle.data = param_handle.data
                handle_value.value = param_value
            
            call_request_msg = CallRequestMessage(call_request)
            send_response = self.my_msg_handler.send_and_wait(call_request_msg, the_call_response_ref.SENDINTERACTIONRESPONSE_FIELD_NUMBER, 3)
            
            if send_response is None:
                log_error("ERROR: Received None response for send interaction")
                return False
                
            log_incoming("Interaction sent successfully.")
            return True
            
        except Exception as e:
            log_error(f"Exception during send_interaction: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            return False

    def delete_object_instance(self, object_instance_handle: ObjectInstanceHandle, user_supplied_tag: bytes = b"")-> bool:
        """
            Description:
                Delete a registered object instance, optionally attaching a user-supplied tag.
            Inputs:
                self: rtiAmbassadorFedPro instance.
                object_instance_handle (ObjectInstanceHandle): Handle identifying instance to delete.
                user_supplied_tag (bytes, default b""): Optional tag payload.
            Outputs:
                True on success; False on None response or exception.
            Exceptions:
                Raises RTIinternalError if not connected; returns False if exception occurs while sending.
        """
        if not self.my_is_connection_ok:
            raise RtiException.RTIinternalError("RTI Ambassador is not connected")
        
        log_outgoing(f"DtRtiAmbassadorFedPro::delete_object_instance")
        log_outgoing(f"userSuppliedTag size: {len(user_supplied_tag)}")
        
        try:
            call_request = RTIambassador_pb2.CallRequest()
            delete_request = call_request.deleteObjectInstanceRequest
            
            delete_request.objectInstance.data = object_instance_handle.data
            if user_supplied_tag:
                delete_request.userSuppliedTag = user_supplied_tag
            
            call_request_msg = CallRequestMessage(call_request)
            delete_response = self.my_msg_handler.send_and_wait(call_request_msg, the_call_response_ref.DELETEOBJECTINSTANCERESPONSE_FIELD_NUMBER, 3)
            
            if delete_response is None:
                log_error("ERROR: Received None response for delete object instance")
                return False
                
            log_incoming("Object instance deleted successfully.")
            return True
            
        except Exception as e:
            log_error(f"Exception during delete_object_instance: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            return False

    def update_attribute_values(self, object_instance_handle: ObjectInstanceHandle, attribute_values: dict[AttributeHandle, bytes], user_supplied_tag: bytes=b""):
        """
            Description:
                Update a set of attributes for a given object instance; sends update attribute values request.
            Inputs:
                self: rtiAmbassadorFedPro instance.
                object_instance_handle (ObjectInstanceHandle): Target instance handle.
                attribute_values (dict[AttributeHandle, bytes]): Attribute handle to new raw value mapping.
                user_supplied_tag (bytes, optional): Tag to attach; may be empty.
            Outputs:
                None; logs success. Raises on failure.
            Exceptions:
                Raises RTIinternalError for empty attribute set or failed update (exception or no response).
        """
        log_outgoing(f"\nDtRtiAmbassadorFedPro::update_attribute_values")
        log_outgoing(f"objectInstanceHandle: {object_instance_handle}")
        log_outgoing(f"attributeValues count: {len(attribute_values)}")
        if user_supplied_tag is not None:
            log_outgoing(f"userSuppliedTag size: {len(user_supplied_tag)}")
        log_outgoing("Attribute Values:")
        for attr_handle, attr_value in attribute_values.items():
            log_outgoing(f"  Attribute Handle: {attr_handle}, Value: {attr_value}")
        log_outgoing(attribute_values)
        
        if not attribute_values:
            log_warning("WARNING: No attribute values to update")
            raise RtiException.RTIinternalError("No attribute values provided for update")
        
        call_request = RTIambassador_pb2.CallRequest()
        update_request = call_request.updateAttributeValuesRequest
        
        # Set the object instance handle - handle both bytes and ObjectInstanceHandle objects
        an_object_instance_handle = datatypes_pb2.ObjectInstanceHandle()
        update_request.objectInstance.data = object_instance_handle.data
        
        # Set the user supplied tag
        if user_supplied_tag is not None and user_supplied_tag:
            update_request.userSuppliedTag = user_supplied_tag
        
        # Add attribute handle-value pairs
        for attr_handle, attr_value in attribute_values.items():
            handle_value = update_request.attributeValues.attributeHandleValue.add()
            
            an_attribute_handle = datatypes_pb2.AttributeHandle()
            handle_value.attributeHandle.data = attr_handle.data
            handle_value.value = attr_value
        # Send the request and wait for response
        call_request_msg = CallRequestMessage(call_request)
        
        if not self.my_msg_handler.send_and_wait(call_request_msg, the_call_response_ref.UPDATEATTRIBUTEVALUESRESPONSE_FIELD_NUMBER, 5):
            log_warning(self.my_msg_handler.my_fedPro_response)
            if self.my_msg_handler.my_poll_result == -1:
                log_error("ERROR: Failed to update attribute values, exception received")
                raise RtiException.RTIinternalError("Failed to update attribute values, exception received")
            else:
                log_error("ERROR: Failed to update attribute values, Unexpected or No responses received")
                raise RtiException.RTIinternalError("Failed to update attribute values due to missing/invalid response")
        else:
            log_incoming("Attribute values updated successfully.")

    def evoke_callback(self, max_time: float = 3.0):
        """
            Description:
                Evoke (process) pending callbacks for a limited duration by temporarily disabling queueing.
            Inputs:
                self: rtiAmbassadorFedPro instance.
                max_time (float, default 3.0): Maximum seconds to spend attempting callback processing.
            Outputs:
                Returns number of processed messages (or Falsey) from read_and_process; 0 indicates none processed.
            Exceptions:
                None raised; early returns False if not connected.
        """
        result = False
        if not self.my_is_connection_ok:
            return result

        if self.my_msg_handler.my_enable_callback_requests:
            self.my_msg_handler.my_queue_callback_requests = False
            #Read and Process will go here, make sure that RnP returns bool
            result = self.my_msg_handler.read_and_process(0.0, max_time)
            # if result == 0:
            #    log_info("No Callbacks Evoked")
            self.my_msg_handler.my_queue_callback_requests = True

        return result

# ===================================================================