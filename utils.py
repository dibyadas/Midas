import os
import moosegesture
import yaml
# moosegesture._MIN_STROKE_LEN = 100

with open('gesture_map.yml','r') as f:
    map_config = yaml.full_load(f)

gesture_map = map_config['gesture_map']
command_map = map_config['command_map']

tuple_gesture_keys = [eval(gesture) for gesture in gesture_map.keys()]

def execute_command(gesture):
    os.system(f"notify-send 'Confirmed... Executing - {gesture}'")
    os.system(f"{command_map[gesture]['command']} &")
    # print(f"{command_map[gesture_map[str(closest_match[0])]]['command']} &")
    # os.system('echo V &')

def sanitize_and_notify(timestamp_vals):
    sanitized_tuple_list = []
    count = 0
    for item in timestamp_vals.values():
        count += 1
        if len(item) == 2 and count == 2:
            sanitized_tuple_list.append(tuple(item))
            count = 0

    # print(sanitized_tuple_list)
    trim_beginning_len = 0.1*len(sanitized_tuple_list)
    # print(trim_beginning_len)
    # print(sanitized_tuple_list[int(trim_beginning_len):])
    detected_gesture = moosegesture.getGesture(sanitized_tuple_list[int(trim_beginning_len):])
    print(f'Gesture is :- {detected_gesture}')
    closest_match = moosegesture.findClosestMatchingGesture(
        detected_gesture, tuple_gesture_keys, maxDifference=4)
    # print(gesture_map[closest_match[0]])
    if closest_match is None:
        return None
    os.system(f"notify-send 'Gesture Detected :- {gesture_map[str(closest_match[0])]}'")
    return gesture_map[str(closest_match[0])]
    # if closest_match is not None:
    #     os.system(f"notify-send 'Gesture Detected :- {gesture_map[str(closest_match[0])]}'")
    #     # print(f"{command_map[gesture_map[str(closest_match[0])]]['command']} &")
    #     # os.system('echo V &')
    #     os.system(f"{command_map[gesture_map[str(closest_match[0])]]['command']} &")
    # else:
    #     print("No gesture detected")