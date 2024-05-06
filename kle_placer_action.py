from typing import Dict
import pcbnew
from pcbnew import BOARD, FOOTPRINT, VECTOR2I, wxPoint, EDA_ANGLE

import wx
import os
import sys
import json
import logging
from copy import deepcopy
from math import sin, cos, radians, sqrt, atan, degrees

from .serial import deserialize, Keyboard
from .util import read_file, sort_keys_kle_placer, min_x_y, check_multilayout_keys


class KeyAutoPlaceDialog(wx.Dialog):
    def __init__(self, parent, title, caption):
        style = wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        super(KeyAutoPlaceDialog, self).__init__(parent, -1, 'KLE Placer', style=style)

        # File select
        layout_select_box = wx.BoxSizer(wx.HORIZONTAL)

        text = wx.StaticText(self, -1, "Select KLE json file:")
        layout_select_box.Add(text, 0, wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, 5)

        layout_file_picker = wx.FilePickerCtrl(self, -1)
        layout_select_box.Add(layout_file_picker, 1, wx.EXPAND|wx.ALL, 5)

        # Key format
        key_format_box = wx.BoxSizer(wx.HORIZONTAL)

        key_annotation_label = wx.StaticText(self, -1, "Key Annotation format string:")
        key_format_box.Add(key_annotation_label, 1, wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, 5)

        key_annotation_format = wx.TextCtrl(self, value='SW{}')
        key_format_box.Add(key_annotation_format, 1, wx.EXPAND|wx.ALL, 5)

        # Key spacing
        key_spacing_box = wx.BoxSizer(wx.HORIZONTAL)

        spacing_annotation_label = wx.StaticText(self, -1, "Key spacing")
        key_spacing_box.Add(spacing_annotation_label, 1, wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, 5)

        spacing_control = wx.Choice(self, choices=["MX", "Choc"])
        spacing_control.SetSelection(0)
        key_spacing_box.Add(spacing_control, 1, wx.EXPAND|wx.ALL, 5)

        # Stab format
        stab_format_box = wx.BoxSizer(wx.HORIZONTAL)

        stabilizer_annotation_label = wx.StaticText(self, -1, "Stabillizer Annotation format string:")
        stab_format_box.Add(stabilizer_annotation_label, 1, wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, 5)

        stabilizer_annotation_format = wx.TextCtrl(self, value='S{}')
        stab_format_box.Add(stabilizer_annotation_format, 1, wx.EXPAND|wx.ALL, 5)

        # Diode format
        diode_format_box = wx.BoxSizer(wx.HORIZONTAL)

        diodeAnnotationLabel = wx.StaticText(self, -1, "Diode Annotation format string:")
        diode_format_box.Add(diodeAnnotationLabel, 1, wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, 5)

        diode_annotation_format = wx.TextCtrl(self, value='D{}')
        diode_format_box.Add(diode_annotation_format, 1, wx.EXPAND|wx.ALL, 5)

        # Diode bool
        move_diodes_box = wx.BoxSizer(wx.HORIZONTAL)

        move_diodes_bool = wx.CheckBox(self, label="Move Diodes")
        move_diodes_bool.SetValue(True)
        move_diodes_box.Add(move_diodes_bool, 1, wx.EXPAND|wx.ALL, 5)

        # Relative diode mode
        relative_diode_box = wx.BoxSizer(wx.HORIZONTAL)

        relative_diode_bool = wx.CheckBox(self, label="Move diodes based on the first switch and diode (Won't do anything if move diodes is disabled)")
        relative_diode_bool.SetValue(True)
        relative_diode_box.Add(relative_diode_bool, 1, wx.EXPAND|wx.ALL, 5)

        # Rotation mode
        specific_ref_box = wx.BoxSizer(wx.HORIZONTAL)

        specific_ref_mode = wx.CheckBox(self, label="Specific Reference Mode. Required for rotated keys. See documentation.")
        specific_ref_mode.SetValue(False)
        specific_ref_box.Add(specific_ref_mode, 1, wx.EXPAND|wx.ALL, 5)

        # Final setup of box
        box = wx.BoxSizer(wx.VERTICAL)

        box.Add(layout_select_box, 0, wx.EXPAND|wx.ALL, 5)
        box.Add(key_format_box, 0, wx.EXPAND|wx.ALL, 5)
        box.Add(key_spacing_box, 0, wx.EXPAND|wx.ALL, 5)
        box.Add(stab_format_box, 0, wx.EXPAND|wx.ALL, 5)
        box.Add(diode_format_box, 0, wx.EXPAND|wx.ALL, 5)
        box.Add(move_diodes_box, 0, wx.EXPAND|wx.ALL, 5)
        box.Add(relative_diode_box, 0, wx.EXPAND|wx.ALL, 5)
        box.Add(specific_ref_box, 0, wx.EXPAND|wx.ALL, 5)

        buttons = self.CreateButtonSizer(wx.OK|wx.CANCEL)
        box.Add(buttons, 0, wx.EXPAND|wx.ALL, 5)

        self.SetSizerAndFit(box)
        self.layout_file_picker = layout_file_picker
        self.key_annotation_format = key_annotation_format
        self.key_spacing = spacing_control
        self.stabilizer_annotation_format = stabilizer_annotation_format
        self.diode_annotation_format = diode_annotation_format
        self.move_diodes_bool = move_diodes_bool
        self.relative_diode_bool = relative_diode_bool
        self.specific_ref_mode = specific_ref_mode

    def get_layout_path(self):
        return self.layout_file_picker.GetPath()

    def get_key_annotation_format(self):
        return self.key_annotation_format.GetValue()

    def get_key_spacing(self):
        return self.key_spacing.GetStringSelection()

    def get_stabilizer_annotation_format(self):
        return self.stabilizer_annotation_format.GetValue()

    def get_diode_annotation_format(self):
        return self.diode_annotation_format.GetValue()

    def get_move_diodes_bool(self):
        return self.move_diodes_bool.GetValue()

    def get_relative_diode_bool(self):
        return self.relative_diode_bool.GetValue()

    def get_specific_ref_mode_bool(self):
        return self.specific_ref_mode.GetValue()


