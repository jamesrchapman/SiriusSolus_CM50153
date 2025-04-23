"""
Look, how about we just make a simple update every 1 minute model: 

We want 

insulin effect - has a curve, that triangle with peaks
insulin sensitivity (doesn't change much, maybe high glucose means worse sensitivity but let's omit that for now)
insulin dose - scales the insulin effect curve I think. 
Bolus Frequency
glucose (mg/dl)
glucose rate(mg/dl/hr)
digestion glucose uptake rate (mg/hr)

weight (doesn't really change)
meal calories (rough for glucose uptake)

so let each loop be 1 minute, calculate glucose rate and calculate the next glucose value based on the current one and the rate and collect the bgl and add it to a list
then we'll plot that at the end. okay? 
digestion glucose uptake rate = meal_size*digestion_curve/weight
insulin uptake rate = -insulin_effect_curve*insulin_sensitivity*insulin_dose/weight
bgl_rate =  insulin uptake rate + digestion glucose uptake rate



"""

import numpy as np
import matplotlib.pyplot as plt

# Simulation constants
duration_minutes = 72 * 60  # simulate 72 hours
dt = 1  # timestep in minutes
steps = int(duration_minutes / dt)
time = np.arange(0, duration_minutes) / 60  # time in hours for plotting

# Parameters
weight = 10  # kg
insulin_sensitivity = 50  # mg/dL per unit insulin
daily_expected_insulin = weight
bolus_frequency = 96  # number of insulin doses per day
# insulin_dose = daily_expected_insulin / bolus_frequency  # units per bolus
meal_size = weight * 50 / 2  # calories per meal
meals_per_day = 2
initial_glucose = 300  # mg/dL

# Triangle kernel function
def triangle_kernel(length, peak_position):
    kernel = np.zeros(length)
    for i in range(length):
        if i < peak_position:
            kernel[i] = i / peak_position
        else:
            kernel[i] = max(0, 1 - (i - peak_position) / (length - peak_position))
    return kernel

# Insulin and digestion effect kernels (in minutes)
insulin_effect_minutes = 480  # 8 hours
digestion_minutes = 180  # 3 hours
insulin_kernel = triangle_kernel(insulin_effect_minutes, int(240))
digestion_kernel = triangle_kernel(digestion_minutes, int(60))

# Generate bolus and meal times
bolus_interval = int(24 * 60 / bolus_frequency)
meal_times = [8 * 60, 20 * 60]  # 8 AM and 8 PM each day

insulin_effect = np.zeros(steps)
digestion_effect = np.zeros(steps)


# Schedule meals
for day in range(int(duration_minutes / (24 * 60))):
    for meal_minute in meal_times:
        t = day * 24 * 60 + meal_minute
        if t < steps:
            end = min(t + digestion_minutes, steps)
            digestion_effect[t:end] += digestion_kernel[:end - t]

# Run simulation
glucose = np.zeros(steps)
glucose[0] = initial_glucose
bgl_rate = [initial_glucose]
insulin_dose_history = []




# # Schedule insulin boluses
# for t in range(0, steps, bolus_interval):
#     end = min(t + insulin_effect_minutes, steps)
#     insulin_effect[t:end] += insulin_kernel[:end - t]

def calculate_insulin_dose(glucose, bgl_rate):
	insulin_dose = daily_expected_insulin / bolus_frequency
	return insulin_dose


for t in range(1, steps):
    insulin_uptake = -insulin_effect[t] * insulin_sensitivity / weight
    if t % bolus_interval == 0:
    	end = min(t + insulin_effect_minutes, steps)
    	insulin_dose = calculate_insulin_dose(glucose,bgl_rate)
    	insulin_effect[t:end] += insulin_kernel[:end - t]*insulin_dose
    insulin_dose_history.append(0)
    digestion_uptake = digestion_effect[t] * meal_size / weight * 3 # 3 is just a constant I picked for a reasonable jump
    bgl_rate.append(insulin_uptake + digestion_uptake)
    glucose[t] = glucose[t - 1] + (bgl_rate[-1] / 60)  # convert to per-minute rate






# Plot result
plt.figure(figsize=(14, 6))
plt.plot(time, glucose, label='Blood Glucose (mg/dL)', linewidth=2)
plt.plot(time, bgl_rate, label='Blood Glucose Rate (mg/dL/hr)', linewidth=1)
plt.axhline(80, color='red', linestyle='--', label='Hypoglycemia Threshold')
plt.axhline(140, color='green', linestyle='--', label='Target Range Start')
plt.title('Blood Glucose Simulation Over 72 Hours (1-min Resolution)')
plt.xlabel('Time (hours)')
plt.ylabel('Blood Glucose (mg/dL)')
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()
