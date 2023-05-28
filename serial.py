import json
from copy import deepcopy

from dataclasses import dataclass, field as dcf
from typing import Optional, List, Callable

@dataclass
class KeyDefault:
    text_color: str = "#000000"
    text_size: int = 3

def _default_factory_list_factory(s: int) -> Callable:
    def list_factory() -> List:
        return [None for i in range(s)]
    return list_factory

def _dcf_list() -> List:
    return dcf(default_factory=list)

@dataclass
class Key:
    color: str = "#cccccc"
    labels: List[str] = _dcf_list()
    text_color: List[Optional[str]] = _dcf_list()
    text_size: List[Optional[int]] = _dcf_list()
    default: KeyDefault = dcf(default_factory=KeyDefault)
    x: float = 0.
    y: float = 0.
    width: float = 1.
    height: float = 1.
    x2: float = 0.
    y2: float = 0.
    width2: float = 1.
    height2: float = 1.
    rotation_x: float = 0.
    rotation_y: float = 0.
    rotation_angle: float = 0.
    decal: bool = False
    ghost: bool = False
    stepped: bool = False
    nub: bool = False
    profile: str = ""
    sm: str = ""  # switch mount
    sb: str = ""  # switch brand
    st: str = ""  # switch type

class TempKey:
    def __init__(self, align:int):
        self.align = align
        self.labels: list = ["", ] * 12
        self.text_color: list = ["", ] * 12
        self.text_size: list = []

@dataclass
class KeyboardMetadataBackground:
    name: str
    style: str

@dataclass
class KeyboardMetadata:
    backcolor: str = "#eeeeee"
    name: str = ""
    author: str = ""
    notes: str = ""
    background: Optional[KeyboardMetadataBackground] = None
    radii: str = ""
    switchMount: str = ""
    switchBrand: str = ""
    switchType: str = ""
    plate: bool = False
    pcb: bool = False

@dataclass
class Keyboard:
    meta: KeyboardMetadata = dcf(default_factory=KeyboardMetadata)
    keys: List[Key] = _dcf_list()

def get_ndx(lst: list, ndx: int):
    """Gets the object at index `ndx` if it is a valid index, otherwise returns `None`.
    Used to replicate JavaScript behaviour.
    """
    try:
        return lst[ndx]
    except IndexError:
        return None

def set_ndx(lst: list, ndx: int, obj: object, filler=None) -> list: 
    """Sets the index `ndx` in a list to any object `obj`,
    filling the empty spaces with `filler` (`None` by default) if the length of 
    the list is smaller than `ndx`. Used to replicate JavaScript behaviour.
    """
    try:
        lst[ndx] = obj
        return lst
    except IndexError:
        dct = {}
        dct[ndx] = obj
        for i in range(0, max(ndx+1, len(lst))):
            if i == ndx:
                continue
            try:
                dct[i] = lst[i]
            except IndexError:
                dct[i] = filler
        while len(lst) < len(dct.keys()):
            lst.append(filler)
        for i, key in enumerate(dct.keys()):
            lst[i] = (dct[i])

def is_empty_object(o):
    for prop in o:
        return False
    return True

# Map from serialized label position to normalized position,
# depending on the alignment flags.
LABEL_MAP = [
    # 0  1  2  3  4  5  6  7  8  9 10 11      align flags
    [ 0, 6, 2, 8, 9,11, 3, 5, 1, 4, 7,10],  # 0 = no centering          
    [ 1, 7,-1,-1, 9,11, 4,-1,-1,-1,-1,10],  # 1 = center x              
    [ 3,-1, 5,-1, 9,11,-1,-1, 4,-1,-1,10],  # 2 = center y              
    [ 4,-1,-1,-1, 9,11,-1,-1,-1,-1,-1,10],  # 3 = center x & y          
    [ 0, 6, 2, 8,10,-1, 3, 5, 1, 4, 7,-1],  # 4 = center front (default)
    [ 1, 7,-1,-1,10,-1, 4,-1,-1,-1,-1,-1],  # 5 = center front & x      
    [ 3,-1, 5,-1,10,-1,-1,-1, 4,-1,-1,-1],  # 6 = center front & y      
    [ 4,-1,-1,-1,10,-1,-1,-1,-1,-1,-1,-1],  # 7 = center front & x & y  
]

