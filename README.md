## Midas - Touchpad gesture detection utility

------

Midas is gesture detection program written in Python that runs in the background silently tracking touchpad for gestures and executes the corresponding commands according to the mapping defined. 

The gesture mapping is defined as directions mapped to commands in the `gesture_map.yml` file. 

Here's what it might look like

```yaml
gesture_map:
	('DR', 'UR'): 'V'
  	('UR', 'DR'): 'inverted_V'
command_map:
	V:
	  command: 'xfce4-terminal'
	inverted_V:
	  command: 'googlechrome'
```

The running process need not be restarted whenever the above file is re-written as it reloaded every time the gesture detection starts. To trigger the detection, tap & hold the extreme top right corner of the touchpad for 0.3s until a notification appears. The mouse pointer is grabbed and no longer responds because the bg process is processing all the input. Draw the gesture and you see a notif saying what gesture has been detected. To confirm it's execution tap and the touchpad within a sec of the notif appearing. If not, the gesture is refreshed. To stop the detection, tap & hold the same extreme corner for 0.3s until the notif appears. Here's a GIF showing how it works.

The code needs more documentation and refactoring and is open for PRs and issues. Cheers :beers: !

It is written in Python 3.7 and uses extensively uses asyncio library. It has a low memory and CPU footprint.