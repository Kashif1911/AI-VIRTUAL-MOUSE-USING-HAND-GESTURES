from modules.brightness_controller import BrightnessController
import time

brightness = BrightnessController()

print("Current Brightness:", brightness.get_brightness())

print("Setting Brightness to 30%")
brightness.set_brightness(30)
time.sleep(2)

print("Setting Brightness to 80%")
brightness.set_brightness(80)
time.sleep(2)

print("Increasing")
brightness.increase()
time.sleep(2)

print("Decreasing")
brightness.decrease()

print("Test Completed!")