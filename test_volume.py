from modules.volume_controller import VolumeController
import time

volume = VolumeController()

print("Current Volume:", volume.get_volume())

print("Setting Volume to 20%")
volume.set_volume(20)

time.sleep(2)

print("Setting Volume to 80%")
volume.set_volume(80)

time.sleep(2)

print("Muting...")
volume.mute()

time.sleep(2)

print("Unmuting...")
volume.unmute()

print("Test Completed!")