DISALLOWED_ALIGNMENT_FOR_LABELS = [
    [1,2,3,5,6,7],	#0
    [2,3,6,7],		#1
    [1,2,3,5,6,7],	#2
    [1,3,5,7],		#3
    [],				#4
    [1,3,5,7],		#5
    [1,2,3,5,6,7],	#6
    [2,3,6,7],		#7
    [1,2,3,5,6,7],	#8
    [4,5,6,7],		#9
    [],				#10
    [4,5,6,7]		#11
]

def sort_keys(keys):
    keys.sort(key=lambda k: ((k.rotation_angle + 360) % 360, k.rotation_x, k.rotation_y, k.y, k.x))

def reorder_labels(key, current):
    # Possible alignment flags in order of preference (this is fairly
    # arbitrary, but hoped to reduce raw data size).
    align = [7, 5, 6, 4, 3, 1, 2, 0]

    # remove impossible flag combinations
    for i in range(len(key.labels)):
        if key.labels[i]:
            align = [a for a in align if a not in DISALLOWED_ALIGNMENT_FOR_LABELS[i]]

    # For the chosen alignment, generate the label array in the correct order
    ret = TempKey(align[0])
    for i in range(0, 12):
        if i in LABEL_MAP[ret.align]:
            ndx = (LABEL_MAP[ret.align]).index(i)
        else:
            ndx = -1
        if ndx >= 0:
            if get_ndx(key.labels, i):
                set_ndx(ret.labels, ndx, key.labels[i])
            if get_ndx(key.text_color, i):
                set_ndx(ret.text_color, ndx, key.text_color[i])
            if get_ndx(key.text_size, i):
                set_ndx(ret.text_size, ndx, key.text_size[i])
    # Clean up
    for i in range(len(ret.text_size)):
        if not ret.labels[i]:
            set_ndx(ret.text_size, i, get_ndx(current.text_size, i))
        if not ret.text_size[i] or ret.text_size[i] == key.default.text_size:
            set_ndx(ret.text_size, i, 0)
    return ret

def compare_text_sizes(current, key, labels):
    if type(current) == int:
        current = [current]
    for i in range(12):
        if labels[i] and (bool(get_ndx(current, i)) != bool(get_ndx(key, i)) or (get_ndx(current, i) and get_ndx(current, i) != get_ndx(key, i))):
            return False
    return True

def serialize_prop(props, nname, val, defval):
    if val != defval:
        props[nname] = val
    return val

