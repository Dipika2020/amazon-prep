
# Import Enum to define named constant values and auto() to assign their values.
from enum import Enum, auto

# Import Lock to protect shared state when multiple threads access it.
from threading import Lock

# Import datetime to record entry and exit times.
from datetime import datetime, timedelta

# Import ceil to round a partial hour up to a complete billable hour.
from math import ceil

# Import ABC and abstractmethod to define interfaces for pricing and payment.
from abc import ABC, abstractmethod


# ============================================================
# STEP 1: DEFINE VEHICLE AND PARKING SPOT TYPES
# ============================================================

# Define the kinds of vehicles the parking lot supports.
class VehicleType(Enum):
    MOTORCYCLE = auto()  # Represents a motorcycle.
    CAR = auto()         # Represents a car.
    TRUCK = auto()       # Represents a truck.


# Define the categories of physical parking spots.
class SpotType(Enum):
    MOTORCYCLE = auto()  # A spot intended for motorcycles.
    COMPACT = auto()     # A spot intended for cars and motorcycles.
    LARGE = auto()       # A larger spot that can accommodate all supported types.


# ============================================================
# STEP 2: DEFINE VEHICLE-TO-SPOT COMPATIBILITY
# ============================================================

# Map each vehicle type to the parking spot types it is allowed to use.
# A set makes membership checks straightforward and efficient.
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


# ============================================================
# STEP 3: REPRESENT A VEHICLE
# ============================================================

class Vehicle:
    # Initialize a vehicle using its license plate and vehicle category.
    def __init__(self, license_plate: str, vehicle_type: VehicleType):
        self.license_plate = license_plate  # Store the vehicle's identifier.
        self.vehicle_type = vehicle_type    # Store its type for compatibility checks.


# ============================================================
# STEP 4: REPRESENT ONE PARKING SPOT
# ============================================================

class ParkingSpot:
    # Create a parking spot with a unique ID and a spot category.
    def __init__(self, spot_id: str, spot_type: SpotType):
        self.spot_id = spot_id          # Store the spot's unique identifier.
        self.spot_type = spot_type      # Store the category of the spot.
        self.is_occupied = False        # New spots are initially available.

    # Check whether this spot can accommodate the specified vehicle.
    def can_fit(self, vehicle: Vehicle) -> bool:
        # The spot must be empty and compatible with the vehicle's type.
        return (
            not self.is_occupied
            and self.spot_type in COMPATIBLE_SPOTS[vehicle.vehicle_type]
        )

    # Report whether the spot is currently unoccupied.
    def is_available(self) -> bool:
        return not self.is_occupied


# ============================================================
# STEP 5: MANAGE PARKING SPOTS ON ONE FLOOR
# ============================================================

class ParkingFloor:
    # Initialize a floor and the collection of spots that belong to it.
    def __init__(self, floor_id: str, spots: list[ParkingSpot]):
        self.floor_id = floor_id  # Store the floor's unique identifier.
        self.spots = spots        # Store the spots managed by this floor.

        # Create a lock to protect spot reservation and release operations.
        self.lock = Lock()

    # Find the first compatible, currently available spot.
    def find_spot(self, vehicle: Vehicle) -> ParkingSpot | None:
        # Examine each spot in the order in which it appears in the list.
        for spot in self.spots:
            # Return the first spot that is both available and compatible.
            if spot.can_fit(vehicle):
                return spot

        # Return None when this floor has no suitable available spot.
        return None

    # Atomically find and reserve a spot for a vehicle.
    def try_reserve(self, vehicle: Vehicle) -> ParkingSpot | None:
        # Acquire the floor lock before checking or changing occupancy.
        with self.lock:
            # Find a compatible spot while holding the lock.
            spot = self.find_spot(vehicle)

            # If no suitable spot exists, leave the floor unchanged.
            if spot is None:
                return None

            # Mark the selected spot occupied before releasing the lock.
            spot.is_occupied = True

            # Return the reserved spot to the caller.
            return spot

    # Release a spot safely after a successful checkout.
    def release_spot(self, spot: ParkingSpot) -> None:
        # Use the same lock as reservation to synchronize occupancy changes.
        with self.lock:
            # Ensure the spot belongs to this floor before modifying it.
            if spot in self.spots:
                # Mark the spot available for another vehicle.
                spot.is_occupied = False


