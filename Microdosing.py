import numpy as np
import matplotlib.pyplot as plt

# Time in hours (0 to 24, in 5-minute intervals)
time = np.linspace(0, 24, 24 * 12 + 1)  # 5-minute resolution

def insulin_effect_kernel(t, onset=1, peak=4, duration=8):
    """
    Simple triangular insulin effect model:
    Starts at `onset`, peaks at `peak`, ends at `onset` + `duration`.
    """
    if t < onset or t > onset + duration:
        return 0
    elif t <= peak:
        return (t - onset) / (peak - onset)
    else:
        return (onset + duration - t) / (onset + duration - peak)

# Vectorize the kernel
vectorized_kernel = np.vectorize(insulin_effect_kernel)

# Baseline huge dose (e.g. 1.0 unit) given at 7am and 7pm
dose_times = [7, 19]
huge_dose_profile = np.zeros_like(time)
for dt in dose_times:
    huge_dose_profile += vectorized_kernel(time - dt)

# Spread-out microbolus strategy (e.g. 96 microdoses across 24 hours)
micro_dose_times = np.linspace(0, 24, 96)
micro_dose_profile = np.zeros_like(time)
for md in micro_dose_times:
    micro_dose_profile += vectorized_kernel(time - md) * (1 / len(micro_dose_times))  # scaled total dose = 1

# Define the insulin effect kernel more realistically over time
def full_kernel_curve(onset=1, peak=4, duration=8, resolution=5):
    """
    Generate the full effect curve over time, sampled at given resolution (minutes).
    Returns the time vector and the corresponding effect values.
    """
    t = np.linspace(0, onset + duration, int((onset + duration) * 60 / resolution))
    effect = np.array([insulin_effect_kernel(x, onset=onset, peak=peak, duration=duration) for x in t])
    return t, effect

# Get the kernel curve (in hours, 5-minute resolution)
kernel_time, kernel_effect = full_kernel_curve()

# Apply 96 microdoses across the day with proper convolution
micro_dose_profile_fixed = np.zeros_like(time)
dose_per_micro = 1 / len(micro_dose_times)  # total dose still 1 unit

for md in micro_dose_times:
    # Add the kernel effect scaled by the microdose at the appropriate time offset
    start_idx = np.searchsorted(time, md)
    end_idx = start_idx + len(kernel_effect)
    if end_idx > len(time):
        end_idx = len(time)
        kernel_segment = kernel_effect[:end_idx - start_idx]
    else:
        kernel_segment = kernel_effect
    micro_dose_profile_fixed[start_idx:end_idx] += dose_per_micro * kernel_segment

# Apply convolution to the 2 large doses as well, using the same kernel
large_dose_profile_fixed = np.zeros_like(time)
dose_per_large = 0.5  # total dose 1.0u, split across two injections

for dt in dose_times:
    start_idx = np.searchsorted(time, dt)
    end_idx = start_idx + len(kernel_effect)
    if end_idx > len(time):
        end_idx = len(time)
        kernel_segment = kernel_effect[:end_idx - start_idx]
    else:
        kernel_segment = kernel_effect
    large_dose_profile_fixed[start_idx:end_idx] += dose_per_large * kernel_segment

# Plot the convolved version of both dosing strategies
plt.figure(figsize=(12, 6))
plt.plot(time, large_dose_profile_fixed, label='2 Large Doses w/ Convolved Kernel (1.0u total)', linewidth=2)
plt.plot(time, micro_dose_profile_fixed, label='96 Microdoses w/ Convolved Kernel (1.0u total)', linewidth=2, linestyle='--')
plt.title('Insulin Activity: Convolved Large Doses vs. Microdosing')
plt.xlabel('Time (hours)')
plt.ylabel('Relative Insulin Effect')
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()
