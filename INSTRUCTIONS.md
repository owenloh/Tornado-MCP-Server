**SETUP**
unzip file of .win-venv and .linux-venv if they are there, refrain from creating or activating your own environments
it will import directly from these *-venv folders
    .win-venv is made in windows 11, python 3.13.5, packages from win-requirements.txt installed
    .linux-venv created in linux, python 3.6.8 to match Tornado version, packages from linux-requirements.txt installed
DO NOT ACTIVATE THE VENVs 

1. set LLM usage in .env, check .env(example only) as example
2. set config.json for seismic, attribute, horizons at mappings of crosslines to  survey coordinates
3. set context.json to give the LLM more context
4. set templates, at least 'default_template.html' found in data/templates and more can be created via tornado (each saved xml must only contain ONE bookmark (through tornado you can save a set in one xml, but don't do it))

data/captures have .pngs that are a byproduct of vision, where we are forced to capture an image in order to change the view on tornado (please someone enlighten me if I am wrong, could not figure out from documentation)
data/bookmarks/TEMP_BKM.html is the only xml where torpy loads into tornado, so this is the xml that src/tornado_end/core/bookmark_engine_v2.py manipulates

**TORNADO end**
src/tornado-end/main.py is made to run in python 3.6.8 only, with no internet access

open an XTerm terminal and go to root directory
!!! MUST run from root folder(Tornado MCP)
run bash:
    tornadoi -script src/tornado_end/tornado_listener.py

This is due to some constraints regarding where the internal libraries can be imported from

**NLP end**
on your Windows NUC, go to the same root directory in the networked files, and run bash:
    python src/nlp_end/main.py

**both ends have to share the same directory/folder, not copies, for this to work**
this is because both ends communicate through the SQLite database only (this is due to security restraints)







Done:
===========================

multiple prompt, remembers what you told it, understands your environemtn (what templates available etc)

change horizon toggle to work

use internal llms/gemini fallback

make it use crossline adn inline instaed of x y z through mapping for now will do

give a very direct context example say zoom in at a dip (then it loads a specific bookmark that shows that part)

BUGS/IMPROVEMENTS:
===========================================================================

    make to speech

More Challenging Improvements:    
===============================================================================

    make it load when i want it to only, add a function to load from config, it doesnt load immdediatey, also a function to end the listener session

    for context that means llm needs to know metadata and current state and units
    
    shifting frame with crossline and inline (can be done w math)
    