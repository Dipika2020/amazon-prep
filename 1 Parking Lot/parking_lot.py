
from enum import Enum, auto
from threading import Lock
from datetime import datetime
from math import ceil
from abc import ABC, abstractmethod


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

# Step 5: Manage all parking spots on one floor.
# import lock
class ParkingFloor:
    def __init__(self, floor_id: str, spots: list[ParkingSpot]):
        # Identify this floor.
        self.floor_id = floor_id

        # Store the parking spots belonging to this floor.
        self.spots = spots

        # Protect spot reservations from concurrent arrivals.
        self.lock = Lock()

    def find_spot(self, vehicle: Vehicle) -> ParkingSpot | None:
        # Search the floor for the first compatible available spot.
        for spot in self.spots:
            if spot.can_fit(vehicle):
                return spot

        # Return None if no compatible spot is available.
        return None

    def try_reserve(self, vehicle: Vehicle) -> ParkingSpot | None:
        # Hold the lock while checking and reserving a spot.
        # This prevents two threads from reserving the same spot.
        with self.lock:
            spot = self.find_spot(vehicle)

            # No suitable spot was found.
            if spot is None:
                return None

            # Mark the selected spot as occupied.
            spot.is_occupied = True

            # Return the successfully reserved spot.
            return spot

# Step 6A: Create the Ticket class
# import datetime & enum, auto

# represents lifecycle of parking ticket
class TicketStatus(Enum):
    ACTIVE = auto()
    PAID = auto()
    CLOSED = auto()

# store info about one parking session:
class Ticket:
    def __init__(self, ticket_id: str, vehicle: Vehicle, spot: ParkingSpot, entry_time: datetime,):
        # unique identifier
        self.ticket_id = ticket_id
        self.vehicle = vehicle
        #spot assigned to the vehicle
        self.spot = spot
        self.entry_time = entry_time
        self.status = TicketStatus.ACTIVE

    def mark_paid(self) -> None:
        # record that payment is completed
        if self.status != TicketStatus.ACTIVE:
            raise ValueError("Only an active ticket can be paid.")

        self.status = TicketStatus.PAID

    def close(self) -> None:
        # close ticket after payment
        if self.status != TicketStatus.PAID:
            raise ValueError("Ticket must be paid before closing.")

        self.status = TicketStatus.CLOSED


#s7. implementing pricing and payment
# import ceil, abstract method
# why abstract? PricingStrategy lets us change how fees are calculated without rewriting the parking workflow. PaymentProcessor lets us swap the mock payment implementation for another implementation later.

# Defines the contract that all pricing strategies must follow.
class PricingStrategy(ABC):
    @abstractmethod
    def calculate_fee(
        self,
        entry_time: datetime,
        exit_time: datetime,
    ) -> float:
        pass


# Charges a fixed rate for each started hour.
class HourlyPricingStrategy(PricingStrategy):
    def __init__(self, hourly_rate: float):
        self.hourly_rate = hourly_rate

    def calculate_fee(
        self,
        entry_time: datetime,
        exit_time: datetime,
    ) -> float:
        # Reject invalid timestamps.
        if exit_time < entry_time:
            raise ValueError("Exit time cannot precede entry time.")

        # Convert the parking duration into seconds.
        duration_seconds = (exit_time - entry_time).total_seconds()

        # Charge for every started hour.
        hours = ceil(duration_seconds / 3600)

        # Return the total fee.
        return hours * self.hourly_rate


# Defines the contract for payment processing.
class PaymentProcessor(ABC):
    @abstractmethod
    def pay(self, amount: float, ticket_id: str) -> bool:
        pass


# Simple payment implementation for local testing.
class MockPaymentProcessor(PaymentProcessor):
    def __init__(self, should_succeed: bool = True):
        self.should_succeed = should_succeed

    def pay(self, amount: float, ticket_id: str) -> bool:
        # Simulate success or failure without charging real money.
        print(f"Processing ${amount:.2f} for ticket {ticket_id}")
        return self.should_succeed



#Step 6B: Implement ParkingLot.park()