# ============================================================
# STEP 6A: DEFINE THE PARKING TICKET AND ITS LIFECYCLE
# ============================================================

# Represent the possible states of a parking ticket.
class TicketStatus(Enum):
    ACTIVE = auto()   # The vehicle is parked and payment is outstanding.
    PAID = auto()     # Payment succeeded, but the ticket has not yet closed.
    CLOSED = auto()   # Checkout completed and the parking session has ended.


class Ticket:
    # Store the information associated with one parking session.
    def __init__(
        self,
        ticket_id: str,
        vehicle: Vehicle,
        spot: ParkingSpot,
        entry_time: datetime,
    ):
        self.ticket_id = ticket_id    # Store the ticket's unique identifier.
        self.vehicle = vehicle        # Keep a reference to the parked vehicle.
        self.spot = spot              # Keep a reference to its assigned spot.
        self.entry_time = entry_time  # Record when the parking session began.

        # A newly issued ticket begins in the ACTIVE state.
        self.status = TicketStatus.ACTIVE

        # Prevent multiple threads from checking out the same ticket together.
        self.lock = Lock()

    # Transition an active ticket to the paid state.
    def mark_paid(self) -> None:
        # Only an ACTIVE ticket is allowed to become PAID.
        if self.status != TicketStatus.ACTIVE:
            raise ValueError("Only an active ticket can be paid.")

        # Record successful payment.
        self.status = TicketStatus.PAID

    # Transition a paid ticket to the closed state.
    def close(self) -> None:
        # A ticket cannot be closed before payment succeeds.
        if self.status != TicketStatus.PAID:
            raise ValueError("Ticket must be paid before closing.")

        # Mark the parking session as complete.
        self.status = TicketStatus.CLOSED


# ============================================================
# STEP 7: DEFINE PRICING AND PAYMENT INTERFACES
# ============================================================

# Abstract base class that allows different pricing algorithms.
class PricingStrategy(ABC):
    # Require every concrete pricing strategy to implement fee calculation.
    @abstractmethod
    def calculate_fee(
        self,
        entry_time: datetime,
        exit_time: datetime,
    ) -> float:
        # Concrete subclasses must provide the actual calculation.
        pass


# Concrete strategy: charge a fixed rate for every started hour.
class HourlyPricingStrategy(PricingStrategy):
    # Configure the amount charged per billable hour.
    def __init__(self, hourly_rate: float):
        self.hourly_rate = hourly_rate  # Save the hourly price.

    # Calculate the parking fee for the supplied entry and exit times.
    def calculate_fee(
        self,
        entry_time: datetime,
        exit_time: datetime,
    ) -> float:
        # Reject an invalid time interval.
        if exit_time < entry_time:
            raise ValueError("Exit time cannot precede entry time.")

        # Calculate the duration in seconds.
        duration_seconds = (exit_time - entry_time).total_seconds()

        # Convert seconds to hours and round any partial hour upward.
        hours = ceil(duration_seconds / 3600)

        # Multiply billable hours by the configured hourly rate.
        return hours * self.hourly_rate


# Abstract base class for payment implementations.
class PaymentProcessor(ABC):
    # Require implementations to accept a fee and ticket ID.
    @abstractmethod
    def pay(self, amount: float, ticket_id: str) -> bool:
        # Concrete subclasses decide how payment is processed.
        pass


# Mock payment processor for tests; it does not charge real money.
class MockPaymentProcessor(PaymentProcessor):
    # Configure whether simulated payments should succeed or fail.
    def __init__(self, should_succeed: bool = True):
        self.should_succeed = should_succeed  # Store the simulated result.

    # Simulate processing a payment.
    def pay(self, amount: float, ticket_id: str) -> bool:
        # Print the amount and ticket so the test output is easy to inspect.
        print(f"Processing ${amount:.2f} for ticket {ticket_id}")

        # Return the configured result to the checkout workflow.
        return self.should_succeed


# ============================================================
# STEP 8: COORDINATE THE PARKING LOT
# ============================================================

