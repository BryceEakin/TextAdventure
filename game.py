from adventure.engine import GameEngine, TerminalInterface, GameDefinition
from adventure.base import GameRoom, GameItem, GameContainer
from adventure import materials
from adventure.enums import Match

from adventure import utils

from typing import Optional



class Door(GameItem):
    def __init__(self, 
                 article, 
                 name, 
                 is_locked:bool = True, 
                 is_secret:bool = False,
                 goes_to: Optional[GameRoom] = None,
                 material=materials.WOOD
                 ):
        super().__init__(article, name, is_secret=is_secret, material=material)
        self.is_locked = is_locked
        self.goes_to = goes_to
        
    @property
    def short_description(self):
        desc = super().short_description
        if self.is_locked:
            return desc
        
        if self.goes_to is None:
            return desc + " to nowhere"
        return desc + " to " + self.goes_to.name
        
    def matches_name(self, text):
        if self.goes_to is not None and not self.is_locked:
            match = utils.is_rough_match(text, self.goes_to.name)
            if match > Match.NoMatch:
                return match
        
        return super().matches_name(text)
        
    def on_unlock(self, player, key):

        if not self.is_locked:
            return "It's not locked"
        
        if key.name != 'key':
            return "You can't unlock it with that"
        
        self.is_locked = False
        return "You unlock the door with the key! It can now open."
        
    def on_open(self, player, with_obj=None):
        
        where_it_goes = "...nothing" if self.goes_to is None else self.goes_to.name
        
        if self.is_secret:
            return "What are you trying to do?"

        if self.is_locked and with_obj is not None and with_obj.name == 'key':
            self.is_locked = False
            return "You unlock the door with the key and open it. Eureka! Through the door you see " + where_it_goes
        
        if self.is_locked:
            return "It's locked"
        
        return "You opened it.  Through the door you see " + self.goes_to.name
    
    def on_enter(self, player):
        if self.is_secret or self.is_locked:
            return None
        
        if self.goes_to is None:
            return "It leads nowhere.  You're still in the "
        
        return player.move_to(self.goes_to)
    
next_room = GameRoom(
    "a dining room",
    description = "You enter the dining room. There is a long dining table with 8 place settings. You see cobwebs on the wine glasses",
    objects = {
        "on the table":[
            GameItem("a", "candelabra"),
        ]
    }
)
    
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
            Door("a", "cell door", is_locked=False, goes_to=next_room)
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
        GameItem("some", "lbint", size=0)
    ]
)

if __name__ == "__main__":
    App = GameEngine(our_game)
    App.run(TerminalInterface())