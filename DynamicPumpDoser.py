import numpy as np
from collections import defaultdict

class InsulinDoseTrainer:

    def get_rate(self, glucose_history):
        if len(glucose_history) >= 2:
            return (glucose_history[-1] - glucose_history[-2]) * 60
        else:
            return 0
    def __init__(self, duration_minutes):
        self.actions = np.array([0.0, 0.02, 0.05, 0.1, 0.5, 1.0])
        self.reward_table = defaultdict(float)
        self.count_table = defaultdict(int)
        self.policy = self._initialize_policy()
        self.min_trials = 20
        self.glucose = 200
        self.minutes_since_last_meal = 1000

        self.insulin_kernel = self._make_insulin_kernel()
        self.food_kernel = self._make_food_kernel()
        self.insulin_effects = np.zeros(duration_minutes + len(self.insulin_kernel))
        self.food_effects = np.zeros(duration_minutes + len(self.food_kernel))
        self.sensitivity = 0.0001

    def _initialize_policy(self):
        policy = {}
        for glucose_bin in ["low", "target", "high", "very_high"]:
            for rate_bin in ["dropping_fast", "dropping", "stable", "rising", "rising_fast"]:
                for time_from_meal_bin in ["early", "mid", "late", "none"]:
                    for insulin_on_board_bin in ["none", "low", "moderate", "high"]:
                        state = (glucose_bin, rate_bin, time_from_meal_bin, insulin_on_board_bin)
                        policy[state] = np.random.choice(self.actions)
        return policy

    def _make_insulin_kernel(self):
        kernel = np.zeros(8 * 60)
        peak_idx = int(3.5 * 60)
        for i in range(len(kernel)):
            if i <= peak_idx:
                kernel[i] = i / peak_idx
            else:
                kernel[i] = max(0, (8 * 60 - i) / (8 * 60 - peak_idx))
        return kernel

    def _make_food_kernel(self):
        kernel = np.zeros(5 * 60)
        peak_idx = int(1.5 * 60)
        for i in range(len(kernel)):
            if i <= peak_idx:
                kernel[i] = i / peak_idx
            else:
                kernel[i] = max(0, (5 * 60 - i) / (5 * 60 - peak_idx))
        return kernel

    def bin_glucose(self, g):
        if g < 80:
            return "low"
        elif g < 140:
            return "target"
        elif g < 250:
            return "high"
        else:
            return "very_high"

    def bin_rate(self, r):
        if r < -2:
            return "dropping_fast"
        elif r < -0.5:
            return "dropping"
        elif r < 0.5:
            return "stable"
        elif r < 2:
            return "rising"
        else:
            return "rising_fast"

    def bin_time_from_meal(self, minutes_since_meal):
        if minutes_since_meal < 60:
            return "early"
        elif minutes_since_meal < 180:
            return "mid"
        elif minutes_since_meal < 360:
            return "late"
        else:
            return "none"

    def bin_insulin_on_board(self, iob):
        if iob < 0.1:
            return "none"
        elif iob < 0.5:
            return "low"
        elif iob < 1.5:
            return "moderate"
        else:
            return "high"

    def record_outcome(self, state, action, reward):
        self.reward_table[(state, action)] += reward
        self.count_table[(state, action)] += 1

    def update_policy(self):
        for state in self.policy:
            unexplored = [a for a in self.actions if self.count_table[(state, a)] < self.min_trials]
            if unexplored:
                self.policy[state] = np.random.choice(unexplored)
                continue

            best_action = None
            best_reward = -np.inf
            for action in self.actions:
                if self.count_table[(state, action)] > 0:
                    avg_reward = self.reward_table[(state, action)] / self.count_table[(state, action)]
                    if avg_reward > best_reward:
                        best_reward = avg_reward
                        best_action = action
            if best_action is not None:
                self.policy[state] = best_action

    def print_policy_with_rewards(self):
        print("Final Best Policy Table:")
        for state in sorted(self.policy.keys()):
            best_action = None
            best_reward = -np.inf
            for action in self.actions:
                key = (state, action)
                if self.count_table[key] > 0:
                    avg_reward = self.reward_table[key] / self.count_table[key]
                    if avg_reward > best_reward:
                        best_reward = avg_reward
                        best_action = action
            if best_action is not None:
                print(f"State {state}: Best Action {best_action:.2f}, Avg Reward {best_reward:.2f}")
            else:
                print(f"State {state}: No data")

    def simulate_minute(self, rate, t):
        self.minutes_since_last_meal += 1

        glucose_bin = self.bin_glucose(self.glucose)
        rate_bin = self.bin_rate(rate)
        time_from_meal_bin = self.bin_time_from_meal(self.minutes_since_last_meal)
        iob_bin = self.bin_insulin_on_board(np.sum(self.insulin_effects[t:t+len(self.insulin_kernel)]))

        state = (glucose_bin, rate_bin, time_from_meal_bin, iob_bin)
        action = self.policy[state]

        end_ins = min(t + len(self.insulin_kernel), len(self.insulin_effects))
        self.insulin_effects[t:end_ins] += action * self.insulin_kernel[:end_ins - t]

        if t % (12 * 60) == 0:
            end_food = min(t + len(self.food_kernel), len(self.food_effects))
            self.food_effects[t:end_food] += 100 * self.food_kernel[:end_food - t]
            self.minutes_since_last_meal = 0

        active_insulin_concentration = self.insulin_effects[t]
        insulin_rate = -active_insulin_concentration * self.glucose * self.sensitivity
        food_rate = self.food_effects[t]

        self.glucose += insulin_rate + food_rate / 60

        reward = -abs(self.glucose - 100)
        self.record_outcome(state, action, reward)

if __name__ == "__main__":
    duration_minutes = 24 * 60 * 10
    trainer = InsulinDoseTrainer(duration_minutes)

    glucose_history = [trainer.glucose]

    for t in range(1, duration_minutes):
        rate = trainer.get_rate(glucose_history)

        trainer.simulate_minute(rate, t)
        glucose_history.append(trainer.glucose)

    trainer.update_policy()
    trainer.print_policy_with_rewards()
