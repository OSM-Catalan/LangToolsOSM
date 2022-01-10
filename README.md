CLI tools to help with the localisation of OpenStreetMap.
Edit ```name:LANG``` and ```name``` keys, always supervised by the user.
See [Multilingual names](https://wiki.openstreetmap.org/wiki/Multilingual_names) for the OpenStreetMap rules and best practices. 

# Requirements

This tool requires the python3 interpreter. You can find it here:
https://www.python.org/downloads/

# Installation
Download the code and run ```pip3 install .``` inside the folder.

In Windows to run this command to install LangToolsOSM you have to open the Windows Console
```
win + R "cmd"
```
 and execute ```cd``` to navigate to the target folder
```
cd <path>
```
once in the folder run the command
```
pip3 install .
```



# Usage

Execute the commands

* ```fill_empty_name```: looks for features with ```name:LANG``` & without ```name``` tags and copy ```name:LANG``` value to ```name```.
* ```fill_empty_name_lang```: looks for features with ```name``` & without ```name:LANG``` tags and copy ```name``` value to ```name:LANG```.
* ```regex_name_lang```: look for features with ```name``` matching a regular expression and fill ```name:LANG``` with a modified version of ```name``` by a regular expression.
* ```translate_with_wikidata```: add ```name:LANG``` selecting the label or alias from ```wikidata```.
* ```fill_wikidata_from_wikipedia```: add ```wikidata``` from ```wikipedia``` tag.

All commands accept the following flags:

* ```--verbose```: print the changeset tags and all the tags of the features that you are currently editing.
* ```--dry-run```: run the program without saving any change to OSM. Useful for testing. No login required, ignores ```--username```.
* ```--help```: show documentation with all the available options.

You will be asked for necessary options if they are not passed to the command call (```--area```, ```--lang```, ```--username```).

You can define the search area by the coordinates of the bounding box in the following format ```(South,West,North,East)```, overpass filters or by the exact ```name``` value of a feature with area.

# Example
In the following example you will be able to review and add all the ```name:ca``` that are missing in the municipality of Alcalalí with the content of the ```name``` tag which is in catalan.

```
fill_empty_name_lang --lang ca -v --area "['name'='Alcalalí']" --dry-run
```
