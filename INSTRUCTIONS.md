
**SETUP**
unzip file of .win-venv and .linux-venv are there, do not create or activate your own environments
it will import directly from these -venv folders

copy rest over / use github to pull changes

**TORNADO LISTENER**
src/tornado/tornado_listener.py is made to run in python 3.6.8 only, with no internet access

! have to run from the root (Tornado MCP)
bash:
    tornadoi -script src/tornado/tornado_listener.py 

**NLP CLI**
run bash:
    python nlp_terminal.py 
from anywhere 
it will import modules directly from .win-venv as well





NICE TO HAVES AFTER SHOWN WE CAN ACTUALLY CONTROL TORNADO:
==========================================================

clean up and commit to git as it already works

    fix undo does twice

    allow two functions to be sent at same time, in one user query typed

    bookmark loads, you need to do another action before it actually loads

    load the other data horizons etc from config file

    clean up to seperate into nlp end and tornado listener end clearly in their seperate folders

    fix rotation and context

    give a very direct  example say zoom in at a dip (then it loads a specific bookmark that shows that part)

    add more template views

    load and toggle horizons

    change color keep integer

    gain context more

    shift? maybe ignore for now

    make limits for each transformation

    make to speech

    for context that means llm needs to know metadata and current state and units

    bookmark instead of many html files, use one html with many sub bookmarks (thats how it works turns out)

    rewrite README
    
    commit as a branch
    