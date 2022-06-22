from copy import deepcopy
from dataclasses import dataclass
from typing import List

from .kle_placer_utils import Key, Keyboard, KeyboardMetadata, UB_LABEL_MAP, sort_keys

@dataclass
class DeserializeCluster:
    x: float = 0.
    y: float = 0.

class _ReorderLabelsIn:
    def __init__(self):
        # Map from serialized label position to normalized position,
        # depending on the alignment flags.
        self.LABEL_MAP = [
            # 0  1  2  3  4  5  6  7  8  9 10 11      align flags
            [ 0, 6, 2, 8, 9,11, 3, 5, 1, 4, 7,10],  # 0 = no centering              # noqa
            [ 1, 7,-1,-1, 9,11, 4,-1,-1,-1,-1,10],  # 1 = center x                  # noqa
            [ 3,-1, 5,-1, 9,11,-1,-1, 4,-1,-1,10],  # 2 = center y                  # noqa
            [ 4,-1,-1,-1, 9,11,-1,-1,-1,-1,-1,10],  # 3 = center x & y              # noqa
            [ 0, 6, 2, 8,10,-1, 3, 5, 1, 4, 7,-1],  # 4 = center front (default)    # noqa
            [ 1, 7,-1,-1,10,-1, 4,-1,-1,-1,-1,-1],  # 5 = center front & x          # noqa
            [ 3,-1, 5,-1,10,-1,-1,-1, 4,-1,-1,-1],  # 6 = center front & y          # noqa
            [ 4,-1,-1,-1,10,-1,-1,-1,-1,-1,-1,-1],  # 7 = center front & x & y      # noqa
        ]

    def __call__(self, labels: List, align: int) -> List:
        ret: List = ["", ] * UB_LABEL_MAP
        for i, lbl in enumerate(labels):
            if lbl:
                lm: int = self.LABEL_MAP[align][i]
                if lm == -1:
                    continue
                ret[lm] = lbl
        return ret

reorder_labels_in = _ReorderLabelsIn()

def deserialize(rows: List) -> Keyboard:  # noqa: C901
    def _deserialize_error(msg: str, data):
        import json5
        raise ValueError("Error: " + msg + ":\n  " + json5.dumps(data) if data is not None else "")

    if not isinstance(rows, List):
        _deserialize_error("expected an array of objects", rows)

    # Initialize with defaults
    current = deepcopy(Key())
    kbd = Keyboard()
    cluster = DeserializeCluster()
    align: int = 4

    for r, rows_r in enumerate(rows):
        if isinstance(rows_r, list):
            for k, item in enumerate(rows_r):
                if isinstance(item, str):
                    new_key: Key = deepcopy(current)

                    # Calculate some generated values
                    new_key.width2 = current.width if new_key.width2 == 0. else current.width2
                    new_key.height2 = current.height if new_key.height2 == 0. else current.height2
                    new_key.labels = reorder_labels_in(item.split("\n"), align)
                    new_key.textSize = [
                        (int(x) if x.isdecimal() else None) if isinstance(x, str) else x for x in reorder_labels_in(new_key.textSize, align)]

                    # Add the key!
                    kbd.keys.append(new_key)

                    # Set up for the next key
                    current.x += current.width
                    current.width = current.height = 1.
                    current.x2 = current.y2 = current.width2 = current.height2 = 0.
                    current.nub = current.stepped = current.decal = False
                else:
                    if k != 0 and any(item.get(v) is not None for v in ['r', 'rx', 'ry']):
                        _deserialize_error("rotation can only be specified on the first key in a row", item)

                    if item.get('g') is not None:
                        current.ghost = bool(item['g'])
                    if item.get('a') is not None:
                        align = item['a']
                    if item.get('f'):
                        current.default.textSize = int(item['f'])
                        current.textSize = [None, ] * UB_LABEL_MAP
                    if item.get('f2'):
                        for i in range(1, UB_LABEL_MAP):
                            current.textSize[i] = int(item['f2'])
                    if item.get('t'):
                        split = item['t'].split("\n")
                        if len(split[0]) > 0:
                            current.default.textColor = split[0]
                        current.textColor = reorder_labels_in(split, align)
                    if item.get('rx') is not None:
                        cluster.x = float(item['rx'])
                        current.rotation_x = cluster.x
                        current.x = cluster.x
                        current.y = cluster.y
                    if item.get('ry') is not None:
                        cluster.y = float(item['ry'])
                        current.rotation_y = cluster.y
                        current.x = cluster.x
                        current.y = cluster.y

                    current.x += item.get('x', 0.)
                    current.y += item.get('y', 0.)

                    for item_key, attr, c in [
                        ('fa', 'textSize', lambda x: x),
                        ('p', 'profile', str),
                        ('c', 'color', str),
                        ('x2', 'x2', float),
                        ('y2', 'y2', float),
                        ('n', 'nub', bool),
                        ('l', 'stepped', bool),
                        ('d', 'decal', bool),
                        ('sm', 'sm', str),
                        ('sb', 'sb', str),
                        ('st', 'st', str),
                    ]:
                        v = item.get(item_key)
                        if v:
                            setattr(current, attr, c(v))
                    for item_key, attr in [
                        ('r', 'rotation_angle'),
                        ('w', 'width'),
                        ('w', 'width2'),
                        ('h', 'height'),
                        ('h', 'height2'),
                        ('w2', 'width2'),
                        ('h2', 'height2'),
                    ]:
                        v = item.get(item_key)
                        if v is not None:
                            setattr(current, attr, float(v))

            # End of the row
            current.y += 1
            current.x = current.rotation_x
        elif isinstance(rows_r, dict):
            if r != 0:
                _deserialize_error("keyboard metadata must the be first element", rows_r)
            for prop in vars(KeyboardMetadata).keys():
                if prop in rows_r:
                    setattr(kbd.meta, prop, rows_r[prop])
        else:
            _deserialize_error("unexpected", rows_r)

    sort_keys(kbd.keys)
    
    return kbd


def parse(json: str) -> Keyboard:
    import json5
    return deserialize(json5.loads(json))