def serialize(keyboard):
    keys = keyboard.keys
    rows = []
    row = []
    current = deepcopy(Key())
    current.text_color = current.default.text_color
    current.align = 4
    cluster = {'r': 0, 'rx': 0, 'ry': 0}

    # Serialize metadata
    meta: dict = {}
    for property in vars(keyboard.meta).keys():
        if getattr(keyboard.meta, property) != vars(KeyboardMetadata)[property]:
            meta[property] = getattr(keyboard.meta, property)
    if meta:
        rows.append(meta)

    new_row = True
    current.y -= 1  # will be incremented on first row

    # Serialize row/key-data
    sort_keys(keys)
    for key in keys:
        props: dict = {}
        ordered: TempKey = reorder_labels(key, current)

        # start a new row when necessary
        cluster_changed = (key.rotation_angle != cluster['r'] or key.rotation_x != cluster['rx'] or key.rotation_y != cluster['ry'])
        row_changed = (key.y != current.y)
        if row and (row_changed or cluster_changed):
            # Push the old row
            rows.append(row)
            row = []
            new_row = True

        if new_row:
            # Set up for the new row
            current.y += 1

            # 'y' is reset if *either* 'rx' or 'ry' are changed
            if key.rotation_y != cluster['ry'] or key.rotation_x != cluster['rx']:
                current.y = key.rotation_y
            current.x = key.rotation_x  # always reset x to rx (which defaults to zero)

            # Update current cluster
            cluster['r'] = key.rotation_angle
            cluster['rx'] = key.rotation_x
            cluster['ry'] = key.rotation_y

            new_row = False
        
        current.rotation_angle = serialize_prop(props, "r", key.rotation_angle, current.rotation_angle)
        current.rotation_x = serialize_prop(props, "rx", key.rotation_x, current.rotation_x)
        current.rotation_y = serialize_prop(props, "ry", key.rotation_y, current.rotation_y)
        current.y += serialize_prop(props, "y", key.y - current.y, 0)
        current.x += serialize_prop(props, "x", key.x - current.x, 0) + key.width
        current.color = serialize_prop(props, "c", key.color, current.color)
        if not ordered.text_color[0]:
            ordered.text_color[0] = key.default.text_color
        else:
            for i in range(2, 12):
                if not ordered.text_color[i] and ordered.text_color[i] is not ordered.text_color[0]:
                    ordered.text_color[i] is not key.default.text_color
        
        current.text_color = serialize_prop(props, "t", "\n".join(ordered.text_color).rstrip(), current.text_color)
        current.ghost = serialize_prop(props, "g", key.ghost, current.ghost)
        current.profile = serialize_prop(props, "p", key.profile, current.profile)
        current.sm = serialize_prop(props, "sm", key.sm, current.sm)
        current.sb = serialize_prop(props, "sb", key.sb, current.sb)
        current.st = serialize_prop(props, "st", key.st, current.st)
        current.align = serialize_prop(props, "a", ordered.align, current.align)
        current.default.text_size = serialize_prop(props, "f", key.default.text_size, current.default.text_size)
        if props.get('f'):
            current.text_size = []
        if not compare_text_sizes(current.text_size, ordered.text_size, ordered.labels):
            if len(ordered.text_size) == 0:
                serialize_prop(props, "f", key.default.text_size, -1) # Force 'f' to be written
            else:
                optimizeF2 = not ordered.text_size[0]
                for i in range(2, len(ordered.text_size)):
                    optimizeF2 = optimizeF2 and (ordered.text_size[i] == ordered.text_size[1])
                if optimizeF2:
                    f2 = ordered.text_size[1]
                    current.f2 = serialize_prop(props, "f2", f2, -1)
                    current.text_size = [0,f2,f2,f2,f2,f2,f2,f2,f2,f2,f2,f2]
                else:
                    current.f2 = None
                    current.text_size = serialize_prop(props, "fa", ordered.text_size, [])
        
        serialize_prop(props, "w", key.width, 1)
        serialize_prop(props, "h", key.height, 1)
        serialize_prop(props, "w2", key.width2, key.width)
        serialize_prop(props, "h2", key.height2, key.height)
        serialize_prop(props, "x2", key.x2, 0)
        serialize_prop(props, "y2", key.y2, 0)
        serialize_prop(props, "n", key.nub or False, False)
        serialize_prop(props, "l", key.stepped or False, False)
        serialize_prop(props, "d", key.decal or False, False)
        if not is_empty_object(props):
            row.append(props)
        current.labels = ordered.labels
        row.append('\n'.join(ordered.labels).rstrip())

    if len(row) > 0:
        rows.append(row)

    return rows

def deserialize_error(msg, data):
    raise ValueError("Error: " + msg + ":\n  " + json.dumps(data) if data is not None else "")

def reorder_labels_in(labels, align, filler=None, skipdefault=False):
    if filler is not None:
        ret = [filler, ] * 12 # Mainly for key labels
    else:
        ret = []
    for i in range(1, len(labels)) if skipdefault else range(len(labels)):
        lm = LABEL_MAP[align][i]
        if lm == -1:
            continue
        lbl = labels[i]
        set_ndx(ret, lm, lbl)
    return ret

