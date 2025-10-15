#!/usr/bin/env python3
"""
DDM (Data Distribution Management) region data for HLA Bounce federate.
Manages spatial regions for efficient data distribution.
"""

from typing import Dict, List, Tuple, Optional

class DdmRegion:
    """Represents a DDM region for spatial data distribution."""
    
    def __init__(self, region_id: str, x_min: float = 0.0, x_max: float = 100.0, 
            y_min: float = 0.0, y_max: float = 100.0):
        self.region_id = region_id
        self.x_min = x_min
        self.x_max = x_max
        self.y_min = y_min
        self.y_max = y_max
        self.is_active = False
        self.region_handle = None
        
    def contains_point(self, x: float, y: float) -> bool:
        """Check if a point is within this region."""
        return (self.x_min <= x <= self.x_max and 
                self.y_min <= y <= self.y_max)
                
    def overlaps_with(self, other: 'DdmRegion') -> bool:
        """Check if this region overlaps with another region."""
        return not (self.x_max < other.x_min or other.x_max < self.x_min or
            self.y_max < other.y_min or other.y_max < self.y_min)

    def set_bounds(self, x_min: float, x_max: float, y_min: float, y_max: float):
        """Set the bounds of this region."""
        self.x_min = x_min
        self.x_max = x_max
        self.y_min = y_min
        self.y_max = y_max
        
    def get_bounds(self) -> Tuple[float, float, float, float]:
        """Get the bounds as a tuple (x_min, x_max, y_min, y_max)."""
        return (self.x_min, self.x_max, self.y_min, self.y_max)
        
    def get_center(self) -> Tuple[float, float]:
        """Get the center point of the region."""
        center_x = (self.x_min + self.x_max) / 2.0
        center_y = (self.y_min + self.y_max) / 2.0
        return (center_x, center_y)
        
    def get_area(self) -> float:
        """Get the area of the region."""
        return (self.x_max - self.x_min) * (self.y_max - self.y_min)
        
    def __str__(self):
        return f"DdmRegion({self.region_id}: [{self.x_min:.2f},{self.x_max:.2f}] x [{self.y_min:.2f},{self.y_max:.2f}])"


class DdmRegionMap:
    """Manages a collection of DDM regions."""
    
    def __init__(self):
        self.regions: Dict[str, DdmRegion] = {}
        self.subscription_regions: Dict[str, DdmRegion] = {}  # Regions we subscribe to
        self.update_regions: Dict[str, DdmRegion] = {}        # Regions we update in
        
    def add_region(self, region: DdmRegion, is_subscription: bool = True, is_update: bool = False):
        """Add a region to the collection."""
        self.regions[region.region_id] = region
        
        if is_subscription:
            self.subscription_regions[region.region_id] = region
            
        if is_update:
            self.update_regions[region.region_id] = region
            
    def remove_region(self, region_id: str):
        """Remove a region from all collections."""
        if region_id in self.regions:
            del self.regions[region_id]
        if region_id in self.subscription_regions:
            del self.subscription_regions[region_id]
        if region_id in self.update_regions:
            del self.update_regions[region_id]
            
    def get_region(self, region_id: str) -> Optional[DdmRegion]:
        """Get a region by ID."""
        return self.regions.get(region_id)
        
    def get_all_regions(self) -> Dict[str, DdmRegion]:
        """Get all regions."""
        return self.regions.copy()
        
    def get_subscription_regions(self) -> Dict[str, DdmRegion]:
        """Get subscription regions."""
        return self.subscription_regions.copy()
        
    def get_update_regions(self) -> Dict[str, DdmRegion]:
        """Get update regions."""
        return self.update_regions.copy()
        
    def find_regions_containing_point(self, x: float, y: float) -> List[DdmRegion]:
        """Find all regions that contain a given point."""
        containing_regions = []
        for region in self.regions.values():
            if region.contains_point(x, y):
                containing_regions.append(region)
        return containing_regions
        
    def find_overlapping_regions(self, target_region: DdmRegion) -> List[DdmRegion]:
        """Find all regions that overlap with the target region."""
        overlapping_regions = []
        for region in self.regions.values():
            if region.region_id != target_region.region_id and region.overlaps_with(target_region):
                overlapping_regions.append(region)
        return overlapping_regions
        
    def create_default_regions(self, world_width: float = 200.0, world_height: float = 200.0):
        """Create default regions covering the simulation space."""
        # Create a single region covering the entire world
        full_region = DdmRegion("full_world", 0.0, world_width, 0.0, world_height)
        self.add_region(full_region, is_subscription=True, is_update=True)
        
        # Create quadrant regions for more granular control
        half_width = world_width / 2
        half_height = world_height / 2
        
        quadrants = [
            ("quadrant_1", 0.0, half_width, 0.0, half_height),
            ("quadrant_2", half_width, world_width, 0.0, half_height),
            ("quadrant_3", 0.0, half_width, half_height, world_height),
            ("quadrant_4", half_width, world_width, half_height, world_height)
        ]
        
        for quad_id, x_min, x_max, y_min, y_max in quadrants:
            region = DdmRegion(quad_id, x_min, x_max, y_min, y_max)
            self.add_region(region, is_subscription=True, is_update=False)
            
    def clear(self):
        """Clear all regions."""
        self.regions.clear()
        self.subscription_regions.clear()
        self.update_regions.clear()
        
    def __len__(self):
        return len(self.regions)
        
    def __str__(self):
        return f"DdmRegionMap: {len(self.regions)} regions ({len(self.subscription_regions)} subscription, {len(self.update_regions)} update)"
