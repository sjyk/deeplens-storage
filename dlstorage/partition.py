"""
This module partitions video clips logically - it returns division points.
"""

from typing import List, Set, Tuple, Dict

def partition(tags: Set[Tuple[str, int, int]], no_frames: int, cost_table: Dict[str, float] = dict(),
    default_cost: float = 1, penalty: float = 2) -> List[int]:
    """partition() takes annotations of each frame, penalty for each cut and returns best partition strategy.

    Args:
        tags - set of time intervals where a tag occurs:
            { (label, start, end) }, a video from time 0 (inclusive) to time T (exclusive)
            e.g. {('cat', 3, 9), ('dog', 5, 8), ('people', 0, 6)}
            e.g. {('cat', 0, 1), ('cat', 2, 4), ('cat', 6, 8), ('dog', 0, 3),
                  ('dog', 6, 8), ('people', 0, 2), ('people', 4, 6)}
        no_frames - number of frames for this video clip
        cost_table (optional) - the skip cost (weight) for each label present.
        default_cost (optional) - cost (weight) if not found from cost_table (Default 1)
        penalty (optional) - for each cut, add how much penalty to total cost (Default 2)

    Returns:
        divisions (list of division points) - frame indexes BEFORE which we should cut
    """

    # Step 1. Enumerate All "Cutting" Points
    # Put all start and end times into a big set including 0 and T. These enumerate the possible segment boundaries.
    # In: ('cat',1,3), ('dog',4,7), ('cat',5,7)
    # Out: [0,1,3,4,5,7]

    cutting_points = {0, no_frames}
    for tag in tags:
        _, start, end = tag
        cutting_points.add(start)
        cutting_points.add(end)

    # Step 2. Enumerate All Possible Segments (with penalty added)
    # Enumerate all pairs of cutting points returned by step 1. These enumerate the boundaries of all possible segments.
    # In: [0,1,3,7]
    # Out: [(0,1), (0,3), (0,7), (1,3), (1,7), (3,7)]

    possible_segments = set()
    for start in cutting_points:
        for end in cutting_points:
            if start < end:
                possible_segments.add((penalty, start, end))

    # Step 3. Assign a Skip Cost to each segment
    # For each tuple of points returned by Step 2, calculate the skip cost (number of labels present * time * weights for the labels present)
    # In: [(0,1), (0,3), (0,7), (1,3), (1,7), (3,7)]
    # Out: [(cost, 0,1), (cost, 0,3), (cost, 0,7),....]

    weighted_segments = set()
    for segment in possible_segments:
        for tag in tags:
            if tag[1] >= segment[2] or tag[2] <= segment[1]:
                continue
            length = segment[2] - segment[1]
            if tag[0] in cost_table.keys():
                segment = (segment[0] + cost_table[tag[0]] * length, segment[1], segment[2])
            else:
                segment = (segment[0] + default_cost * length, segment[1], segment[2])
        weighted_segments.add(segment)

    # Step 4. Build a directed acyclic graph
    # For each tuple returned by step 3 (now annotated with a cost) you can build a graph in the following way. 
    # - All tuples are vertices
    # - Add a directed edge -> when segment1.end == segment2.start
    # Over this graph any path that starts with a vertex segment.start == 0, and segment.end == T is full segmentation.

    graph = {vertex[1]: dict() for vertex in weighted_segments}
    for segment in weighted_segments:
        graph[segment[1]].update({segment[2]: segment[0]})

    # Step 5. Algorithm
    # For each vertex where segment.start == 0, run djikstra's algorithm to find the minimum cost path that terminates at a segment where segment.end == T
    # Return the lowest cost path for all possible start vertices.

    def dijkstra(graph, start, end):
        dist = dict()
        prev = dict()
        unvisited = set()
        for edge_start, edge in graph.items():
            unvisited.add(edge_start)
            for edge_end in edge:
                unvisited.add(edge_end)
        dist[start] = 0

        current = start
        while True:
            unvisited.remove(current)
            for neighbor in graph[current]:
                cost = graph[current][neighbor]
                if neighbor not in dist or dist[current] + cost < dist[neighbor]:
                    dist[neighbor] = dist[current] + cost
                    prev[neighbor] = current

            min_dist = None
            for vertex in unvisited:
                if min_dist == None or dist[vertex] < min_dist:
                    min_dist = dist[vertex]
                    current = vertex

            if current == end:
                 break

        assert current == end
        path = [end]
        while current != start:
            path.append(prev[current])
            current = prev[current]

        path.reverse()
        return path

    return dijkstra(graph, 0, no_frames)

def test():
    print("Test #1")
    tags = {('cat', 3, 9), ('dog', 5, 8), ('people', 0, 6)}
    no_frames = 9
    division = partition(tags, no_frames, penalty=3)
    assert division == [0, 3, 9]
    print("In: {('cat', 3, 9), ('dog', 5, 8), ('people', 0, 6)}")
    print("Out: [0, 3, 9]")
    
    print()
    print("Test #2")
    tags = {('cat', 0, 1), ('cat', 2, 4), ('cat', 6, 8), ('dog', 0, 3), ('dog', 6, 8), ('people', 0, 2), ('people', 4, 6)}
    no_frames = 8
    division = partition(tags, no_frames, penalty=3)
    assert division == [0, 2, 4, 6, 8]
    print("In: {('cat', 0, 1), ('cat', 2, 4), ('cat', 6, 8), ('dog', 0, 3), ('dog', 6, 8), ('people', 0, 2), ('people', 4, 6)}")
    print("Out: [0, 2, 4, 6, 8]")

    print()
    print("Test #3")
    tags = {('surfboard', 84, 86), ('boat', 30, 31), ('bird', 47, 52), ('boat', 9, 10), ('person', 43, 48), ('person', 52, 65), ('suitcase', 25, 26), ('suitcase', 69, 70), ('truck', 26, 27), ('bus', 23, 24), ('person', 66, 89), ('bird', 45, 46), ('bird', 53, 54), ('person', 0, 21), ('person', 29, 37), ('car', 38, 42), ('car', 21, 34), ('car', 14, 16), ('mouse', 19, 21), ('car', 61, 76), ('truck', 23, 24), ('car', 35, 36), ('bus', 26, 27), ('bird', 59, 60), ('boat', 27, 28), ('mouse', 15, 16), ('suitcase', 30, 31), ('bird', 38, 43), ('surfboard', 6, 8), ('person', 27, 28), ('suitcase', 33, 35), ('bird', 75, 83), ('cell phone', 79, 80), ('person', 39, 40), ('bird', 61, 70), ('boat', 15, 16), ('suitcase', 36, 37), ('mouse', 36, 38), ('person', 41, 42), ('person', 49, 50), ('mouse', 76, 78), ('car', 11, 12), ('surfboard', 79, 80), ('mouse', 13, 14), ('suitcase', 22, 24)}
    no_frames = 89
    division = partition(tags, no_frames, penalty=20)
    print(division)

if __name__ == "__main__":
    test()