class BoardModifier():
    def __init__(self, logger, board: BOARD):
        self.logger = logger
        self.board: BOARD = board

    def mm_to_nm(self, v):
        return int(v * 1000000)

    def nm_to_mm(self, v):
        return v / 1000000.0

    def get_footprint(self, reference, required=True) -> FOOTPRINT:
        self.logger.info("Searching for {} footprint".format(reference))
        footprint = self.board.FindFootprintByReference(reference)
        if footprint is None and required:
            self.logger.error("Footprint not found")
            raise Exception("Cannot find footprint {}".format(reference))
        return footprint

    def set_position(self, footprint: FOOTPRINT, position: wxPoint):
        self.logger.info("Setting {} footprint position: {}".format(footprint.GetReference(), position))
        footprint.SetPosition(VECTOR2I(int(position.x), int(position.y)))

    def set_relative_position_mm(self, footprint, referencePoint, direction):
        position = pcbnew.wxPoint(referencePoint.x + pcbnew.FromMM(direction[0]), referencePoint.y + pcbnew.FromMM(direction[1]))
        self.set_position(footprint, position)

    def rotate(self, footprint: FOOTPRINT, rotationReference, angle):
        self.logger.info("Rotating {} footprint: rotationReference: {}, rotationAngle: {}".format(footprint.GetReference(), rotationReference, angle))
        footprint.Rotate(VECTOR2I(int(rotationReference.x), int(rotationReference.y)), EDA_ANGLE(angle*-1, pcbnew.DEGREES_T))


