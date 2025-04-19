from typing import Dict
import math

class CostCalculator:
    def __init__(
        self,
        loc: int,
        avg_salary: float,
        num_members: int,
        additional_hw_cost: float,
        eaf: float = 1.0,
        machine_cost: float = 55000,
        misc_cost: float = 10000,
        paid_sw_cost: float = 0
    ):
        self.loc = loc
        self.kloc = loc / 1000
        self.avg_salary = avg_salary
        self.num_members = num_members
        self.additional_hw_cost = additional_hw_cost
        self.eaf = eaf
        self.machine_cost = machine_cost
        self.misc_cost = misc_cost
        self.paid_sw_cost = paid_sw_cost
        # Semi-detached project constants
        self.a = 3.0
        self.b = 1.12
        self.c = 2.5
        self.d = 0.35

    def calculate_effort(self) -> float:
        """Calculate effort: E = a * (KLOC)^b * EAF"""
        try:
            effort = self.a * (self.kloc ** self.b) * self.eaf
            return round(effort, 2)
        except Exception as e:
            raise ValueError(f"Error calculating effort: {e}")

    def calculate_time(self, effort: float) -> float:
        """Calculate time: T = c * (E)^d"""
        try:
            time = self.c * (effort ** self.d)
            return round(time, 2)
        except Exception as e:
            raise ValueError(f"Error calculating time: {e}")

    def calculate_people(self, effort: float, time: float) -> int:
        """Calculate people: P = E / T"""
        try:
            if time == 0:
                raise ValueError("Time cannot be zero")
            people = math.ceil(effort / time)
            return people
        except Exception as e:
            raise ValueError(f"Error calculating people: {e}")

    def calculate_costs(self) -> Dict[str, float]:
        """Calculate all costs per Annexure-I"""
        try:
            effort = self.calculate_effort()
            time = self.calculate_time(effort)
            people = self.calculate_people(effort, time)

            # Developer cost: T * avg_salary * num_members
            developer_cost = time * self.avg_salary * self.num_members

            # System cost: machine_cost * num_members
            system_cost = self.machine_cost * self.num_members
            final_system_cost = (system_cost * 0.25) + self.additional_hw_cost  # 75% discount

            # Total cost
            total_cost = (
                developer_cost +
                final_system_cost +
                self.paid_sw_cost +
                self.misc_cost
            )

            return {
                "loc": self.loc,
                "kloc": round(self.kloc, 2),
                "effort": effort,
                "time": time,
                "people": people,
                "developer_cost": round(developer_cost, 2),
                "system_cost": round(system_cost, 2),
                "final_system_cost": round(final_system_cost, 2),
                "paid_sw_cost": self.paid_sw_cost,
                "misc_cost": self.misc_cost,
                "total_cost": round(total_cost, 2)
            }
        except Exception as e:
            raise ValueError(f"Error calculating costs: {e}")