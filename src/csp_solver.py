'''
Calendar Satisfaction Problem (CSP) Solver
Designed to make scheduling those meetings a breeze! Suite of tools
for efficiently scheduling some n meetings in a given datetime range
that abides by some number of constraints.

In this module:
- A solver that uses the backtracking exact solver approach
- Tools for pruning domains using node and arc consistency
'''
from collections import deque
from datetime import *
from date_constraints import *
from dataclasses import *
from copy import *


# CSP Backtracking Solver
# ---------------------------------------------------------------------------
# Function to solve the constraint satisfaction problem
def solve(n_meetings: int, date_range: Set[datetime], constraints: Set[DateConstraint]) -> Optional[List[datetime]]:
    # Initialize assignment and domains
    assignment: List[Optional[datetime]] = [None] * n_meetings
    domains: List[Set[datetime]] = [set(date_range) for _ in range(n_meetings)]

    # Apply node consistency and arc consistency to prune domains
    node_consistency(domains, constraints)
    arc_consistency(domains, constraints)

    # Perform recursive backtracking
    result: Optional[List[datetime]] = recursive_backtracker(
        assignment, list(range(n_meetings)), domains, constraints, depth=n_meetings
    )
    return result


# Recursive backtracking function
def recursive_backtracker(
        assignment: List[Optional[datetime]],
        variables: List[int],
        domains: List[Set[datetime]],
        constraints: Set[DateConstraint],
        depth: int
) -> Optional[List[datetime]]:
    # Base case: If all variables are assigned, return the assignment
    if all(assignment):
        return cast(List[datetime], assignment)  # cast to remove None values

    # Limit recursion depth to avoid out of bounds error
    if depth <= 0:
        return None

    # Select the next unassigned variable
    next_var: Optional[int] = cast(Optional[int], select_unassigned_variable(variables, assignment))

    if next_var is not None:
        # Iterate through the values in the domain of the selected variable
        for value in order_domain_values(domains[next_var]):
            # Assign the value to the variable
            assignment[next_var] = value

            # Check if the assignment is consistent with constraints
            if is_assignment_consistent(assignment, constraints):
                # Recursive call with reduced depth
                result: Optional[List[datetime]] = recursive_backtracker(
                    assignment, variables, domains, constraints, depth - 1
                )

                # Check if the result is not a failure
                if result:
                    return result

            # If we get here, the assignment failed, so backtrack
            assignment[next_var] = None

    # If we get here, all values in the domain failed, so backtrack
    return None


# Function to select the next unassigned variable
def select_unassigned_variable(variables: List[int], assignment: List[Optional[datetime]]) -> int:
    # Find unassigned variables
    unassigned_variables: List[int] = [var for var in variables if assignment[var] is None]

    # Check if all variables are assigned
    if not unassigned_variables:
        raise ValueError("All variables are assigned")

    # Return the first unassigned variable
    return unassigned_variables[0]


# Function to order domain values (convert set to list)
def order_domain_values(domain: Set[datetime]) -> List[datetime]:
    return list(domain)


# Function to check if the current assignment is consistent with constraints
def is_assignment_consistent(assignment: List[Optional[datetime]], constraints: Set[DateConstraint]) -> bool:
    for constraint in constraints:
        # Check if the constraint is satisfied by the current assignment
        if not constraint.is_satisfied_by_assignment(assignment):
            return False
    return True


# Function to apply node consistency to prune domains
def node_consistency(domains: List[Set[datetime]], constraints: Set[DateConstraint]) -> None:
    for constraint in constraints:
        # Check if the constraint is unary
        if constraint.arity() == 1:
            # For unary constraints, prune the domain based on constraint satisfaction
            meeting_index: int = constraint.L_VAL
            domain: Set[datetime] = domains[meeting_index]
            new_domain: Set[datetime] = set()

            for value in domain:
                # Check if the value satisfies the unary constraint
                if constraint.is_satisfied_by_values(value):
                    new_domain.add(value)

            # Update the domain with the pruned values
            domains[meeting_index] = new_domain


class Arc:
    def __init__(self, constraint: DateConstraint):
        self.CONSTRAINT: DateConstraint = constraint
        self.TAIL: int = constraint.L_VAL
        self.HEAD: Optional[int] = constraint.R_VAL if constraint.arity() == 2 else None

    def __eq__(self, other: Any) -> bool:
        if other is None:
            return False
        if not isinstance(other, Arc):
            return False
        return self.CONSTRAINT == other.CONSTRAINT and self.TAIL == other.TAIL and self.HEAD == other.HEAD

    def __hash__(self) -> int:
        return hash((self.CONSTRAINT, self.TAIL, self.HEAD))

    def __str__(self) -> str:
        return f"Arc[{self.CONSTRAINT}, ({self.TAIL} -> {self.HEAD})]"

    def __repr__(self) -> str:
        return self.__str__()


# Function to initialize arcs based on constraints
def initialize_arcs(constraints: Set[DateConstraint]) -> Set[Arc]:
    arcs: Set[Arc] = set()
    for constraint in constraints:
        # If the constraint has arity 2, add arcs in both directions
        if constraint.arity() == 2:
            arcs.add(Arc(constraint))
            arcs.add(Arc(constraint.get_reverse()))
        else:
            # If the constraint has arity 1, add a single arc
            arcs.add(Arc(constraint))
    return arcs


# Function to enforce arc consistency on domains
def arc_consistency(domains: List[Set[datetime]], constraints: Set[DateConstraint]) -> None:
    # Initialize a set of arcs based on constraints
    arc_set: Set[Arc] = initialize_arcs(constraints)

    # Continue until the set of arcs is not empty
    while arc_set:
        # Pop an arc from the set
        curr_arc: Arc = arc_set.pop()

        # Remove inconsistent values and update the set of arcs
        if remove_inconsistent_values(domains, curr_arc):
            for arc in get_arcs_related_to_tail(curr_arc, constraints):
                arc_set.add(arc)


# Function to remove inconsistent values from the tail of the arc
def remove_inconsistent_values(domains: List[Set[datetime]], curr_arc: Arc) -> bool:
    removed: bool = False
    for tail_val in set(domains[curr_arc.TAIL]):
        # Check if there is no satisfying head value for the tail value
        if not exists_satisfying_head_value(tail_val, curr_arc, domains):
            # Remove the inconsistent value from the domain
            domains[curr_arc.TAIL].remove(tail_val)
            removed = True

    return removed


# Function to check if there exists a satisfying head value for the tail value in the given arc
def exists_satisfying_head_value(tail_val: datetime, curr_arc: Arc, domains: List[Set[datetime]]) -> bool:
    if curr_arc.HEAD is not None:
        # Check if there exists a satisfying head value in the domain
        for head_val in domains[curr_arc.HEAD]:
            if curr_arc.CONSTRAINT.is_satisfied_by_values(tail_val, head_val):
                return True
    elif curr_arc.HEAD is None:
        # For unary arcs, check if the tail value satisfies the constraint
        return curr_arc.CONSTRAINT.is_satisfied_by_values(tail_val)

    return False


# Function to get arcs related to the tail of the given arc
def get_arcs_related_to_tail(curr_arc: Arc, constraints: Set[DateConstraint]) -> List[Arc]:
    return [Arc(constraint) for constraint in constraints if constraint.L_VAL == curr_arc.HEAD]