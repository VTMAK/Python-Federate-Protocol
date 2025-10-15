"""
    Python Federate Protocol © 2025 by MAK Technologies is licensed under CC BY-ND 4.0.
    To view a copy of this license, visit https://creativecommons.org/licenses/by-nd/4.0/
"""
import time
from typing import Dict, Optional
from HLA1516_2025.RTI.handles import ObjectInstanceHandle

class Ball:
    """
        Represents a single ball in the simulation.
    """
    
    def __init__(self, ball_id: str, x: int = 0, y: int = 0, dx: float = 1.0, dy: float = 1.0, scale: int = 5, color: int = 1):
        """
            Initialize a Ball with identifiers, position, velocity, size, and color; timestamps for updates.

            Args:
                ball_id (str): Unique identifier.
                x (int): Initial X coordinate (default 0).
                y (int): Initial Y coordinate (default 0).
                dx (float): Initial velocity in X (default 1.0).
                dy (float): Initial velocity in Y (default 1.0).
                scale (int): Ball size scale factor (default 5).
                color (int): Color index (default 1).
            Notes:
                object_handle is set later upon registration.
        """
        self.ball_id = ball_id
        self.x : float = x
        self.y : float = y
        self.scale : int = scale  # size scale factor
        self.dx : float = dx  # velocity in x direction
        self.dy : float = dy  # velocity in y direction
        self.color = color
        self.last_update_time = time.time()
        self.last_attr_send_time = 0.0  # float seconds
        self.is_owned = False
        self.object_handle : ObjectInstanceHandle
        
    def update_position(self, dt: float):
        """
            Advance position using current velocity over a timestep.

            Args:
                dt (float): Time delta in seconds.
            Side Effects:
                Updates x, y and last_update_time.
        """
        self.x += float(self.dx * dt)
        self.y += float(self.dy * dt)
        self.last_update_time = time.time()
        
    def bounce_x(self):
        """
            Invert horizontal velocity to simulate collision with vertical boundary.
        """
        self.dx = -self.dx
        
    def bounce_y(self):
        """
            Invert vertical velocity to simulate collision with horizontal boundary.
        """
        self.dy = -self.dy
        
    def set_position(self, x: int, y: int):
        """
            Assign absolute position values and refresh update timestamp.

            Args:
                x (int): New X coordinate.
                y (int): New Y coordinate.
            Side Effects:
                Updates x, y, last_update_time.
        """
        self.x = x
        self.y = y
        self.last_update_time = time.time()
        
    def set_velocity(self, dx: float, dy: float):
        """
            Update both velocity components unconditionally.

            Args:
                dx (float): New horizontal velocity.
                dy (float): New vertical velocity.
        """
        self.dx = dx
        self.dy = dy
        
    def __str__(self):
        """
            Human-readable summary of ball state (id, position, velocity, color).
        """
        return f"Ball({self.ball_id}: pos=({self.x:.2f},{self.y:.2f}), vel=({self.dx:.2f},{self.dy:.2f}), color={self.color})"


class BallMap:
    """
        Manages a collection of balls in the simulation.
    """
    
    def __init__(self):
        """
            Initialize empty ball containers for all, local, and remote ball segregation.

            Side Effects:
                Sets up empty dicts for balls, local_balls, remote_balls.
        """
        self.balls: Dict[str, Ball] = {}
        self.local_balls: Dict[str, Ball] = {}  # Balls owned by this federate
        self.remote_balls: Dict[str, Ball] = {}  # Balls from other federates
        
    def add_ball(self, ball: Ball, is_local: bool = False):
        """
            Insert ball into global map; classify as local or remote and set ownership flag.

            Args:
                ball (Ball): Ball instance to add.
                is_local (bool): Ownership indicator (default False).
            Side Effects:
                Updates internal dictionaries; sets ball.is_owned.
        """
        self.balls[ball.ball_id] = ball
        if is_local:
            self.local_balls[ball.ball_id] = ball
            ball.is_owned = True
        else:
            self.remote_balls[ball.ball_id] = ball
            ball.is_owned = False
            
    def remove_ball(self, ball_id: str):
        """
            Delete ball entries (if present) from global, local, and remote maps.

            Args:
                ball_id (str): Identifier of ball to remove.
            Side Effects:
                Internal maps updated; silent if ID absent.
        """
        if ball_id in self.balls:
            del self.balls[ball_id]
        if ball_id in self.local_balls:
            del self.local_balls[ball_id]
        if ball_id in self.remote_balls:
            del self.remote_balls[ball_id]
            
    def get_ball(self, ball_id: str) -> Optional[Ball]:
        """
            Retrieve ball reference by ID from master collection.

            Args:
                ball_id (str): Identifier to lookup.
            Returns:
                Optional[Ball]: Ball instance if found; None otherwise.
        """
        return self.balls.get(ball_id)
            
    def clear(self):
        """
            Remove all ball entries from global, local, and remote collections.

            Side Effects:
                Empties internal dictionaries.
        """
        self.balls.clear()
        self.local_balls.clear()
        self.remote_balls.clear()
        
    def __len__(self):
        """
            Return total number of balls tracked.

            Returns:
                int: Count of entries in balls dict.
        """
        return len(self.balls)
        
    def __str__(self):
        """
            Human-readable summary including counts of total, local, and remote balls.
        """
        return f"BallMap: {len(self.balls)} balls ({len(self.local_balls)} local, {len(self.remote_balls)} remote)"
