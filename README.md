CLI tool to help with the localisation of OpenStreetMap.
Edit ```name:LANG``` and ```name``` keys, always supervised by the user.

# Requirements

This tool requires the python3 intrepreter. You can find it here:
https://www.python.org/downloads/

# Installation
Download the code and run this command inside the folder
```
pip3 install .
```

# Usage

Execute the commands

* ```fill_empty_name```: looks for features with ```name:LANG``` & without ```name``` tags and copy ```name:LANG``` value to ```name```.
* ```fill_empty_name_lang```: looks for features with ```name``` & without ```name:LANG``` tags and copy ```name``` value to ```name:LANG```.
* ```regex_name_lang```: look for features with ```name``` matching a regular expression and fill ```name:LANG``` with a modified version of ```name``` by a regular expression.

All commands accept the following flags:

* ```--verbose```: print the changeset tags and all the tags of the features you are currently editing.
* ```--dry-run```: run the program without saving any change to OSM. Useful for testing.

The programs will ask you your username and OSM password to be able to edit OSM. Then, it will ask you the zone you want to edit.
You can specify the coordinates of the bounding box in the following format ```(South,West,North,East)``` or the ```name``` value of a feature with area.