class ParkingLot:
    # Initialize the parking lot with all of its floors.
    def __init__(self, floors: list[ParkingFloor]):
        self.floors = floors  # Store the floors available to the parking lot.

        # Map each issued ticket ID to its corresponding Ticket object.
        self.tickets: dict[str, Ticket] = {}

        # Start sequential ticket numbering at one.
        self._next_ticket_number = 1

        # Protect ticket creation and ticket-number generation across threads.
        self._ticket_lock = Lock()

    # Park a vehicle and return its ticket, or None if no spot is available.
    def park(self, vehicle: Vehicle) -> Ticket | None:
        # Search floors in the order in which they were supplied.
        for floor in self.floors:
            # Atomically reserve a compatible spot on the current floor.
            spot = floor.try_reserve(vehicle)

            # Continue to the next floor if this floor has no suitable spot.
            if spot is None:
                continue

            # Generate the ticket and register it as one protected operation.
            with self._ticket_lock:
                # Create a readable ticket ID, such as T-0001.
                ticket_id = f"T-{self._next_ticket_number:04d}"

                # Increment the number so the next ticket gets a new ID.
                self._next_ticket_number += 1

                # Capture the time at which the parking session starts.
                entry_time = datetime.now()

                # Create a ticket linking the vehicle, spot, and entry time.
                ticket = Ticket(ticket_id, vehicle, spot, entry_time)

                # Save the ticket so a later checkout can look it up.
                self.tickets[ticket_id] = ticket

            # Return the newly issued ticket to the caller.
            return ticket

        # No floor had a suitable available spot.
        return None

    # Calculate the fee, process payment, close the ticket, and release the spot.
    def checkout(
        self,
        ticket_id: str,
        pricing_strategy: PricingStrategy,
        payment_processor: PaymentProcessor,
    ) -> float:
        # Retrieve the ticket associated with the supplied ID.
        ticket = self.tickets.get(ticket_id)

        # Reject ticket IDs that were never issued by this parking lot.
        if ticket is None:
            raise ValueError("Invalid ticket ID.")

        # Serialize checkout requests for this ticket.
        # A second request must wait until the first request finishes.
        with ticket.lock:
            # Only ACTIVE tickets may begin checkout.
            if ticket.status != TicketStatus.ACTIVE:
                raise ValueError("Ticket is not active.")

            # Record the time at which checkout is requested.
            exit_time = datetime.now()

            # Calculate the fee using the selected pricing strategy.
            fee = pricing_strategy.calculate_fee(
                ticket.entry_time,
                exit_time,
            )

            # Ask the configured processor to process the fee.
            payment_succeeded = payment_processor.pay(
                fee,
                ticket.ticket_id,
            )

            # If payment fails, do not close the ticket or release the spot.
            if not payment_succeeded:
                raise RuntimeError("Payment failed. Please try again.")

            # Record successful payment; the ticket is now PAID.
            ticket.mark_paid()

            # Close the ticket after payment; the ticket is now CLOSED.
            ticket.close()

            # Find the floor that owns this spot and release it safely.
            for floor in self.floors:
                # A spot belongs to the floor whose spot list contains it.
                if ticket.spot in floor.spots:
                    # Release the spot while holding the floor's lock.
                    floor.release_spot(ticket.spot)

                    # Stop searching because a spot belongs to one floor.
                    break

            # Return the calculated fee to the caller.
            return fee


# ============================================================
# TESTS: VERIFY THE PARKING LOT IMPLEMENTATION
# ============================================================

