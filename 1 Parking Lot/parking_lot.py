
from enum import Enum, auto


# Step 1: Define the types of vehicles supported by the parking lot.
class VehicleType(Enum):
    MOTORCYCLE = auto()
    CAR = auto()
    TRUCK = auto()


# Step 1: Define the types of parking spots available.
class SpotType(Enum):
    MOTORCYCLE = auto()
    COMPACT = auto()
    LARGE = auto()


# Step 2: Define which types of parking spots each vehicle can use.
COMPATIBLE_SPOTS = {
    VehicleType.MOTORCYCLE: {
        SpotType.MOTORCYCLE,
        SpotType.COMPACT,
        SpotType.LARGE,
    },
    VehicleType.CAR: {
        SpotType.COMPACT,
        SpotType.LARGE,
    },
    VehicleType.TRUCK: {
        SpotType.LARGE,
    },
}


# Step 3: Represent a vehicle entering the parking lot.
class Vehicle:
    def __init__(self, license_plate: str, vehicle_type: VehicleType):
        # Store the vehicle's identifier.
        self.license_plate = license_plate

        # Store the vehicle's type.
        self.vehicle_type = vehicle_type


# Step 4: Represent one physical parking spot.
class ParkingSpot:
    def __init__(self, spot_id: str, spot_type: SpotType):
        # Unique identifier for this spot.
        self.spot_id = spot_id

        # Category of this parking spot.
        self.spot_type = spot_type

        # All spots start out unoccupied.
        self.is_occupied = False

    def can_fit(self, vehicle: Vehicle) -> bool:
        # A vehicle fits only if the spot is empty
        # and the spot type supports the vehicle type.
        return (
            not self.is_occupied
            and self.spot_type in COMPATIBLE_SPOTS[vehicle.vehicle_type]
        )

    def is_available(self) -> bool:
        # Return True when no vehicle occupies this spot.
        return not self.is_occupied


# --------------------------------------------------
# TEST CASES: Verify Steps 1–4
# --------------------------------------------------
def run_tests():
    print("Running Parking Lot tests...\n")

    # Test 1: Create vehicles of different types.
    car = Vehicle("CAR-101", VehicleType.CAR)
    motorcycle = Vehicle("MOTO-101", VehicleType.MOTORCYCLE)
    truck = Vehicle("TRUCK-101", VehicleType.TRUCK)

    assert car.license_plate == "CAR-101"
    assert car.vehicle_type == VehicleType.CAR
    assert motorcycle.vehicle_type == VehicleType.MOTORCYCLE
    assert truck.vehicle_type == VehicleType.TRUCK
    print("Test 1 passed: Vehicles are created correctly.")

    # Test 2: Create parking spots of different types.
    compact = ParkingSpot("C-101", SpotType.COMPACT)
    motorcycle_spot = ParkingSpot("M-101", SpotType.MOTORCYCLE)
    large = ParkingSpot("L-101", SpotType.LARGE)

    # All spots should be available initially.
    assert compact.is_available() is True
    assert motorcycle_spot.is_available() is True
    assert large.is_available() is True
    print("Test 2 passed: Parking spots start available.")

    # Test 3: A car can use compact and large spots.
    assert compact.can_fit(car) is True
    assert large.can_fit(car) is True
    print("Test 3 passed: Cars fit compact and large spots.")

    # Test 4: A car cannot use a motorcycle-only spot.
    assert motorcycle_spot.can_fit(car) is False
    print("Test 4 passed: Cars cannot use motorcycle-only spots.")

    # Test 5: A motorcycle can use all three spot types.
    assert motorcycle_spot.can_fit(motorcycle) is True
    assert compact.can_fit(motorcycle) is True
    assert large.can_fit(motorcycle) is True
    print("Test 5 passed: Motorcycles can use all supported spot types.")

    # Test 6: A truck can use only a large spot.
    assert large.can_fit(truck) is True
    assert compact.can_fit(truck) is False
    assert motorcycle_spot.can_fit(truck) is False
    print("Test 6 passed: Trucks require large spots.")

    # Test 7: An occupied spot cannot accept another vehicle.
    compact.is_occupied = True
    assert compact.is_available() is False
    assert compact.can_fit(car) is False
    print("Test 7 passed: Occupied spots cannot accept vehicles.")

    print("\nAll tests passed!")


# Run 
if __name__ == "__main__":
    run_tests()
