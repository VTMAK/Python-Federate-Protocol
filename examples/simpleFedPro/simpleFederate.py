"""
    Python Federate Protocol © 2025 by MAK Technologies is licensed under CC BY-ND 4.0.
    To view a copy of this license, visit https://creativecommons.org/licenses/by-nd/4.0/
"""
import os
import time
from libsrc.rtiUtil.logger import *
import HLA1516_2025.RTI.handles as handles
import HLA1516_2025.RTI.exception as RtiException
from HLA1516_2025.RTI.federateData import FederateData
from HLA1516_2025.RTI.rtiConfiguration import RtiConfiguration
from libsrc.fedPro.callResponseMessage import CallResponseMessage
from examples.simpleFedPro.simpleFederateAmbassador import SimpleFederateAmbassador
from libsrc.fedProWrapper.rtiAmbassadorFedPro import RtiAmbassadorFedPro, Configuration


class simpleFederate():
    """
        Simple Federate Implementation python FedPro classes/RTI API.
    """
    def __init__(self, configuration: Configuration):
        self.my_data = FederateData()
        self.my_configuration = configuration
        self.my_privilege_to_delete_handle = ""
        self.my_federate_handle : handles.FederateHandle
        self.my_fom_modules = configuration.fom_modules
        self.my_rti_ambassador = RtiAmbassadorFedPro()
        self.my_rti_configuration = RtiConfiguration()
        self.my_callback_model = configuration.callback_model
        self.my_object_instance_Name_Handles : dict[str ,handles.ObjectInstanceHandle] = {}
        self.my_federate_ambassador : SimpleFederateAmbassador = SimpleFederateAmbassador()
        self.my_object_instance_Handle_Values : dict[handles.ObjectInstanceHandle, tuple[handles.ObjectClassHandle, dict[handles.AttributeHandle, bytes]]] = {}

    def connect(self)-> bool:
        """
            Establish connection to RTI via underlying ambassador.
        """
        if self.my_rti_ambassador is None:
            return False

        try:
            self.my_rti_ambassador.connect(self.my_federate_ambassador, self.my_rti_configuration)
            if not self.my_rti_ambassador.my_is_connection_ok:
                log_error("ERROR: RTI connection is not OK after connect")
                return False
        except RtiException.RTIinternalError as e:
            log_error("ERROR: Internal error during connection: " + str(type(e)))
            log_error(e.what())
            lastCheck = self.my_rti_ambassador.evoke_callback(3)
            if lastCheck is CallResponseMessage:
                log_warning("WARNING: Last check result: " + str(lastCheck))
        self.my_rti_ambassador.evoke_callback()
        log_info("Connected to RTI successfully")
        return True

    def list_federation_executions(self) -> bool:
        """
            List existing federation executions via RTI.
    
            Returns:
                bool: True if listing succeeds; False on failure.
        """
        if self.my_rti_ambassador is None:
            return False
        try:
            self.my_rti_ambassador.list_federation_executions()
            self.my_rti_ambassador.evoke_callback(3)
        except Exception as e:
            log_error("ERROR: Listing federation executions failed: " + str(e))
            return False
        return True

    def create_fed_ex(self)-> bool:
        """
            Create federation execution if it does not already exist.
    
            Returns:
                bool: True if creation succeeds or federation already exists; False on failure.
        """
        create_success : bool = False
        if (self.my_rti_ambassador is None):
            return create_success
        
        try:
            self.my_rti_ambassador.create_fed_ex(self.my_configuration.federation_name, self.my_fom_modules)
            create_success = True
        except Exception as e:
            log_error("ERROR: Federation Execution creation failed: " + str(e))
        self.my_rti_ambassador.evoke_callback()
        return create_success

    def join(self)-> bool:
        """
            Attempt to join the target federation execution with retry logic.

            Behavior:
                Repeatedly invokes join_fed_ex up to max_attempts until successful or exhausted.
            Returns:
                bool: True if joined successfully; False after all retries fail.
            Side Effects:
                Logs status; sleeps briefly before returning on failure.
        """
        
        if self.my_rti_ambassador is None:
            return False
        joined = False
        max_attempts = 10
        attempts = 0

        while (not joined) and (attempts < max_attempts):
            try:
                self.my_rti_ambassador.join_fed_ex(self.my_configuration.federate_name, self.my_configuration.federate_type, self.my_configuration.federation_name, self.my_fom_modules)
                joined = True
            except Exception as e:
                attempts += 1
                log_warning(f"WARNING: Join attempt {attempts} failed: {e}")
                self.my_rti_ambassador.evoke_callback(3)
        if (joined):
            log_info("Successfully joined federation execution")
        else:
            log_error(f"Failed to join federation execution after {attempts} attempts")
            time.sleep(1)
        return joined

    def publish_subscribe_and_register_object(self)-> bool:
        """
            Publish/subscribe required object classes and register a single local object instance.

                - Acquire object class handles.
                - Acquire attribute handles for base, ground, and air variants.
                - Subscribe to ground & air attributes.
                - Publish air object class attributes.
                - Reserve name and register object instance.
            Returns:
                bool: True on full success; False on any failure.
            Side Effects:
                Populates my_attr_name_handles, my_attr_handle_names, and registration maps.
        """
        try:
            object_class_name = "BaseEntity.Aircraft"
            base_entity_class_name = "BaseEntity"
            ground_vehicle_class_name = "BaseEntity.GroundVehicle"
            air_vehicle_class_name = "BaseEntity.Aircraft"
            object_class_handle = self.my_rti_ambassador.get_object_class_handle(object_class_name)
            base_object_class_handle = self.my_rti_ambassador.get_object_class_handle(base_entity_class_name)
            ground_object_class_handle = self.my_rti_ambassador.get_object_class_handle(ground_vehicle_class_name)
            air_object_class_handle = self.my_rti_ambassador.get_object_class_handle(air_vehicle_class_name)
            self.my_data.my_attr_name_handles[object_class_handle] = {}
            self.my_data.my_attr_name_handles[ground_object_class_handle] = {}
            self.my_data.my_attr_name_handles[air_object_class_handle] = {}
            self.my_data.my_attr_handle_names[ground_object_class_handle] = {}
            self.my_data.my_attr_handle_names[air_object_class_handle] = {}
        except Exception as e:
            log_error(f"Failed to get object class handle for: {e}")
            return False

        base_entity_names = ["HLAprivilegeToDeleteObject", "WorldLocation", "Orientation", "VelocityVector", "AccelerationVector", "InfraredSignature", "DamageState"]
        for i in base_entity_names:
            try:
                self.my_data.my_attr_name_handles[object_class_handle][i] = self.my_rti_ambassador.get_attribute_handle(object_class_handle, i)
            except Exception as e:
                log_error(f"Failed to get attribute handle for {i} in BaseEntity: {e}")

        ground_names = ["HeadLightsOn", "BrakeLightsOn"]
        for i in ground_names:
            try:
                self.my_data.my_attr_name_handles[ground_object_class_handle][i] = self.my_rti_ambassador.get_attribute_handle(ground_object_class_handle, i)
            except Exception as e:
                log_error(f"Failed to get attribute handle for {i} in BaseEntity: {e}")

        air_names = ["NavigationLightsOn", "LandingLightsOn"]
        for i in air_names:
            try:
                self.my_data.my_attr_name_handles[air_object_class_handle][i] = self.my_rti_ambassador.get_attribute_handle(air_object_class_handle, i)
            except Exception as e:
                log_error(f"Failed to get attribute handle for {i} in BaseEntity: {e}")
        for attr_name, attr_handle in self.my_data.my_attr_name_handles[object_class_handle].items():
            self.my_data.my_attr_name_handles[ground_object_class_handle][attr_name] = attr_handle
            self.my_data.my_attr_name_handles[air_object_class_handle][attr_name] = attr_handle
            self.my_data.my_attr_handle_names[ground_object_class_handle][attr_handle] = attr_name
            self.my_data.my_attr_handle_names[air_object_class_handle][attr_handle] = attr_name
        
        # SUBSCRIBE
        try:
            self.my_rti_ambassador.subscribe_object_class_attributes(ground_object_class_handle, set(self.my_data.my_attr_name_handles[ground_object_class_handle].values()))
            self.my_rti_ambassador.subscribe_object_class_attributes(air_object_class_handle, set(self.my_data.my_attr_name_handles[air_object_class_handle].values()))
        
        except Exception as e:
            log_error(f"ERROR: Failed to subscribe to object class attributes: {e}")
            return False
        
        #PUBLISH
        try:
            self.my_rti_ambassador.publish_object_class_attributes(air_object_class_handle, list(self.my_data.my_attr_name_handles[air_object_class_handle].values()))

        except Exception as e:
            log_error(f"Failed to publish object class attributes: {e}")
            return False
        
        self.my_rti_ambassador.evoke_callback(3)
        object_instance_name : str = self.my_configuration.federate_name + str(os.getpid() // 1000)
        
        # Check connection status before attempting reservation
        if not hasattr(self.my_rti_ambassador, 'my_is_connection_ok') or not self.my_rti_ambassador.my_is_connection_ok:
            log_error("ERROR: RTI connection is not OK before object instance reservation")
            return False
        
        #REGISTER
        try:
            self.my_rti_ambassador.reserve_object_instance_name(object_instance_name)

            self.my_rti_ambassador.evoke_callback(5.0)
            
        except Exception as e:
            log_error(f"Failed to reserve object instance: {e}")
            return False

        try:
            object_instance_handle : handles.ObjectInstanceHandle = self.my_rti_ambassador.register_object_instance(air_object_class_handle, object_instance_name)
            self.my_object_instance_Name_Handles[object_instance_name] = object_instance_handle
            self.my_object_instance_Handle_Values[object_instance_handle] = (air_object_class_handle, {})
            
            self.my_rti_ambassador.evoke_callback(4.0)
        except Exception as e:
            error_msg = str(e)
            log_error(f"Failed to register object instance: {error_msg}")
            
            if "ObjectClassNotPublished" in error_msg:
                log_error("ERROR: The object class has not been published!")
                log_error("Make sure to call publish_object_class_attributes() before register_object_instance()")
                log_error(f"Attempted to register with class handle: {air_object_class_handle}")
                log_error("Check that this handle matches one of the published classes")
            elif "InvalidHandle" in error_msg:
                log_error("ERROR: Invalid object class handle!")
                log_error(f"Handle used: {air_object_class_handle}")
                log_error("Make sure the handle is valid and from get_object_class_handle()")
            
            return False
        return True
    

    def publish_subscribe_interaction(self) -> bool:
        """
            Publish and subscribe to interaction class parameters for WeaponFire.

            Returns:
                bool: True if all handles resolved and pub/sub calls succeed; False otherwise.
            Side Effects:
                Populates interaction and parameter name/handle dictionaries.
        """
        try:
            # Get the interaction class handle
            interaction_class_name = "WeaponFire"
            interaction_class_handle = self.my_rti_ambassador.get_interaction_class_handle(interaction_class_name)
            
            self.my_rti_ambassador.my_interaction_handle_names[interaction_class_handle] = interaction_class_name
            self.my_rti_ambassador.my_interaction_name_handles[interaction_class_name] = interaction_class_handle
            
        except Exception as e:
            log_error(f"ERROR: Could not get interaction class handle for {interaction_class_name}: {e}")
            return False

        # Get parameter handles and construct the name-handle map
        parameter_names = [
            "EventIdentifier",
            "FireControlSolutionRange", 
            "FireMissionIndex",
            "FiringLocation",
            "FiringObjectIdentifier",
            "FuseType",
            "InitialVelocityVector",
            "MunitionObjectIdentifier", 
            "MunitionType",
            "QuantityFired",
            "RateOfFire",
            "TargetObjectIdentifier",
            "WarheadType"
        ]
        
        try:
            param_name = ""
            for param_name in parameter_names:
                param_handle = self.my_rti_ambassador.get_parameter_handle(interaction_class_handle, param_name)
                self.my_rti_ambassador.my_parameter_name_handles[interaction_class_handle][param_name] = param_handle
                
        except Exception as e:
            log_error(f"ERROR: Could not get parameter handle for {param_name}: {e}")
            return False
        
        # Subscribe
        try:
            # Subscribe to interaction class  
            self.my_rti_ambassador.subscribe_interaction_class(interaction_class_handle)
            self.my_rti_ambassador.evoke_callback(0.2)
            
        except Exception as e:
            log_error(f"ERROR: Could not publish/subscribe to interaction class: {e}")
            return False
        
        # Publish
        try:
            # Publish interaction class
            self.my_rti_ambassador.publish_interaction_class(interaction_class_handle)
            self.my_rti_ambassador.evoke_callback(0.2)
            
        except Exception as e:
            log_error(f"ERROR: Could not publish/subscribe to interaction class: {e}")
            return False

        log_info(f"Successfully published and subscribed to interaction class: {interaction_class_name} with handle: {interaction_class_handle}")
        return True

    def run_federate(self, run_time_seconds: float=60.0):
        """
            Main execution loop performing callbacks, periodic attribute & interaction updates.

            Args:
                run_time_seconds (float): Total wall-clock time to run the loop.
            Returns:
                bool: True when loop completes (or breaks) normally.
            Side Effects:
                Sends attribute and interaction updates; logs progress.
        """
        
        log_info(f"Starting federate execution for {run_time_seconds} seconds...")
        start_time = time.time()
        last_update_time = start_time
        update_interval = 5.0  # Update attributes every 5 seconds
        
        # Store the registered object handle for updates
        registered_object_handle = getattr(self, 'registered_object_instance_handle', None)
        
        while (time.time() - start_time) < run_time_seconds:
            try:
                current_time = time.time()
                elapsed_time = current_time - start_time
                
                # Process any pending callbacks
                self.my_rti_ambassador.evoke_callback(10.0)
                
                # Periodic status updates
                if int(elapsed_time) % 10 == 0:  # Every 10 seconds
                    pass
                
                # Periodic attribute updates
                if (current_time - last_update_time) >= update_interval:
                    for a, b in self.my_object_instance_Name_Handles.items():
                        attribute_updates = self.create_sample_attribute_updates(b)
                        if attribute_updates:
                            try:
                                self.my_rti_ambassador.update_attribute_values(b, attribute_updates)
                                log_info("Attribute updates sent successfully")
                            except Exception as e:
                                log_error("Failed to send attribute updates")
                                log_error(f"Exception: {e}")

                    try:
                        param_handle_values = self.create_sample_interaction_parameters()
                        self.my_rti_ambassador.send_interaction(param_handle_values[0], param_handle_values[1])
                        log_info("Attribute updates sent successfully")
                    except Exception as e:
                        log_error("Failed to send attribute updates")
                        log_error(f"Exception: {e}")
                    
                    last_update_time = current_time

                # Sleep briefly to avoid busy waiting
                time.sleep(0.1)
                
            except KeyboardInterrupt:
                log_error("\nFederate execution interrupted by user")
                break
            except Exception as e:
                log_error(f"Error during federate execution: {e}")
                break
        
        log_info("Federate execution completed")
        return True
    
    def create_sample_interaction_parameters(self)-> tuple[handles.InteractionClassHandle, dict[handles.ParameterHandle, bytes]]:
        """
            Create a sample parameter map for a single published interaction class.

            Returns:
                tuple: (InteractionClassHandle, dict[ParameterHandle, bytes]) on success.
            Raises:
                RTIinternalError: If no parameters are found / published.
            Side Effects:
                Logs errors or warnings if state not initialized.
        """
        try:
            # Get the published parameters we stored during registration
            if self.my_rti_ambassador.my_parameter_name_handles == {}:
                log_error("No Interaction Classes Published")
                raise Exception("No Interaction Classes Published")
            
            for value, handle in self.my_rti_ambassador.my_interaction_name_handles.items():
                if self.my_rti_ambassador.my_parameter_name_handles[handle].items() is not {}:
                    parameter_values : dict[handles.ParameterHandle, bytes] = {}
                    # Update some specific parameters with meaningful data
                    for param_name, param_handle in self.my_rti_ambassador.my_parameter_name_handles[handle].items():
                        parameter_values[param_handle] = param_name.encode('utf-8')
                    
                    return (handle, parameter_values)
            log_warning("No parameters found for interaction class")
            raise RtiException.RTIinternalError("No parameters found for interaction class")
            
        except Exception as e:
            log_error(f"Error creating interaction parameters: {e}")
            raise e
    
    def create_sample_attribute_updates(self, object_instance_handle: handles.ObjectInstanceHandle)-> dict[handles.AttributeHandle, bytes]:
        """
            Create/update a dictionary of attribute handle -> value bytes for a registered object.

            Args:
                object_instance_handle (ObjectInstanceHandle): The object whose attributes to populate/update.
            Returns:
                dict[AttributeHandle, bytes]: Mapping of attribute handles to encoded UTF-8 name values.
            Side Effects:
                Initializes attribute value map on first call; mutates stored handle-value structure.
        """
        try:
            current_time = time.time()
            # Get the published attributes we stored during registration
            if self.my_object_instance_Handle_Values is {}:
                log_error("No Object Instances Registered")
                raise Exception("No Object Instances Registered")
            
            if self.my_object_instance_Handle_Values[object_instance_handle][1] == {}:
                log_warning("Attribute initialization required")
                for a,b in self.my_data.my_attr_name_handles[self.my_object_instance_Handle_Values[object_instance_handle][0]].items():
                    self.my_object_instance_Handle_Values[object_instance_handle][1][b] = b""
                
            for attr_handle, attr_value in self.my_object_instance_Handle_Values[object_instance_handle][1].items():
                attr_name = self.my_data.my_attr_handle_names[self.my_object_instance_Handle_Values[object_instance_handle][0]][attr_handle]
                self.my_object_instance_Handle_Values[object_instance_handle][1][attr_handle] = attr_name.encode('utf-8')
            
            log_info(f"Created {len(self.my_object_instance_Handle_Values[object_instance_handle][1].items())} attribute updates")
            
            return self.my_object_instance_Handle_Values[object_instance_handle][1]
            
        except Exception as e:
            log_error(f"Error creating attribute updates: {e}")
            return {}

    def resign_and_destroy(self)-> bool:
        """
            Resign from federation and attempt to destroy it (placeholder implementation).

            Returns:
                bool: True if operations complete without raising.
            Side Effects:
                Logs resignation and destruction attempts.
        """
        try:
            if self.my_rti_ambassador is None:
                return True
                
            log_info("Resigning from federation execution...")
            self.my_rti_ambassador.resign_federation_execution("DELETE_OBJECTS")
            
            log_info("Attempting to destroy federation execution...")
            self.my_rti_ambassador.destroy_federation_execution(self.my_configuration.federation_name)
            
            log_info("Federation cleanup completed")
            return True
            
        except Exception as e:
            log_error(f"Error during resignation/destruction: {e}")
            return False
