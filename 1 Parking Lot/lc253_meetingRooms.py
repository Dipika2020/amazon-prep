"""
Meeting Rooms II — Interview Practice
This is a self-contained version of the problem, with examples, an approach summary, complexity analysis, and a fully commented Python solution.
1. Problem statement
You are given an array intervals where intervals[i] = [starti, endi] represents the start and end times of the ith meeting.
Return the minimum number of conference rooms required to hold all meetings.
A room can host only one meeting at a time. If one meeting ends at the exact time another begins, the same room can be reused.

Example 1
Input:
intervals = [[0, 30], [5, 10], [15, 20]]

Output: 2

Explanation: Meeting 1 overlaps with both other meetings. Meetings 2 and 3 do not overlap with each other, so they can use the same second room.
"""

"""
3. Approach gist — sorting + min-heap
A min-heap lets us quickly find the meeting that finishes earliest.
The idea is to:
1. Sort all meetings by their start time.
2. Maintain a min-heap containing the end times of meetings currently assigned to rooms.
3. For each meeting:
   - If the earliest-ending meeting finishes at or before the new meeting's start, reuse that room by removing its end time from the heap.
   - Add the new meeting's end time to the heap.
4. The heap's maximum size represents the maximum number of rooms needed.

4. Expected time and space complexity
- Time: O(nlogn)
  - Sorting takes O(nlogn)
  - Each meeting is inserted into the heap once and may cause one removal, each costing O(logn).
- Auxiliary space: O(n) for the heap in the worst case.
- The sorting operation may also use additional implementation-dependent space.

"""


import heapq  # Provides min-heap operations.


class Solution:  # Defines the solution class expected by LeetCode.
    def minMeetingRooms(self, intervals: list[list[int]]) -> int:
        # If there are no meetings, no rooms are required.
        if not intervals:
            return 0

        # Sort meetings by their start times in ascending order.
        intervals.sort(key=lambda meeting: meeting[0])

        # Create an empty min-heap to store room meeting end times.
        min_heap = []

        # Process each meeting in chronological order.
        for meeting in intervals:
            # Extract the current meeting's start time.
            start = meeting[0]

            # Extract the current meeting's end time.
            end = meeting[1]

            # If the earliest room is free, reuse that room.
            if min_heap and min_heap[0] <= start:
                # Remove the earliest finishing meeting from the heap.
                heapq.heappop(min_heap)

            # Assign the current meeting to a room.
            # Store its end time to track when the room becomes free.
            heapq.heappush(min_heap, end)

        # The heap's final size is the minimum number of rooms needed.
        return len(min_heap)