# Coordinates parking across all floors.
class ParkingLot:
    def __init__(self, floors: list[ParkingFloor]):
        # Store all floors belonging to this parking lot.
        self.floors = floors

        # Store issued tickets using their unique ticket IDs.
        self.tickets: dict[str, Ticket] = {}

        # Generate sequential ticket IDs for this example.
        self._next_ticket_number = 1

    def park(self, vehicle: Vehicle) -> Ticket | None:
        # Search each floor until a compatible spot is reserved.
        for floor in self.floors:
            spot = floor.try_reserve(vehicle)

            # Skip this floor if no compatible spot is available.
            if spot is None:
                continue

            # Generate a ticket ID.
            ticket_id = f"T-{self._next_ticket_number:04d}"
            self._next_ticket_number += 1

            # Record the time when the vehicle enters.
            entry_time = datetime.now()

            # Create a ticket for the parking session.
            ticket = Ticket(ticket_id, vehicle, spot, entry_time)

            # Store the ticket so checkout can find it later.
            self.tickets[ticket_id] = ticket

            # Return the ticket to the caller.
            return ticket

        # No floor had a compatible available spot.
        return None

    
    def checkout(
        self,
        ticket_id: str,
        pricing_strategy: PricingStrategy,
        payment_processor: PaymentProcessor,
    ) -> float:
        # Look up the ticket.
        ticket = self.tickets.get(ticket_id)

        # Reject unknown ticket IDs.
        if ticket is None:
            raise ValueError("Invalid ticket ID.")

        # Prevent a paid or closed ticket from being charged again.
        if ticket.status != TicketStatus.ACTIVE:
            raise ValueError("Ticket is not active.")

        # Record the exit time.
        exit_time = datetime.now()

        # Calculate the parking fee.
        fee = pricing_strategy.calculate_fee(
            ticket.entry_time,
            exit_time,
        )

        # Attempt payment before releasing the spot.
        payment_succeeded = payment_processor.pay(
            fee,
            ticket.ticket_id,
        )

        # If payment fails, leave the ticket and spot unchanged.
        if not payment_succeeded:
            raise RuntimeError("Payment failed. Please try again.")

        # Mark the ticket paid, then close the session.
        ticket.mark_paid()
        ticket.close()

        # Release the spot after successful payment.
        ticket.spot.is_occupied = False

        # Return the amount charged.
        return fee




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

    
    # Test 8: A floor can find a compatible spot.
    floor_spots = [
        ParkingSpot("M-201", SpotType.MOTORCYCLE),
        ParkingSpot("C-201", SpotType.COMPACT),
        ParkingSpot("L-201", SpotType.LARGE),
    ]

    floor = ParkingFloor("F-2", floor_spots)
    car = Vehicle("CAR-202", VehicleType.CAR)

    found_spot = floor.find_spot(car)

    assert found_spot is not None
    assert found_spot.spot_id == "C-201"
    assert found_spot.is_available() is True
    print("Test 8 passed: Floor finds a compatible spot.")

    # Test 9: Reserving a spot marks it as occupied.
    reserved_spot = floor.try_reserve(car)

    assert reserved_spot is not None
    assert reserved_spot.spot_id == "C-201"
    assert reserved_spot.is_available() is False
    print("Test 9 passed: Reservation occupies the spot.")

    # Test 10: A second car cannot reserve the same compact spot.
    second_car = Vehicle("CAR-203", VehicleType.CAR)
    second_spot = floor.try_reserve(second_car)

    # The large spot is available, so the second car gets that spot.
    assert second_spot is not None
    assert second_spot.spot_id == "L-201"
    print("Test 10 passed: A second car gets another compatible spot.")

    # Test 11: A truck cannot use the motorcycle or compact spots.
    truck = Vehicle("TRUCK-202", VehicleType.TRUCK)
    truck_spot = floor.try_reserve(truck)

    # The large spot is now occupied, so no suitable spot remains.
    assert truck_spot is None
    print("Test 11 passed: Full compatible capacity returns None.")

    
    # Test 12: Parking a vehicle reserves a spot and creates a ticket.
    integration_spot = ParkingSpot("C-301", SpotType.COMPACT)
    integration_floor = ParkingFloor("F-3", [integration_spot])
    parking_lot = ParkingLot([integration_floor])

    integration_car = Vehicle("CAR-301", VehicleType.CAR)
    ticket = parking_lot.park(integration_car)

    assert ticket is not None

    print("Expected vehicle:", integration_car.license_plate)
    print("Actual vehicle:", ticket.vehicle.license_plate)
    print("Same object:", ticket.vehicle is integration_car)
    print("Ticket ID:", ticket.ticket_id)

    assert ticket.vehicle is integration_car

    assert ticket.spot is integration_spot
    assert ticket.status == TicketStatus.ACTIVE
    assert ticket.ticket_id in parking_lot.tickets
    assert integration_spot.is_available() is False
    print("Test 12 passed: Parking creates a ticket and reserves a spot.")

    # Test 13: A full lot rejects another vehicle.
    another_car = Vehicle("CAR-302", VehicleType.CAR)
    rejected_ticket = parking_lot.park(another_car)

    assert rejected_ticket is None
    print("Test 13 passed: A full lot rejects another vehicle.")

    # Test 14: Ticket state transitions are validated.
    ticket.mark_paid()
    assert ticket.status == TicketStatus.PAID

    ticket.close()
    assert ticket.status == TicketStatus.CLOSED
    print("Test 14 passed: Ticket payment and closure states work.")


    
    # Test 15: Successful checkout closes the ticket and frees the spot.
    checkout_spot = ParkingSpot("C-401", SpotType.COMPACT)
    checkout_floor = ParkingFloor("F-4", [checkout_spot])
    checkout_lot = ParkingLot([checkout_floor])

    checkout_car = Vehicle("CAR-401", VehicleType.CAR)
    checkout_ticket = checkout_lot.park(checkout_car)

    assert checkout_ticket is not None

    # Use a fixed hourly rate for this test.
    pricing = HourlyPricingStrategy(hourly_rate=5.0)
    successful_payment = MockPaymentProcessor(should_succeed=True)

    # Set a known entry time to make the fee deterministic.
    checkout_ticket.entry_time = datetime(2026, 1, 1, 10, 0, 0)

    fee = checkout_lot.checkout(
        checkout_ticket.ticket_id,
        pricing,
        successful_payment,
    )

    assert fee >= 0
    assert checkout_ticket.status == TicketStatus.CLOSED
    assert checkout_spot.is_available() is True
    print("Test 15 passed: Successful checkout closes ticket and frees spot.")

    # Test 16: Invalid ticket IDs are rejected.
    try:
        checkout_lot.checkout(
            "INVALID-TICKET",
            pricing,
            successful_payment,
        )
        assert False, "Expected invalid ticket to be rejected."
    except ValueError as error:
        assert str(error) == "Invalid ticket ID."

    print("Test 16 passed: Invalid ticket IDs are rejected.")

    # Test 17: Failed payment must not release the spot.
    failure_spot = ParkingSpot("C-402", SpotType.COMPACT)
    failure_lot = ParkingLot([
        ParkingFloor("F-5", [failure_spot])
    ])

    failure_car = Vehicle("CAR-402", VehicleType.CAR)
    failure_ticket = failure_lot.park(failure_car)
    assert failure_ticket is not None

    failed_payment = MockPaymentProcessor(should_succeed=False)

    try:
        failure_lot.checkout(
            failure_ticket.ticket_id,
            pricing,
            failed_payment,
        )
        assert False, "Expected payment failure."
    except RuntimeError as error:
        assert str(error) == "Payment failed. Please try again."

    assert failure_ticket.status == TicketStatus.ACTIVE
    assert failure_spot.is_available() is False
    print("Test 17 passed: Failed payment preserves ticket and spot.")

    
    # Test 18: Verify hourly pricing with a known duration.
    entry = datetime(2026, 1, 1, 10, 0, 0)
    exit_time = datetime(2026, 1, 1, 11, 1, 0)

    # 61 minutes rounds up to two billable hours.
    expected_fee = 10.0  # $5 per hour × 2 hours
    actual_fee = pricing.calculate_fee(entry, exit_time)

    assert actual_fee == expected_fee, (
        f"Expected ${expected_fee:.2f}, got ${actual_fee:.2f}"
    )
    print("Test 18 passed: Hourly pricing rounds up correctly.")


    print("\nAll tests passed!")


# Run 
if __name__ == "__main__":
    run_tests()
