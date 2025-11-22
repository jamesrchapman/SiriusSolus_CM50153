# switch_test.py
from gpiozero import Button
from time import time

switch = Button(18, pull_up=True, bounce_time=0.01)
print("Press/release the lever. Ctrl+C to exit.")

last = 0.0
while True:
    switch.wait_for_press()
    t = time()
    print(f"press  @ {t:.3f} Δ={t-last:.3f}s"); last = t
    switch.wait_for_release()
    t = time()
    print(f"release@ {t:.3f} Δ={t-last:.3f}s"); last = t
