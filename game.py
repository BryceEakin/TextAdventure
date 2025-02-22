from adventure.engine import GameEngine, TerminalInterface, GameDefinition
from adventure.base import GameRoom, GameItem
from adventure.objects import GameContainer, Door
from adventure import materials
from adventure.enums import Match

from adventure import utils

from typing import Optional


GameEngine.add_room("DINING_ROOM", GameRoom(
    "a dining room",
    description = "You enter the dining room. There is a long dining table. You see cobwebs on the wine glasses",
    objects = {
        "on the table":[
            GameItem("several", "place settings", 3, items=[
                GameItem("a", "plate"),
                GameItem("8", "wine glasses", is_scenery=True, items=[
                    GameItem("a", "cobweb")
                ])
            ])
        ],
    }
))
    
GameEngine.add_room("ENTRYWAY", GameRoom(
    "You're in a ... room?",
    description = "",
    objects={
        "slightly askew against the wall":[
            GameItem("a", "ratty cot", is_scenery=True)
        ],
        "on the bed":[
            GameItem("a", "bit of string"),
            GameItem("a", "paperclip")
        ],
        "in the corner": [
            GameItem("some", "cobwebs", is_scenery=True, verb='are')
        ],
        "to your right":[
            Door("a", "cell door", is_locked=False, goes_to='DINING_ROOM')
        ],
        "on the floor":[
            GameContainer("a", "can", 3, material=materials.RUSTY_TIN, items=[
                GameItem("a", "recipe for making a lockpick"),
                GameItem("a", "comb")
            ])
        ]
    }
))

our_game = GameDefinition(
    "Legends of the Great Game Demo",
    starting_room = "ENTRYWAY",
    opening_exposition = """
    Dear {{player.name.first}},

    My treasure is in the house.  Go find it.
    
    Love, 
    your estranged grandfather
    Percival Montclaire
    
    --------------------------------
    
    You read the letter over again as the taxi pulls up to the house.  What does it mean? 
    Why are you here?  What is the treasure?  Who is Percival!?
    
    You exit the taxi and look at the creepy house.
    
    You pull open the door and step inside.  The door slams shut behind you.
    """,
    initial_inventory_items = [
        GameItem("some", "lint", size=0)
    ]
)

if __name__ == "__main__":
    GameEngine.run(our_game, TerminalInterface(0.005, 0.2))
    