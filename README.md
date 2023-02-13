# KiCAD KLE Placer
A plugin for KiCAD used to place switches based on a KLE. Tested (and should work) in KiCAD 6. Based on [kicad-kbplacer](https://github.com/adamws/kicad-kbplacer).

NOTE:
- ~~Rotated keys in KLE are NOT SUPPORTED (I'm working on it, read at the bottom of the page)~~ Rotated keys requires you to enable the [Specific Reference mode](https://github.com/zykrah/kicad-kle-placer#specific-reference-mode-and-rotated-keys).
- ~~Diode placement is NOT SUPPORTED (I'm working on it)~~ DONE. Read below.
- Plugin is not fully tested, the more complex layouts you try with it, the less likely it is to work fully. Please open issues for any unintended behaviour.
- I tested this plugin with [marbastlib](https://github.com/ebastler/marbastlib) (symbols and footprints).


# Installation
Download the github code and place it into `C:\Users\<user>\Documents\KiCad\7.0\scripting\plugins\kicad-kle-placer` (or wherever your plugins folder is located):

![image](https://user-images.githubusercontent.com/23428162/175076873-44e1a3c8-77f8-4e67-b2b9-29ffcd3559e7.png)

You can then refresh your plugins and it should show up (you can also find a shortcut to the plugins folder here):

![image](https://user-images.githubusercontent.com/23428162/175077103-d6da1715-4924-4cf6-aa6d-9c0848566184.png)

What the dialog looks like:

![image](https://user-images.githubusercontent.com/23428162/175812246-eb44a86b-b6de-445c-b713-ac16aee70f52.png)


# Usage
**Initial note: There should be the SAME number of footprints/symbols (in your KiCAD project) as there are keys (in the KLE).**

The script takes in the `json` file of a KLE, downloaded as shown:

![image](https://user-images.githubusercontent.com/23428162/168476867-7477de1c-a342-41e8-b515-0a1d21b097b8.png)

Follow the following KLE guidelines to enable more advanced functionality of the plugin:


## KLE Guidelines
![image](https://user-images.githubusercontent.com/23428162/168476640-09a4b226-8364-4fc1-833d-9fd1efac6a04.png)
- 3:  Multilayout index
- 4:  The reference number **REQUIRED FOR SPECIFIC REFERENCE MODE AND ANGLED KEYS** (e.g. if this key corresponds to `SW1`, put `1` in this label)
- 5:  Multilayout value
- 9:  Stabilizer flip (if you want to flip the stabilizer, place `F` in this label)
- 10: Extra switch rotation in degrees (e.g. if the default orientation is north facing switches, and you wanted specific keys to be south facing, put `180` in this label)


## Order of keys in KLE/Schematic (Normal mode)
By default ("normal mode"), the plugin counts by footprint reference (i.e. `SW1`, `SW2`, etc...) starting from the top left-most key. It then goes left to right (based on the horizontal center of the key), then up to down (based on the top edge of the key).

Example of how it's ordered:

![image](https://user-images.githubusercontent.com/23428162/175812480-e5c02a3e-674a-4918-89fc-3b888d9d3048.png)

Another example with multilayout. See how the 2u key is in the middle of the 1u keys when overlapped, so it goes in between those in the order (NOTE: I didn't mark the multilayout value/indices here, but you need to for the script to work):

![image](https://user-images.githubusercontent.com/23428162/175812594-c8bc52fa-ef7c-49de-af6b-9d838cb62a13.png)


## Diode placement

You can disable diode placement by unchecking `Move Diodes` in the dialog (enabled by default).

If `Move diodes based on first switch and diode` is checked/enabled, the diode placement will be based on the first switch in the pcb editor (recommended). Otherwise, diodes will just be placed at the center of their respective switch footprint.

Example of 2x2 board with `Move Diodes` and `Move diodes based on first switch and diode` enabled:

![image](https://user-images.githubusercontent.com/23428162/175814219-0725c175-1083-4793-b9f3-30fde1fd7e10.png)

![image](https://user-images.githubusercontent.com/23428162/175814161-50c14df7-72af-43a7-9075-80737b756c84.png)

Place the first (top-left) switch down and place its diode appropriately:

![image](https://user-images.githubusercontent.com/23428162/175814166-b5609762-a0fc-41a1-b559-7c426bc7892e.png)

When you run the script, the rest of the diodes will move the same way:

![image](https://user-images.githubusercontent.com/23428162/175814169-297a9c08-3843-4525-a0dd-9670c7bf7e06.png)


## Extra switch rotations

At first, all switches will be set to the same rotation as the first key. You can then use extra switch rotations (assign them in label position 10) to further rotate specific switch footprints. This is useful for e.g. specifying certain keys to be north facing, when the rest of the keys on the board are south facing.

Based on above example:

![image](https://user-images.githubusercontent.com/23428162/175814426-14dbf261-18df-4b97-b3be-6e6cffa1e5a6.png)

![image](https://user-images.githubusercontent.com/23428162/175814448-3136de9c-a5fc-4890-b58e-5f7e0222d9ed.png)


## Multilayout
> NOTE: colour is irrelevant for multilayout, but makes reading it easier.

You can either follow the guidelines and place the appropriate multilayout labels OR "squish" the keys together (layer the same multilayouts on top of eachother):

![image](https://user-images.githubusercontent.com/23428162/175812839-ee803b22-a697-4be9-a8cf-a89718b69f8f.png)

![image](https://user-images.githubusercontent.com/23428162/175812881-1f0823c0-4604-4d8c-b354-3dddf44d2095.png)

> NOTE: the above examples are for normal mode, but the same rules apply to specific reference mode


## Example Schematic (Demonstrating multilayout, diodes and stabilizers)

In terms of **stabilizers**, if the switch footprint library you're using has *separate switch and stabilizer footprints* (e.g. [marbastlib](https://github.com/ebastler/marbastlib)): use the *same reference for the stabilizer as the switch it corresponds to* (e.g. `SW54` and `S54`).

In terms of **diodes**, use the *same reference for the diode as the switch it corresponds to* (e.g. `SW54` and `D54`).

**IMPORTANT: See the rules mentioned above for an explanation on how you should order your schematic.**

> NOTE: I am using symbols from [marbastlib](https://github.com/ebastler/marbastlib). You can use any switch symbol you want.

Schematic from the same example as earlier, note the order of the symbols:

![image](https://user-images.githubusercontent.com/23428162/175812369-cbbaadc2-2d5e-4275-abe7-c62cd958d119.png)

To mass-annotate symbols, you can use this tool in the schematic editor. If you order your symbols as in the example above, this will work well for switches, but for diodes you will need to either manually assign the values, or select specific diodes and change the value of `Use first free number after:` appropriately:

![image](https://user-images.githubusercontent.com/23428162/175813686-3c01367e-f783-4ddc-ad9f-16eac725086d.png)


## SPECIFIC REFERENCE MODE (and rotated keys)
It's hard to do rotated switches with the board's normal mode (it goes left to right based on the order of switches, `SW1`, `SW2`, and so on). The order of keys in KLE gets mixed up/is hard to interpret once you introduce rotated keys, so my solution/compromise for accurately relating keys on the KLE to footprints on the PCB, is to add a separate mode.

To enable it, check the `Specific Reference Mode` checkbox in the dialog. 

Furthermore, with this mode, you're required to fill out label 4 with the reference value of the switch footprint that the key corresponds to (e.g. the key that corresponds to `SW1` should have `1` in label position 4, see guidelines above).

### EXAMPLE: Specific reference mode + rotated keys

KLE:

![image](https://user-images.githubusercontent.com/23428162/175811700-e3fd3fd9-5034-4819-ac10-f79a7ecd29ce.png)

Schematic:

![image](https://user-images.githubusercontent.com/23428162/175811688-6070137a-3b90-4b47-987a-5cdf3b898b75.png)

PCB after the script has run:

![image](https://user-images.githubusercontent.com/23428162/175811704-39f17014-a840-482a-ab17-ac925108f05e.png)
