from .serial import Keyboard

# Gets the bottom right coordinate of bounding box of a cluster of keys
def max_x_y(keys: list) -> float:
    max_x: float = -1
    max_y: float = -1

    for key in keys:
        if (key.x + key.width) > max_x:
            max_x = key.x + key.width
        if (key.y + key.height) > max_y:
            max_y = key.y + key.height

    return max_x, max_y

# Gets the top left coordinate of bounding box of a cluster of keys
def min_x_y(keys: list) -> float:
    min_x, min_y = max_x_y(keys)

    for key in keys:
        if key.x < min_x:
            min_x = key.x
        if key.y < min_y:
            min_y = key.y

    return min_x, min_y

def read_file(path: str):
    with open(path, 'r', encoding='utf-8') as file:
        return file.read()

def write_file(path: str, content:str):
    with open(path, 'w', encoding='utf-8') as file:
        return file.write(content)

def sort_keys_kle_placer(keys):
    keys.sort(key=lambda k: ((k.rotation_angle + 360) % 360, k.rotation_x, k.rotation_y, k.y, (k.x + k.width / 2)))

def check_multilayout_keys(kbd: Keyboard) -> bool:
    keys = []
    for key in kbd.keys:
        if key.labels[3].isnumeric() and key.labels[5].isnumeric():
            keys.append(key)
    return keys
