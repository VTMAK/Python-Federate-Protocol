"""
    Python Federate Protocol © 2025 by MAK Technologies is licensed under CC BY-ND 4.0.
    To view a copy of this license, visit https://creativecommons.org/licenses/by-nd/4.0/
"""
from __future__ import annotations

# Handle type definitions for HLA FedPro protocol.

class HandleType(bytes):
    """Base class for all HLA handle types - direct cast from bytes"""
    def __new__(cls, data: bytes = b""):
        # Use __new__ since bytes is immutable
        return super().__new__(cls, data)
    
    def __str__(self):
        return f"{self.__class__.__name__}({self.hex()})"
    
    def __repr__(self):
        return self.__str__()
    
    def __bool__(self):
        return len(self) > 0
    
    @property
    def data(self) -> bytes:
        """Provide .data attribute for compatibility with protobuf wrappers."""
        return bytes(self)

class FederateHandle(HandleType):
    """Federate handle type - cast from bytes"""

class ObjectClassHandle(HandleType):
    """Object class handle type - cast from bytes"""

class AttributeHandle(HandleType):
    """Attribute handle type - cast from bytes"""

class InteractionClassHandle(HandleType):
    """Interaction class handle type - cast from bytes"""

class ParameterHandle(HandleType):
    """Parameter handle type - cast from bytes"""

class ObjectInstanceHandle(HandleType):
    """Object instance handle type - cast from bytes"""

class MessageRetractionHandle(HandleType):
    """Message retraction handle type - cast from bytes"""

class TransportationTypeHandle(HandleType):
    """Transportation type handle type - cast from bytes"""

class DimensionHandle(HandleType):
    """Dimension handle type - cast from bytes"""

class RegionHandle(HandleType):
    """Region handle type - cast from bytes"""

# Convenience constructors

def federate_handle(data: bytes) -> FederateHandle:
    return FederateHandle(data)

def object_class_handle(data: bytes) -> ObjectClassHandle:
    return ObjectClassHandle(data)

def attribute_handle(data: bytes) -> AttributeHandle:
    return AttributeHandle(data)

def interaction_class_handle(data: bytes) -> InteractionClassHandle:
    return InteractionClassHandle(data)

def parameter_handle(data: bytes) -> ParameterHandle:
    return ParameterHandle(data)

def object_instance_handle(data: bytes) -> ObjectInstanceHandle:
    return ObjectInstanceHandle(data)

def message_retraction_handle(data: bytes) -> MessageRetractionHandle:
    return MessageRetractionHandle(data)

def transportation_type_handle(data: bytes) -> TransportationTypeHandle:
    return TransportationTypeHandle(data)

def dimension_handle(data: bytes) -> DimensionHandle:
    return DimensionHandle(data)

def region_handle(data: bytes) -> RegionHandle:
    return RegionHandle(data)
