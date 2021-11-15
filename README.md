CLI tools to help with the localisation of OpenStreetMap.
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
* ```translate_with_wikidata```: add ```name:LANG``` selecting the label or alias from ```wikidata```.

All commands accept the following flags:

* ```--verbose```: print the changeset tags and all the tags of the features that you are currently editing.
* ```--dry-run```: run the program without saving any change to OSM. Useful for testing. No login required, ignores ```--username```.
* ```--help```: show documentation with all the available options.

You will be asked for necessary options if they are not passed to the command call (```--area```, ```--lang```, ```--username```).

You can define the search area by the coordinates of the bounding box in the following format ```(South,West,North,East)``` or by the exact ```name``` value of a feature with area.