def run_tests():
    # Print a heading before running the test suite.
    print("Running Parking Lot tests...\n")

    # --------------------------------------------------------
    # Test 1: Create vehicles of different types.
    # --------------------------------------------------------

    # Construct one vehicle of each supported type.
    car = Vehicle("CAR-101", VehicleType.CAR)
    motorcycle = Vehicle("MOTO-101", VehicleType.MOTORCYCLE)
    truck = Vehicle("TRUCK-101", VehicleType.TRUCK)

    # Verify each vehicle stores the expected information.
    assert car.license_plate == "CAR-101"
    assert car.vehicle_type == VehicleType.CAR
    assert motorcycle.vehicle_type == VehicleType.MOTORCYCLE
    assert truck.vehicle_type == VehicleType.TRUCK
    print("Test 1 passed: Vehicles are created correctly.")

    # --------------------------------------------------------
    # Test 2: New parking spots start available.
    # --------------------------------------------------------

    # Construct a spot of each category.
    compact = ParkingSpot("C-101", SpotType.COMPACT)
    motorcycle_spot = ParkingSpot("M-101", SpotType.MOTORCYCLE)
    large = ParkingSpot("L-101", SpotType.LARGE)

    # Verify none of the new spots is occupied.
    assert compact.is_available() is True
    assert motorcycle_spot.is_available() is True
    assert large.is_available() is True
    print("Test 2 passed: Parking spots start available.")

    # --------------------------------------------------------
    # Test 3: Cars can use compact and large spots.
    # --------------------------------------------------------

    # Check the two spot types that accept cars.
    assert compact.can_fit(car) is True
    assert large.can_fit(car) is True
    print("Test 3 passed: Cars fit compact and large spots.")

    # --------------------------------------------------------
    # Test 4: Cars cannot use motorcycle-only spots.
    # --------------------------------------------------------

    # Verify a motorcycle-only spot rejects a car.
    assert motorcycle_spot.can_fit(car) is False
    print("Test 4 passed: Cars cannot use motorcycle-only spots.")

    # --------------------------------------------------------
    # Test 5: Motorcycles can use all three spot types.
    # --------------------------------------------------------

    # Check motorcycle compatibility against every category.
    assert motorcycle_spot.can_fit(motorcycle) is True
    assert compact.can_fit(motorcycle) is True
    assert large.can_fit(motorcycle) is True
    print("Test 5 passed: Motorcycles can use all supported spot types.")

    # --------------------------------------------------------
    # Test 6: Trucks require large spots.
    # --------------------------------------------------------

    # Verify that trucks fit large spots but not smaller categories.
    assert large.can_fit(truck) is True
    assert compact.can_fit(truck) is False
    assert motorcycle_spot.can_fit(truck) is False
    print("Test 6 passed: Trucks require large spots.")

    # --------------------------------------------------------
    # Test 7: An occupied spot cannot accept another vehicle.
    # --------------------------------------------------------

    # Simulate a car already occupying the compact spot.
    compact.is_occupied = True

    # Verify that an occupied spot is unavailable and cannot fit a car.
    assert compact.is_available() is False
    assert compact.can_fit(car) is False
    print("Test 7 passed: Occupied spots cannot accept vehicles.")

    # --------------------------------------------------------
    # Test 8: A floor can find a compatible spot.
    # --------------------------------------------------------

    # Create a floor containing one spot of each category.
    floor_spots = [
        ParkingSpot("M-201", SpotType.MOTORCYCLE),
        ParkingSpot("C-201", SpotType.COMPACT),
        ParkingSpot("L-201", SpotType.LARGE),
    ]

    # Create the floor that manages those spots.
    floor = ParkingFloor("F-2", floor_spots)

    # Create a car to search for an appropriate spot.
    car = Vehicle("CAR-202", VehicleType.CAR)

    # Search without reserving the selected spot.
    found_spot = floor.find_spot(car)

    # Verify the compact spot is the first compatible available spot.
    assert found_spot is not None
    assert found_spot.spot_id == "C-201"
    assert found_spot.is_available() is True
    print("Test 8 passed: Floor finds a compatible spot.")

    # --------------------------------------------------------
    # Test 9: Reserving a spot marks it occupied.
    # --------------------------------------------------------

    # Reserve a spot for the first car.
    reserved_spot = floor.try_reserve(car)

    # Verify the expected spot was selected and is now occupied.
    assert reserved_spot is not None
    assert reserved_spot.spot_id == "C-201"
    assert reserved_spot.is_available() is False
    print("Test 9 passed: Reservation occupies the spot.")

    # --------------------------------------------------------
    # Test 10: A second car receives a different available spot.
    # --------------------------------------------------------

    # Create a second car.
    second_car = Vehicle("CAR-203", VehicleType.CAR)

    # Reserve another spot for the second car.
    second_spot = floor.try_reserve(second_car)

    # The compact spot is occupied, so the large spot should be selected.
    assert second_spot is not None
    assert second_spot.spot_id == "L-201"
    print("Test 10 passed: A second car gets another compatible spot.")

    # --------------------------------------------------------
    # Test 11: A truck is rejected when no large spot is available.
    # --------------------------------------------------------

    # Create a truck and attempt to reserve a spot.
    truck = Vehicle("TRUCK-202", VehicleType.TRUCK)
    truck_spot = floor.try_reserve(truck)

    # The only large spot is occupied; the remaining spots are incompatible.
    assert truck_spot is None
    print("Test 11 passed: Full compatible capacity returns None.")

    # --------------------------------------------------------
    # Test 12: Parking creates a ticket and reserves a spot.
    # --------------------------------------------------------

    # Create a new floor and parking lot for this integration test.
    integration_spot = ParkingSpot("C-301", SpotType.COMPACT)
    integration_floor = ParkingFloor("F-3", [integration_spot])
    parking_lot = ParkingLot([integration_floor])

    # Create a vehicle and park it through the ParkingLot interface.
    integration_car = Vehicle("CAR-301", VehicleType.CAR)
    ticket = parking_lot.park(integration_car)

    # Confirm that parking succeeded.
    assert ticket is not None

    # Confirm the ticket references the original vehicle object.
    assert ticket.vehicle is integration_car

    # Confirm the ticket references the spot reserved for this vehicle.
    assert ticket.spot is integration_spot

    # A new ticket should be ACTIVE.
    assert ticket.status == TicketStatus.ACTIVE

    # The ticket should be registered in the parking lot's dictionary.
    assert ticket.ticket_id in parking_lot.tickets

    # The spot should be occupied after parking.
    assert integration_spot.is_available() is False
    print("Test 12 passed: Parking creates a ticket and reserves a spot.")

    # --------------------------------------------------------
    # Test 13: A full parking lot rejects another vehicle.
    # --------------------------------------------------------

    # Create a second car while the only spot remains occupied.
    another_car = Vehicle("CAR-302", VehicleType.CAR)

    # Attempt to park the second car.
    rejected_ticket = parking_lot.park(another_car)

    # Parking should fail because no compatible spot is available.
    assert rejected_ticket is None
    print("Test 13 passed: A full lot rejects another vehicle.")

    # --------------------------------------------------------
    # Test 14: Ticket state transitions are validated.
    # --------------------------------------------------------

    # Create a separate ticket to test its lifecycle independently.
    lifecycle_ticket = Ticket(
        "T-LIFECYCLE",
        car,
        large,
        datetime.now(),
    )

    # The ticket begins in the ACTIVE state.
    assert lifecycle_ticket.status == TicketStatus.ACTIVE

    # Mark the ticket paid and verify the transition.
    lifecycle_ticket.mark_paid()
    assert lifecycle_ticket.status == TicketStatus.PAID

    # Close the paid ticket and verify the final transition.
    lifecycle_ticket.close()
    assert lifecycle_ticket.status == TicketStatus.CLOSED
    print("Test 14 passed: Ticket payment and closure states work.")

    # --------------------------------------------------------
    # Test 15: Successful checkout closes the ticket and frees the spot.
    # --------------------------------------------------------

    # Build a separate lot so this test does not depend on earlier tests.
    checkout_spot = ParkingSpot("C-401", SpotType.COMPACT)
    checkout_floor = ParkingFloor("F-4", [checkout_spot])
    checkout_lot = ParkingLot([checkout_floor])

    # Park a car and obtain its ticket.
    checkout_car = Vehicle("CAR-401", VehicleType.CAR)
    checkout_ticket = checkout_lot.park(checkout_car)

    # Ensure parking succeeded before attempting checkout.
    assert checkout_ticket is not None

    # Configure a price of $5 for every started hour.
    pricing = HourlyPricingStrategy(hourly_rate=5.0)

    # Configure the mock payment processor to succeed.
    successful_payment = MockPaymentProcessor(should_succeed=True)

    # Set entry time to 61 minutes before checkout.
    # This ensures the duration rounds up to exactly two billable hours.
    checkout_ticket.entry_time = datetime.now() - timedelta(minutes=61)

    # Check out the vehicle and calculate the fee.
    fee = checkout_lot.checkout(
        checkout_ticket.ticket_id,
        pricing,
        successful_payment,
    )

    # Sixty-one minutes at $5 per started hour should cost $10.
    assert fee == 10.0

    # A successful checkout should close the ticket.
    assert checkout_ticket.status == TicketStatus.CLOSED

    # A successful checkout should make the spot available again.
    assert checkout_spot.is_available() is True
    print("Test 15 passed: Successful checkout closes ticket and frees spot.")

    # --------------------------------------------------------
    # Test 16: Invalid ticket IDs are rejected.
    # --------------------------------------------------------

    # Attempt checkout using an ID that was never issued.
    try:
        checkout_lot.checkout(
            "INVALID-TICKET",
            pricing,
            successful_payment,
        )

        # Fail the test if checkout unexpectedly succeeds.
        assert False, "Expected invalid ticket to be rejected."

    # Catch the expected error for an unknown ticket.
    except ValueError as error:
        assert str(error) == "Invalid ticket ID."

    print("Test 16 passed: Invalid ticket IDs are rejected.")

    # --------------------------------------------------------
    # Test 17: Failed payment preserves the ticket and the spot.
    # --------------------------------------------------------

    # Create another isolated lot for the failed-payment test.
    failure_spot = ParkingSpot("C-402", SpotType.COMPACT)
    failure_floor = ParkingFloor("F-5", [failure_spot])
    failure_lot = ParkingLot([failure_floor])

    # Park a car and obtain its active ticket.
    failure_car = Vehicle("CAR-402", VehicleType.CAR)
    failure_ticket = failure_lot.park(failure_car)

    # Ensure a ticket was created.
    assert failure_ticket is not None

    # Configure the mock processor to simulate a failed payment.
    failed_payment = MockPaymentProcessor(should_succeed=False)

    # Attempt checkout and expect a payment failure.
    try:
        failure_lot.checkout(
            failure_ticket.ticket_id,
            pricing,
            failed_payment,
        )

        # Fail the test if the checkout unexpectedly succeeds.
        assert False, "Expected payment failure."

    # Verify that the expected payment error is raised.
    except RuntimeError as error:
        assert str(error) == "Payment failed. Please try again."

    # Failed payment must leave the ticket active.
    assert failure_ticket.status == TicketStatus.ACTIVE

    # Failed payment must leave the spot occupied.
    assert failure_spot.is_available() is False
    print("Test 17 passed: Failed payment preserves ticket and spot.")

    # --------------------------------------------------------
    # Test 18: Verify hourly pricing with a known duration.
    # --------------------------------------------------------

    # Define a fixed entry time for the pricing calculation.
    entry = datetime(2026, 1, 1, 10, 0, 0)

    # Define an exit time 61 minutes later.
    exit_time = datetime(2026, 1, 1, 11, 1, 0)

    # At $5 per hour, 61 minutes must be charged as two hours.
    expected_fee = 10.0

    # Calculate the fee directly, without involving checkout or payment.
    actual_fee = pricing.calculate_fee(entry, exit_time)

    # Verify the calculation matches the expected amount.
    assert actual_fee == expected_fee, (
        f"Expected ${expected_fee:.2f}, got ${actual_fee:.2f}"
    )
    print("Test 18 passed: Hourly pricing rounds up correctly.")

    # --------------------------------------------------------
    # Test 19: A closed ticket cannot be checked out again.
    # --------------------------------------------------------

    # The ticket used in Test 15 is already CLOSED.
    # Attempt to check it out a second time.
    try:
        checkout_lot.checkout(
            checkout_ticket.ticket_id,
            pricing,
            successful_payment,
        )

        # Fail the test if a second checkout is allowed.
        assert False, "Expected repeated checkout to be rejected."

    # The closed ticket should be rejected as inactive.
    except ValueError as error:
        assert str(error) == "Ticket is not active."

    # Confirm the ticket remains closed after the rejected attempt.
    assert checkout_ticket.status == TicketStatus.CLOSED

    # Confirm the spot remains available after the rejected attempt.
    assert checkout_spot.is_available() is True
    print("Test 19 passed: Repeated checkout is rejected.")

    # Print the final message only after every assertion succeeds.
    print("\nAll tests passed!")


# Run the test suite only when this file is executed directly.
# Importing this file from another module will not automatically run tests.
if __name__ == "__main__":
    run_tests()
