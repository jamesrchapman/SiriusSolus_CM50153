# Plan C: Baseline insulin + predictive meal bolus adjustment
# Goal: Simulate fixed baseline insulin with additional predictive boluses

import numpy as np
import matplotlib.pyplot as plt

class PlanCInsulinSim:
    def __init__(self, duration_hours=48, step_minutes=1):
        self.duration = duration_hours * 60  # in minutes
        self.dt = step_minutes
        self.time = np.arange(0, self.duration, self.dt)
        self.BGL = np.zeros_like(self.time, dtype=float)
        self.insulin_effect = np.zeros_like(self.time, dtype=float)
        self.food_effect = np.zeros_like(self.time, dtype=float)
        self.basal_rate = 0.01  # units/minute
        self.predicted_meal_times = [8*60, 20*60]  # 8 AM and 8 PM
        self.predicted_meal_sizes = [250, 250]  # calories (glucose equivalent)
        self.weight = 10  # kg (arbitrary for glucose scaling)
        self.k1 = 0.5  # insulin glucose uptake coefficient
        self.k2 = 0.8  # digestion rate glucose release coefficient
        self.meal_duration = 300  # minutes (5 hours)
        self.insulin_duration = 480  # minutes (8 hours)

    def triangle_kernel(self, peak_idx, duration):
        kernel = np.zeros_like(self.time)
        start = max(0, peak_idx - duration // 2)
        end = min(len(self.time), peak_idx + duration // 2)
        for i in range(start, end):
            dist = abs(i - peak_idx)
            kernel[i] = max(0, 1 - dist / (duration / 2))
        return kernel

    def simulate(self):
        bg = 200.0
        for t in range(len(self.time)):
            # Baseline insulin delivery
            self.insulin_effect[t] += self.basal_rate

            # Predictive meal bolus (3.5 hours before meal)
            for meal_time in self.predicted_meal_times:
                print("hu")
                if t == int(meal_time - 210):  # 3.5 hours before
                    kernel = self.triangle_kernel(t, self.insulin_duration)
                    self.insulin_effect += kernel * 0.5  # predictive bolus
                if t == meal_time:
                    food_kernel = self.triangle_kernel(t, self.meal_duration)
                    self.food_effect += food_kernel * self.predicted_meal_sizes[0]

            digestion_rate = self.food_effect[t] / self.weight
            insulin_rate = -self.insulin_effect[t] * self.k1 * bg / self.weight
            bgl_rate = digestion_rate * self.k2 + insulin_rate
            bg += bgl_rate * self.dt / 60.0
            self.BGL[t] = bg

    def plot(self):
        plt.plot(self.time / 60, self.BGL)
        plt.xlabel("Time (hours)")
        plt.ylabel("Blood Glucose Level (mg/dl)")
        plt.title("Plan C: Predictive Baseline and Meal Bolus Glucose Curve")
        plt.grid(True)
        plt.ylim(0, 450)
        plt.show()

if __name__ == '__main__':
    sim = PlanCInsulinSim()
    sim.simulate()
    sim.plot()
