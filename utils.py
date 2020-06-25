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
    os.system(f"{command_map[gesture]['command']} &")

def sanitize_and_notify(coord_set):
    timestamp_vals = {}
    for _, x_event in coord_set:
        if x_event is not None:
            timestamp_vals[f'{x_event.timestamp()}'] = [x_event.value]
    for y_event, _ in coord_set:
        try:
            if y_event is not None:
                try:
                    timestamp_vals[f'{y_event.timestamp()}'][1] = y_event.value
                except IndexError:
                    timestamp_vals[f'{y_event.timestamp()}'].append(y_event.value)
        except KeyError:
            pass

    sanitized_tuple_list = []
    count = 0
    for item in timestamp_vals.values():
        count += 1
        if len(item) == 2:
            sanitized_tuple_list.append(tuple(item))
            count = 0

    trim_beginning_len = 0.1*len(sanitized_tuple_list)
    
    detected_gesture = moosegesture.getGesture(sanitized_tuple_list[int(trim_beginning_len):])
    # print(f'Gesture is :- {detected_gesture}')
    closest_match = moosegesture.findClosestMatchingGesture(
        detected_gesture, tuple_gesture_keys, maxDifference=4)
    
    if closest_match is None:
        return None
    os.system(f"notify-send 'Gesture Detected :- {gesture_map[str(closest_match[0])]}'")
    return gesture_map[str(closest_match[0])]