class KeyPlacer(BoardModifier):
    def __init__(self, logger, board: BOARD, layout, spacing: str):
        super().__init__(logger, board)
        self.layout: Keyboard = layout
        self.key_distance = pcbnew.FromMM(19.05)
        self.current_key = 1
        self.current_diode = 1
        self.reference_coordinate = pcbnew.wxPoint(pcbnew.FromMM(25), pcbnew.FromMM(25))

        self.key_spacing = self._get_spacing(spacing)

    def _get_spacing(self, spacing: str) -> Dict[str, float]:
        if spacing == "MX":
            return {"vertical": pcbnew.FromMM(19.05), "horizontal": pcbnew.FromMM(19.05)}
        else:
            return {"vertical": pcbnew.FromMM(17.0), "horizontal": pcbnew.FromMM(18.0)}

    def get_current_key(self, key_format, stabilizer_format):
        key = self.get_footprint(key_format.format(self.current_key))

        # in case of perigoso/keyswitch-kicad-library, stabilizer holes are not part of of switch footprint and needs to be handled
        # separately, check if there is stabilizer with id matching current key and return it
        # stabilizer will be None if not found
        stabilizer = self.get_footprint(stabilizer_format.format(self.current_key), required=False)
        self.current_key += 1

        return key, stabilizer

    # def get_current_diode(self, diode_format):
    #     diode = self.get_footprint(diode_format.format(self.current_diode))
    #     self.current_diode += 1
    #     return diode

    def squish_kbd_multilayout(self):
        kbd = deepcopy(self.layout)
        self.logger.info(kbd.keys)
        ml_keys = check_multilayout_keys(kbd)

        # This list will replace kbd.keys later
        # It is a list with only the keys to be included in the info.json
        temp_layout = []
        # Add non-multilayout keys to the list for now
        for key in [k for k in kbd.keys if k not in ml_keys]:
            temp_layout.append(key)

        # Generate a dict of all multilayouts
        # E.g. Used to test and figure out the multilayout value with the maximum amount of keys
        ml_dict = {}
        for key in [k for k in kbd.keys if k in ml_keys]:
            ml_ndx = int(key.labels[3])
            ml_val = int(key.labels[5])

            # Create dict with multilayout index if it doesn't exist
            if not ml_ndx in ml_dict.keys():
                ml_dict[ml_ndx] = {}

            # Create dict with multilayout value if it doesn't exist
            # Also create list of keys if it doesn't exist
            if not ml_val in ml_dict[ml_ndx].keys():
                ml_dict[ml_ndx][ml_val] = []

            # Add key to dict if not in already
            if not key in ml_dict[ml_ndx][ml_val]:
                ml_dict[ml_ndx][ml_val].append(key)

        # Iterate over multilayout keys
        for key in [k for k in kbd.keys if k in ml_keys]:
            # WIP: Be able to configure this
            ml_ndx = int(key.labels[3])
            ml_val = int(key.labels[5])

            # list of all amount of keys over all val options
            ml_val_length_list = [len(ml_dict[ml_ndx][i]) for i in ml_dict[ml_ndx].keys() if isinstance(i, int)]
            max_val_len = max(ml_val_length_list) # maximum amount of keys over all val options
            current_val_len = len(ml_dict[ml_ndx][ml_val]) # amount of keys in current val

            current_is_max = max_val_len == current_val_len

            # If all multilayout values/options have the same amount of keys
            all_same_length = len(set(ml_val_length_list)) == 1

            if not "max" in ml_dict[ml_ndx].keys():
                if all_same_length:
                    ml_dict[ml_ndx]["max"] = 0 # Use the default
                elif current_is_max:
                    ml_dict[ml_ndx]["max"] = ml_val

            # If the current multilayout value/option isn't default,
            if ml_val > 0:
                # Check if there is an offsets dict
                if not "offsets" in ml_dict[ml_ndx].keys():
                    ml_dict[ml_ndx]["offsets"] = {}

                # Check if the offset for this multilayout value has been calculated yet.
                if not ml_val in ml_dict[ml_ndx]["offsets"].keys():
                    # If not, calculate and set the offset
                    xmin, ymin = min_x_y(ml_dict[ml_ndx][0])
                    x, y = min_x_y(ml_dict[ml_ndx][ml_val])

                    ml_x_offset = xmin - x
                    ml_y_offset = ymin - y

                    ml_dict[ml_ndx]["offsets"][ml_val] = (ml_x_offset, ml_y_offset)
                else:
                    # If so, just get the offset from ml_dict
                    ml_x_offset, ml_y_offset = ml_dict[ml_ndx]["offsets"][ml_val]

                # Offset the x and y values
                key.x += ml_x_offset
                key.y += ml_y_offset

            # (For multilayouts) make sure there isn't any of the same overlapping keys
            if not any([ (key.x + (key.width/2) == a.x + (a.width/2) and key.y + (key.height/2) == a.y + (a.height/2)) for a in temp_layout]):
                # Add the key to the final list
                temp_layout.append(key)

        # Offset all the remaining keys (align against the top left)
        x_offset, y_offset = min_x_y(temp_layout)
        for key in temp_layout:
            key.x -= x_offset
            key.y -= y_offset

            if key.rotation_angle:
                key.rotation_x -= x_offset
                key.rotation_y -= y_offset

        # Override primary layout with temporary layout
        self.layout.keys = temp_layout

        # Sort keys based on the centers of each key (by default it sorts with the top left corner)
        sort_keys_kle_placer(self.layout.keys)

    def Run(self, key_format, stabilizer_format, diode_format, move_diodes, relative_diode_mode, rotation_mode):

        ### First, check all the multilayouts and squish all the same multilayouts into the same position on top of one another. ###

        self.squish_kbd_multilayout()

        # Check for violations of KLE guidelines
        if any([not key.labels[4].isdigit() for key in self.layout.keys]) and rotation_mode:
            raise Exception("You need to provide a reference for every switch (label 4) if using rotation mode!")

        if any([key.rotation_angle != 0 for key in self.layout.keys]) and not rotation_mode:
            raise Exception("You must enable rotation mode if there are any rotated keys!")

        ### Now begin the placement of all keys based on new layout. ###

        # Get information about the first key
        first_key = self.get_footprint(key_format.format(1))
        if rotation_mode: # Sort layout by reference if using specific reference mode
            def check(key):
                return int(key.labels[4])
            self.layout.keys.sort(key=lambda x:check(x))
            # if first key is already rotated as it should be upon running the code, use maths to get the reference point, accounting for rotation:
            if self.layout.keys[0].rotation_angle != 0 and (first_key.GetOrientationDegrees() + self.layout.keys[0].rotation_angle) in [0, 90, 180, -90]:
                r = self.layout.keys[0].rotation_angle
                w = self.layout.keys[0].width
                h = self.layout.keys[0].height
                rx = self.layout.keys[0].rotation_x
                ry = self.layout.keys[0].rotation_y

                u = self.key_distance
                pos = first_key.GetPosition()

                lx = w/2
                ly = h/2
                l = sqrt( pow(lx, 2) + pow(ly, 2) ) * u
                theta = degrees(atan(ly/lx))
                alpha = 180 - ( 90 + r + theta )
                self.logger.info("l {}".format(l))
                self.logger.info("theta {}".format(theta))
                self.logger.info("alpha {}".format(alpha))

                dif_x = sin(radians(alpha)) * l
                dif_y = cos(radians(alpha)) * l
                self.logger.info("dif_x {}".format(dif_x))
                self.logger.info("dif_y {}".format(dif_y))

                x = pos.x
                y = pos.y
                self.logger.info("x {}".format(x))
                self.logger.info("y {}".format(y))

                xc = x - dif_x - rx * u
                yc = y - dif_y - ry * u
                self.logger.info("xc {}".format(xc))
                self.logger.info("yc {}".format(yc))

                top_left = pcbnew.wxPoint(xc , yc)
                first_key_pos = top_left

                # self.set_position(first_key,  pcbnew.wxPoint(xc, yc))
            else:
                first_key_pos = pcbnew.wxPoint((first_key.GetPosition().x) - ((self.key_spacing['horizontal'] * self.layout.keys[0].x) + (self.key_spacing['horizontal'] * self.layout.keys[0].width // 2)),
                                               (first_key.GetPosition().y) - ((self.key_spacing['vertical'] * self.layout.keys[0].y) + (self.key_spacing['vertical'] * self.layout.keys[0].height // 2)))
        else:
            first_key_pos = pcbnew.wxPoint((first_key.GetPosition().x) - ((self.key_spacing['horizontal'] * self.layout.keys[0].x) + (self.key_spacing['horizontal'] * self.layout.keys[0].width // 2)),
                                           (first_key.GetPosition().y) - ((self.key_spacing['vertical'] * self.layout.keys[0].y) + (self.key_spacing['vertical'] * self.layout.keys[0].height // 2)))

        self.logger.info("first_key_pos {}".format(first_key_pos))
        first_key_rotation = first_key.GetOrientationDegrees()

        # Set the origin/reference as the first key
        self.reference_coordinate = first_key_pos

        # Set the default rotation to that of the first key's
        first_key_already_rotated = False
        if first_key_rotation != 0 and (first_key_rotation + self.layout.keys[0].rotation_angle) in [0, 90, 180, -90]:
            default_key_rotation = first_key_rotation + self.layout.keys[0].rotation_angle
            first_key_already_rotated = True
        else:
            default_key_rotation = first_key_rotation
        self.logger.info("default_key_rotation {}".format(default_key_rotation))

        # Get information about the first diode
        first_diode = self.get_footprint(diode_format.format(1), required=False) or None

        # Make sure there is a first diode if relative diode is enabled
        if not first_diode and relative_diode_mode:
            raise Exception("First key requires a diode!")

        # DEFAULTS
        diode_offset_x = 0 # mm
        diode_offset_y = 0 # mm

        if relative_diode_mode:
            # if first key is already rotated as it should be upon running the code, use maths to get the proper diode offset, accounting for rotation:
            if rotation_mode and self.layout.keys[0].rotation_angle != 0 and (first_key.GetOrientationDegrees() + self.layout.keys[0].rotation_angle) in [0, 90, 180, -90]:
                mx = abs(first_diode.GetPosition().x - first_key.GetPosition().x)
                my = abs(first_diode.GetPosition().y - first_key.GetPosition().y)
                ml = sqrt(pow(mx, 2) + pow(my, 2))
                beta = degrees(atan(my/mx))
                z = 90 - beta - r  # r from earlier
                self.logger.info("mx {}".format(mx))
                self.logger.info("my {}".format(my))
                self.logger.info("ml {}".format(ml))
                self.logger.info("beta {}".format(beta))
                self.logger.info("z {}".format(z))

                ox = sin(radians(z)) * ml
                oy = cos(radians(z)) * ml
                self.logger.info("ox {}".format(ox))
                self.logger.info("oy {}".format(oy))

                diode_offset_x = self.nm_to_mm(ox)
                diode_offset_y = self.nm_to_mm(oy)
            else:
                diode_offset_x = self.nm_to_mm(first_diode.GetPosition().x - first_key.GetPosition().x)
                diode_offset_y = self.nm_to_mm(first_diode.GetPosition().y - first_key.GetPosition().y)

        first_diode_rotation = first_diode.GetOrientationDegrees()
        if first_key_already_rotated:
            first_diode_rotation += self.layout.keys[0].rotation_angle

        # Set the default diode rotation to that of the first diode's
        default_diode_rotation = first_diode_rotation

        # Start placement of keys
        for key in self.layout.keys:
            if rotation_mode:
                current_ref = int(key.labels[4]) # Already checked for violations earlier
                # if current_ref == 1:
                #     continue
                self.current_key = current_ref

            # Get the diode, switch and stabilizer footprints
            diode_footprint = self.get_footprint(diode_format.format(self.current_key), required=False) or None
            switch_footprint, stabilizer = self.get_current_key(key_format, stabilizer_format)

            # Extra individual switch rotations i.e. extra rotation compared to the first switch's rotation e.g. for south/north facing switches
            extra_switch_rotation = 0
            if key.labels[10].isdigit():
                extra_switch_rotation = int(key.labels[10])

            # Whether or not to flip the stablizer footprint
            flip_stabilizer = False
            if key.labels[9].lower() == 'f':
                flip_stabilizer = True

            # Shortcuts
            width = key.width
            height = key.height
            angle = key.rotation_angle

            # Calculate position on board
            position = pcbnew.wxPoint((self.key_spacing['horizontal'] * key.x) + (self.key_spacing['horizontal'] * width // 2),
                                      (self.key_spacing['vertical'] * key.y) + (self.key_spacing['vertical'] * height // 2)) + self.reference_coordinate

            # Move switch footprint
            self.set_position(switch_footprint, position)

            # Set rotation of switch to the same as the first one, then rotate extra based if needed
            switch_footprint.SetOrientationDegrees(default_key_rotation)
            if extra_switch_rotation:
                self.rotate(switch_footprint, switch_footprint.GetPosition(), extra_switch_rotation)

            # Move (and rotate) diode if it exists, and Move Diode is enabled
            if diode_footprint and move_diodes:
                self.set_relative_position_mm(diode_footprint, position, [diode_offset_x, diode_offset_y])
                diode_footprint.SetOrientationDegrees(default_diode_rotation)
                self.rotate(diode_footprint, switch_footprint.GetPosition(), extra_switch_rotation)

            # Move stabilizer if it exists
            if stabilizer:
                stabilizer.SetOrientationDegrees(0)
                self.set_position(stabilizer, position)

                if flip_stabilizer:
                    stabilizer.SetOrientationDegrees(180)

            # For angled keys (should only apply when rotation mode is enabled)
            if angle != 0:
                rotation_reference = pcbnew.wxPoint((self.key_spacing['horizontal'] * key.rotation_x), (self.key_spacing['vertical'] * key.rotation_y)) + self.reference_coordinate
                self.logger.info("rotation_reference {}".format(rotation_reference))
                self.rotate(switch_footprint, rotation_reference, angle)

                if diode_footprint and move_diodes:
                    self.rotate(diode_footprint, rotation_reference, angle)

                if stabilizer:
                    self.rotate(stabilizer, rotation_reference, angle)


class KLEPlacerAction(pcbnew.ActionPlugin):
    def defaults(self):
        self.name = "KLE Placer"
        self.category = "Utility"
        self.description = "Places switches down in a kicad project based on "
        self.show_toolbar_button = True # Optional, defaults to False
        # self.icon_file_name = os.path.join(os.path.dirname(__file__), 'icon.png') # Optional

    def Initialize(self):
        self.board = pcbnew.GetBoard()

        # go to the project folder - so that log will be in proper place
        os.chdir(os.path.dirname(os.path.abspath(self.board.GetFileName())))

        # Remove all handlers associated with the root logger object.
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)

        # set up logger
        logging.basicConfig(level=logging.DEBUG,
                            filename="keyautoplace.log",
                            filemode='w',
                            format='%(asctime)s %(name)s %(lineno)d: %(message)s',
                            datefmt='%H:%M:%S')
        self.logger = logging.getLogger(__name__)
        self.logger.info("Plugin executed with python version: " + repr(sys.version))

    def Run(self):
        self.Initialize()

        pcbFrame = [x for x in wx.GetTopLevelWindows() if x.GetName() == 'PcbFrame'][0]

        dlg = KeyAutoPlaceDialog(pcbFrame, 'Title', 'Caption')
        if dlg.ShowModal() == wx.ID_OK:

            layout_path = dlg.get_layout_path()
            if layout_path:
                self.layout = deserialize(json.loads(read_file(layout_path)))

                self.logger.info("User layout: {}".format(self.layout))
                placer = KeyPlacer(self.logger, self.board, self.layout, dlg.get_key_spacing())
                placer.Run(dlg.get_key_annotation_format(), dlg.get_stabilizer_annotation_format(), dlg.get_diode_annotation_format(
                ), dlg.get_move_diodes_bool(), dlg.get_relative_diode_bool(), dlg.get_specific_ref_mode_bool())

        dlg.Destroy()
        logging.shutdown()