def deserialize(rows):
    # Initialize with defaults
    current = deepcopy(Key())
    meta = deepcopy(KeyboardMetadata())
    keys = []
    cluster = { "x": 0, "y": 0 }
    align = 4
    for r, rows_r in enumerate(rows):
        if isinstance(rows_r, list):
            for k, item in enumerate(rows_r):
                key = item
                if isinstance(key, str):
                    new_key = deepcopy(current)
                    new_key.width2 = new_key.width2 if new_key.width2 != 0 else current.width
                    new_key.height2 = new_key.height2 if new_key.height2 != 0 else current.height
                    new_key.labels = reorder_labels_in(key.split("\n"), align, "")
                    new_key.text_size = reorder_labels_in(new_key.text_size, align)

                    for i in range(12):
                        if not get_ndx(new_key.labels, i):
                            set_ndx(new_key.text_size, i, None)
                            set_ndx(new_key.text_color, i, None)
                        if get_ndx(new_key.text_size, i) == new_key.default.text_size:
                            set_ndx(new_key.text_size, i, None)
                        if get_ndx(new_key.text_color, i) == new_key.default.text_color:
                            set_ndx(new_key.text_color, i, None)

                    keys.append(new_key)

                    current.x += current.width
                    current.width = current.height = 1
                    current.x2 = current.y2 = current.width2 = current.height2 = 0
                    current.nub = current.stepped = current.decal = False

                else:
                    if item.get('r') != None:
                        if k != 0:
                            deserialize_error("'r' can only be used on the first key in a row", item)
                        current.rotation_angle = item.get('r')
                    if item.get('rx') != None:
                        if k != 0:
                            deserialize_error("'rx' can only be used on the first key in a row", item)
                        cluster["x"] = float(item['rx'])
                        current.rotation_x = cluster["x"]
                        current.x = cluster["x"]
                        current.y = cluster["y"]
                    if item.get('ry') != None:
                        if k != 0:
                            deserialize_error("'ry' can only be used on the first key in a row", item)
                        cluster["y"] = float(item['ry'])
                        current.rotation_y = cluster["y"]
                        current.x = cluster["x"]
                        current.y = cluster["y"]
                    if item.get('a') != None:
                        align = item.get('a')
                    if item.get('f'):
                        current.default.text_size = item.get('f')
                        current.text_size = []
                    if item.get('f2'):
                        for i in range(1, 12):
                            set_ndx(current.text_size, i, item.get('f2'))
                    if item.get('fa'):
                        current.text_size = item.get('fa')
                    if item.get('p'):
                        current.profile = item.get('p')
                    if item.get('c'):
                        current.color = item.get('c')
                    if item.get('t'):
                        split = item.get('t').split('\n')
                        current.default.text_color = split[0]
                        current.text_color = reorder_labels_in(split, align)
                    if item.get('x'):
                        current.x += item.get('x')
                    if item.get('y'):
                        current.y += item.get('y')
                    if item.get('w'):
                        current.width = current.width2 = item.get('w')
                    if item.get('h'):
                        current.height = current.height2 = item.get('h')
                    if item.get('x2'):
                        current.x2 = item.get('x2')
                    if item.get('y2'):
                        current.y2 = item.get('y2')
                    if item.get('w2'):
                        current.width2 = item.get('w2')
                    if item.get('h2'):
                        current.height2 = item.get('h2')
                    if item.get('n'):
                        current.nub = item.get('n')
                    if item.get('l'):
                        current.stepped = item.get('l')
                    if item.get('d'):
                        current.decal = item.get('d')
                    if item.get('g') != None:
                        current.ghost = item.get('g')
                    if item.get('sm'):
                        current.sm = item.get('sm')
                    if item.get('sb'):
                        current.sb = item.get('sb')
                    if item.get('st'):
                        current.st = item.get('st')
            # End of the row
            current.y += 1
        elif isinstance(rows_r, dict):
            if r != 0:
                deserialize_error("keyboard metadata must the be first element", rows_r)
            for prop in vars(KeyboardMetadata).keys():
                if prop in rows_r:
                    setattr(meta, prop, rows_r[prop])
        current.x = current.rotation_x

    return Keyboard(meta, keys)
