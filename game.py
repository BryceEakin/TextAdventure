from adventure.engine import GameEngine, TerminalInterface, GameDefinition
from adventure.base import GameRoom, GameItem, GameContainer
from adventure import materials

starting_room = GameRoom(
    "A bare concrete cell",
    description = "You find yourself in a bare concrete cell.  Moonlight streams in "
        "through a barred window high on the far wall.",
    objects={
        "slightly askew against the wall":[
            GameItem("a", "ratty bed", is_scenery=True)
        ],
        "on the bed":[
            GameItem("a", "bit of string"),
            GameItem("a", "paperclip")
        ],
        "in the corner": [
            GameItem("some", "cobwebs", is_scenery=True, verb='are')
        ],
        "to your right":[
            GameItem("a", "cell door")
        ],
        "on the floor":[
            GameContainer("a", "can", 3, material=materials.RUSTY_TIN, initial_items=[
                GameItem("a", "recipe for making a lockpick"),
                GameItem("a", "comb")
            ])
        ]
    }
)

our_game = GameDefinition(
    "Legends of the Great Game Demo",
    starting_room = starting_room, 
    initial_inventory_items = [
        GameItem("some", "lint", size=0)
    ]
)

if __name__ == "__main__":
    App = GameEngine(our_game)
    App.run(TerminalInterface())