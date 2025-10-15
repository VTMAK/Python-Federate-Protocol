"""
    Python Federate Protocol © 2025 by MAK Technologies is licensed under CC BY-ND 4.0.
    To view a copy of this license, visit https://creativecommons.org/licenses/by-nd/4.0/
"""
import sys
import os
import time
import math
import struct
from typing import Dict
from libsrc.rtiUtil.logger import *
from examples.hla_bounce.ballData import BallMap, Ball
from examples.hla_bounce.regionData import DdmRegionMap
from libsrc.fedProWrapper.rtiAmbassadorFedPro import Configuration
from libsrc.fedPro.callResponseMessage import CallResponseMessage
from libsrc.fedProWrapper.rtiAmbassadorFedPro import RtiAmbassadorFedPro
from HLA1516_2025.RTI import rtiConfiguration, exception, federateData
from libsrc.rtiUtil import exception
from examples.hla_bounce.hlaBounceFederateAmbassador import HlaBounceFederateAmbassador
from HLA1516_2025.RTI.handles import AttributeHandle, ObjectClassHandle, ObjectInstanceHandle

class BallController():
    """HLA Bounce Ball Controller - manages ball objects via HLA."""
    
    def __init__(self, ball_data: BallMap, region_data: DdmRegionMap):
        """
            Construct a BallController federate with provided ball and region data containers.

            Description:
                Initializes configuration, ambassadors, state containers, and handle placeholders.
            Args:
                ball_data (BallMap): Collection managing Ball objects (local and remote).
                region_data (DdmRegionMap): Region data manager (Ddm / spatial filtering support).
            Exceptions:
                None (assumes provided maps are valid objects).
        """

        # Create configuration for bounce federate
        self.my_configuration = Configuration()
        self.my_configuration.federation_name = "MakHlaBounce"
        self.my_configuration.federate_type = "BallFederate"
        self.my_configuration.federate_name = f"BallFederate_{os.getpid()}"
        # Use the corrected FOM file
        self.my_configuration.fom_modules.append("gui\\MakHlaBounce1516_2025.xml")

        self.my_rti_configuration = rtiConfiguration.RtiConfiguration()

        # Initialize Ambassadors
        self.my_data = federateData.FederateData()
        self.my_rti_ambassador : RtiAmbassadorFedPro = RtiAmbassadorFedPro()
        self.my_federate_ambassador : HlaBounceFederateAmbassador = HlaBounceFederateAmbassador(self, self.my_data)
        
        # Store references to data structures
        self.ball_data = ball_data
        self.region_data = region_data
        
        # Ball-specific HLA handles  
        self.ball_class_handle : ObjectClassHandle
        self.direction_handle : AttributeHandle
        self.speed_handle : AttributeHandle
        self.y_location_handle : AttributeHandle
        self.x_location_handle : AttributeHandle
        self.color_handle : AttributeHandle
        self.size_handle : AttributeHandle
        
        # Simulation parameters
        self.world_width : int = 500
        self.world_height : int = 500
        self.ball_radius : float = 5.0
        self.simulation_running = False
        self.last_update_time = time.time()
        self.list_refresh_needed = False
        # Map object instance handle bytes->ball_id
        self._inst_to_ball = {}
        self.my_object_instance_Name_Handles : dict[str, ObjectInstanceHandle] = {}
        self.my_object_instance_Handle_Values : dict[ObjectInstanceHandle, tuple[ObjectClassHandle, dict[AttributeHandle, bytes]]] = {}


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
                
        except exception.FedProSocketError as e:
            log_error("ERROR: Socket connection failed: " + str(type(e)))
            log_error(e.what())
            return False
        except exception.RTIinternalError as e:
            log_error("ERROR: Internal error during connection: " + str(type(e)))
            log_error(e.what())
            lastCheck = self.my_rti_ambassador.evoke_callback(3)
            if lastCheck is CallResponseMessage:
                log_warning("WARNING: Last check result: " + str(lastCheck))
        self.my_rti_ambassador.evoke_callback()
        log_info("Connected to RTI successfully")
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
            self.my_rti_ambassador.create_fed_ex(self.my_configuration.federation_name, self.my_configuration.fom_modules)
            create_success = True
        except Exception as e:
            log_error("ERROR: Federation Execution creation failed: " + str(e))
        self.my_rti_ambassador.evoke_callback()
        return create_success

    def join(self)-> bool:
        """
            Join the federation execution using configured parameters.

            Returns:
                bool: True if join succeeds; False otherwise.
        """
        if self.my_rti_ambassador is None:
            return False
        joined = False
        max_attempts = 3
        attempts = 0

        while (not joined) and (attempts < max_attempts):
            try:
                self.my_rti_ambassador.join_fed_ex(self.my_configuration.federate_name, self.my_configuration.federate_type, self.my_configuration.federation_name, self.my_configuration.fom_modules)
                joined = True
                # maybe get the transportation type handle
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

    def initialize_hla(self) -> bool:
        """
            Establish network connectivity, create/join federation, resolve required ball class/attribute handles.

            Returns:
                bool: True on success, False on any failure.
            Exceptions:
                Catches generic Exceptions, logs to stdout, returns False.
        """
        try:
            # Connect to RTI
            if not self.connect():
                print("ERROR: Failed to connect to RTI")
                return False
            
            # Create or join federation
            self.create_fed_ex()  # Don't fail if federation already exists
            
            if not self.join():
                print("ERROR: Failed to join federation")
                return False

            # Get ball object class handles
            if not self.get_ball_handles():
                print("ERROR: Failed to get ball object handles")
                return False

            print("HLA initialization complete")
            return True

        except Exception as e:
            print(f"ERROR: HLA initialization failed: {e}")
            return False

    def pump_hla(self):
        """
            Invoke a short callback processing slice to keep RTI events flowing.

            Side Effects:
                Processes queued callbacks via underlying ambassador.
            Exceptions:
                Suppresses any Exception (non-fatal UI loop support).
        """
        try:
            # Evoke callbacks briefly; underlying code queues/dispatches
            self.my_rti_ambassador.evoke_callback(0.05)
        except Exception as e:
            pass

    def get_ball_handles(self) -> bool:
        """
            Acquire and cache object class and attribute handles for the Ball HLA class.

            Returns:
                bool: True if all required handles resolved; False otherwise.
            Exceptions:
                Broad Exception caught, prints error, returns False.
        """
        try:
            # Get object class handle (assuming a Ball class exists in FOM)
            self.ball_class_handle : ObjectClassHandle 
            if self.my_rti_ambassador.my_obj_name_handles is {} or "Ball" not in self.my_rti_ambassador.my_obj_name_handles:
                self.ball_class_handle = self.my_rti_ambassador.get_object_class_handle("Ball")
                self.my_data.my_attr_name_handles[self.ball_class_handle] = {}
            else:
                self.ball_class_handle = self.my_rti_ambassador.my_obj_name_handles["Ball"]

            if self.my_data.my_attr_name_handles[self.ball_class_handle] == {} or self.ball_class_handle not in self.my_data.my_attr_name_handles[self.ball_class_handle]:
                # Get attribute handles using the correct names from the FOM
                self.my_data.my_attr_name_handles[self.ball_class_handle]["Color"] = self.my_rti_ambassador.get_attribute_handle(self.ball_class_handle, "Color")
                self.my_data.my_attr_name_handles[self.ball_class_handle]["Size"] = self.my_rti_ambassador.get_attribute_handle(self.ball_class_handle, "Size")
                self.my_data.my_attr_name_handles[self.ball_class_handle]["XLocation"] = self.my_rti_ambassador.get_attribute_handle(self.ball_class_handle, "XLocation")
                self.my_data.my_attr_name_handles[self.ball_class_handle]["YLocation"] = self.my_rti_ambassador.get_attribute_handle(self.ball_class_handle, "YLocation")
                self.my_data.my_attr_name_handles[self.ball_class_handle]["Speed"] = self.my_rti_ambassador.get_attribute_handle(self.ball_class_handle, "Speed")
                self.my_data.my_attr_name_handles[self.ball_class_handle]["Direction"] = self.my_rti_ambassador.get_attribute_handle(self.ball_class_handle, "Direction")

            self.color_handle = self.my_data.my_attr_name_handles[self.ball_class_handle]["Color"]
            self.size_handle = self.my_data.my_attr_name_handles[self.ball_class_handle]["Size"]
            self.x_location_handle = self.my_data.my_attr_name_handles[self.ball_class_handle]["XLocation"]
            self.y_location_handle = self.my_data.my_attr_name_handles[self.ball_class_handle]["YLocation"]
            self.speed_handle = self.my_data.my_attr_name_handles[self.ball_class_handle]["Speed"]
            self.direction_handle = self.my_data.my_attr_name_handles[self.ball_class_handle]["Direction"]

            print("Successfully retrieved ball attribute handles")
            return True
            
        except Exception as e:
            print(f"ERROR: Failed to get ball handles: {e}")
            return False
            
    def publish_ball(self) -> bool:
        """
            Publish all Ball attribute handles so local updates can be sent to RTI.

            Returns:
                bool: True if publication completes; False on failure.
            Exceptions:
                Catches generic Exception; logs and returns False.
        """
        try:
            # Create attribute handle set for publication
            ball_attributes: Dict[str, AttributeHandle] = {
                "Direction": self.direction_handle,
                "Speed": self.speed_handle,
                "YLocation": self.y_location_handle,
                "XLocation": self.x_location_handle,
                "Color": self.color_handle,
                "Size": self.size_handle
            }
            
            # Publish ball object class
            if self.ball_class_handle is None:
                raise RuntimeError("Ball class handle not resolved")
            self.my_rti_ambassador.publish_object_class_attributes(self.ball_class_handle, list(ball_attributes.values()))  # type: ignore[arg-type]
                
            print("Successfully published ball attributes")
            return True
            
        except Exception as e:
            print(f"ERROR: Failed to setup ball publication: {e}")
            return False
            
    def subscribe_ball(self) -> bool:
        """
            Subscribe to remote Ball attribute updates for discovered or future instances.

            Returns:
                bool: True if subscription succeeds; False otherwise.
            Exceptions:
                Catches generic Exception; logs and returns False.
        """
        try:
            # Create attribute handle set for subscription
            ball_attributes: Dict[str, AttributeHandle] = {
                "Direction": self.direction_handle,
                "Speed": self.speed_handle,
                "YLocation": self.y_location_handle,
                "XLocation": self.x_location_handle,
                "Color": self.color_handle,
                "Size": self.size_handle
            }
            
            # Subscribe to ball object class
            if self.ball_class_handle is None:
                raise RuntimeError("Ball class handle not resolved")
            self.my_rti_ambassador.subscribe_object_class_attributes(self.ball_class_handle, list(ball_attributes.values()))  # type: ignore[arg-type]
            
            print("Successfully subscribed to ball attributes")
            return True
            
        except Exception as e:
            print(f"ERROR: Failed to setup ball subscription: {e}")
            return False
            
    def create_local_ball(self, ball_id: str, x: int | None = None, y: int | None = None, dx: float = 4.0, dy: float = 4.0, scale: int = 10, color: int = 0) -> bool:
        """
            Instantiate and publish a new locally-owned Ball.

            Args:
                ball_id: Unique identifier / instance name for the ball.
                x: Initial X position (defaults to world_width/4 if None).
                y: Initial Y position (defaults to world_height/4 if None).
                dx: Initial horizontal velocity component.
                dy: Initial vertical velocity component.
                scale: Size attribute (encoded as short when sent).
                color: Color index encoded as single byte.
            Returns:
                bool: True on success; False on failure.
            Exceptions:
                Catches generic Exception, logs, returns False.
        """
        try:
            # Set default position if not provided
            if x is None:
                x = int(self.world_width / 4)
            if y is None:
                y = int(self.world_height / 4)
                
            # Create ball object
            temp_ball = Ball(ball_id, x, y, dx, dy, scale, color)
            # Register object instance with RTI
            self.my_rti_ambassador.reserve_object_instance_name(ball_id)
            if self.ball_class_handle is None:
                raise RuntimeError("Ball class handle not resolved")
            self.my_rti_ambassador.evoke_callback()
            object_handle = self.my_rti_ambassador.register_object_instance(self.ball_class_handle, ball_id)
            self.my_object_instance_Handle_Values[object_handle] = (self.ball_class_handle, {})
                
            if object_handle:
                temp_ball.object_handle = object_handle
                self.ball_data.add_ball(temp_ball, is_local=True)
                
                # Send initial attribute update
                self.update_ball_attributes(temp_ball)
                
                print(f"Created local ball: {temp_ball}")
                return True
            else:
                print(f"ERROR: Failed to register ball object instance: {ball_id}")
                return False
                
        except Exception as e:
            print(f"ERROR: Failed to create local ball {ball_id}: {e}")
            return False
            
    def update_ball_attributes(self, ball: Ball):
        """
            Package Ball state into attribute value map and send update to RTI (with throttling).

            Args:
                ball (Ball): Ball whose state should be published.
            Side Effects:
                Updates ball.last_attr_send_time and sends attribute update via RTI ambassador.
            Exceptions:
                Broad Exception caught; logs error without raising.
        """
        try:
            if not ball.ball_id != "":
                return
            # Throttle attribute updates to at most 10 Hz per ball
            now = time.time()       
            if (now - ball.last_attr_send_time) < 0.1:  # 100 ms minimum interval
                return

            # Create attribute handle-value map
            attribute_values = {}
            print(f"Updating attributes for ball {ball.ball_id}:\n pos=({ball.x},{ball.y})\n vel=({ball.dx},{ball.dy})\n color={ball.color}\n size={ball.scale}")
            attribute_values[self.color_handle] = struct.pack('>B', ball.color)
            attribute_values[self.size_handle] = struct.pack('>h', ball.scale)
            attribute_values[self.x_location_handle] = struct.pack('>h', int(ball.x - 250))
            attribute_values[self.y_location_handle] = struct.pack('>h', int(ball.y - 250))
            # The direction attribute is measured in radians, perform some calculations to
            # ball's x, y, dx, dy values to determine direction and speed
            speed = math.sqrt(float(ball.dx) * float(ball.dx) + float(ball.dy) * float(ball.dy))
            print(f"Calculated speed: {speed}")
            attribute_values[self.speed_handle] = struct.pack('>h', int(speed))
            direction_radians = math.atan2(float(ball.dy), float(ball.dx))
            print(f"Calculated direction (radians): {direction_radians}")
            attribute_values[self.direction_handle] = struct.pack('>d', direction_radians)
            
            # Update attributes
            self.my_rti_ambassador.update_attribute_values(ball.object_handle, attribute_values, b"")
            ball.last_attr_send_time = now

        except Exception as e:
            print(f"ERROR: Failed to update ball attributes for {ball.ball_id}: {e}")

    def update_simulation(self, dt: float):
        """
            Advance simulation by dt seconds: update positions, handle bounces, emit updates for owned balls.

            Args:
                dt (float): Elapsed simulation timestep in seconds.
            Exceptions:
                None explicitly; relies on Ball methods assumed safe.
        """
        for ball in self.ball_data.balls.values():
            # Update position
            ball.update_position(dt)
            
            # Check for bounces off walls
            if ball.x <= self.ball_radius / 100 or ball.x >= (self.world_width - self.ball_radius):
                ball.bounce_x()
                ball.x = int(max(self.ball_radius / 100, min(float(self.world_width) - (self.ball_radius / 100), float(ball.x))))
                
            if ball.y <= self.ball_radius / 100 or ball.y >= (self.world_height - self.ball_radius):
                ball.bounce_y()
                ball.y = int(max(self.ball_radius / 100, min(float(self.world_height) - (self.ball_radius / 100), float(ball.y))))
            # Send attribute update
            if ball.is_owned:
                print("Updating local ball")
                self.update_ball_attributes(ball)

    def cleanup(self):
        """
            Delete local object instances, resign, and attempt federation destruction.

            Side Effects:
                Deletes objects, resigns, may destroy federation if possible.
            Exceptions:
                Swallows most exceptions, logs warnings.
        """
        try:
            # Delete all local object instances
            for ball in self.ball_data.local_balls.values():
                if ball.object_handle:
                    self.my_rti_ambassador.delete_object_instance(ball.object_handle)  # type: ignore[arg-type]
                        
            # Resign from federation
            self.my_rti_ambassador.resign_federation_execution("DELETE_OBJECTS")
            
            # Destroy federation (may fail if other federates still joined)
            try:
                self.my_rti_ambassador.destroy_federation_execution(self.my_configuration.federation_name)
            except:
                pass  # Ignore if other federates still exist
                
        except Exception as e:
            print(f"WARNING: Error during cleanup: {e}")

    # ---------- Local management helpers ----------
    def remove_local_ball(self, ball_id: str) -> bool:
        """
            Delete a locally owned ball: remove from RTI (if possible) and internal collection.

            Args:
                ball_id (str): Identifier of the local ball to remove.
            Returns:
                bool: True if removal attempted on existing local ball; False otherwise.
            Exceptions:
                Suppresses exceptions during RTI deletion; broad outer exception returns False.
        """

        ball = self.ball_data.get_ball(ball_id)
        if not ball or not ball.is_owned:
            return False
        try:
            if ball.object_handle:
                try:
                    self.my_rti_ambassador.delete_object_instance(ball.object_handle)
                except Exception:
                    pass
            self.ball_data.remove_ball(ball_id)
            return True
        except Exception:
            return False
            
    def __del__(self):
        """
            Ensure cleanup invoked during object finalization (ignores exceptions).
        """
        self.cleanup()
