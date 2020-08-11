import abc
import typing as typ
from typing import Optional

from . import constants, materials, phrasing, commands, utils
from .enums import Match
from .utils import select_one, is_rough_match

Player = "adventure.base.Player"
GameItem = "adventure.base.GameItem"
GameRoom = "adventure.base.GameRoom"

class GameEntity():
    def delete(self):
        pass
    
class Player(GameEntity):
    def __init__(self, initial_inventory = [], name='Player McPlayerface'):
        self.name = name
        from .objects import GameContainer
        self.inventory = GameContainer("some", "pockets", capacity=3, items=initial_inventory)
        self.inventory.currently_in = self
        
        self.room = None

    @commands.SMELL
    def on_smell(self, player):
        return phrasing.foul_smelling_person(player == self)
    
    def move_to(self, room: typ.Union[GameRoom, str]):
        if isinstance(room, str):
            room = GameEngine.get_room(room)
            
        if room is None:
            return "You try to go nowhere.  It isn't very effective."
        
        if self.room == room:
            return "You're already there."
        
        self.room = room
        
        return "You enter " + room.name + ".\n\n" + room.on_look(self)


class GameItem(GameEntity):
    def __init__(self, 
                 article: str, 
                 name: str,
                 is_scenery: bool = False,
                 is_secret: bool = False,
                 items: typ.List["GameItem"] = [],
                 material: materials.Material = materials.DEFAULT,
                 verb: str = "is",
                 combustible: typ.Optional[bool] = None,
                 include_items_in_description: bool = True,
                 size: int = 1):
        super().__init__()
        self.article = article
        self.name = name
        self.verb = verb
        self.location = None
        self.is_scenery = is_scenery
        self.material = material
        self.verb = verb
        self._combustible = combustible
        self.size = size
        self.is_secret = is_secret
        self.include_items_in_description = include_items_in_description
        
        self.items = list(items)
        for item in self.items:
            item.currently_in = self
            item.location = None
        
        self.currently_in = None
        self.used_space = 0
        self.capacity = 10000
    
    def add(self, item):
        if item.size + self.used_space > self.capacity:
            raise ValueError("Not enough space to add that")
        
        self.items.append(item)
        if item.currently_in is not None:
            item.currently_in.remove(item)
        item.currently_in = self
        item.location = None
        self.used_space += item.size
        
    def remove(self, item: GameItem):
        if item not in self.items:
            raise ValueError(f"{item} not in {self}")
        
        self.items.remove(item)
        if item.currently_in == self:
            item.currently_in = None
    
    def possessive_or_the(self, relative_to: Player):
        item = self
        while getattr(item, 'currently_in', None) is not None:
            if isinstance(item.currently_in, Player):
                if item.currently_in == relative_to:
                    return 'your'
                return item.currently_in.name + "'s"
            
            item = item.currently_in

        return 'the'
        
    def delete(self):
        super().delete()
        
        if self.currently_in is not None:
            self.currently_in.remove(self)
            
        self.currently_in = None
        
    @property
    def is_combustible(self) -> bool:
        """Can you burn this item"""
        
        if self._combustible is not None:
            return self._combustible
        return self.material.combustible

    @property
    def short_description(self) -> str:
        suffix = ''
        if self.items and self.include_items_in_description:
            suffix = ' with ' + phrasing.natural_list([x.short_description for x in self.items])
        
        if self.material == materials.DEFAULT:
            return self.article + " " + self.name + suffix
        return f"{self.article} {self.material.name} {self.name}{suffix}"
    
    def __repr__(self):
        return self.short_description
    
    def matches_name(self, text:str) -> Match:
        """Check whether user provided text might refer to this item

        Args:
            text (str): The user description of an item

        Returns:
            Match: [description]
        """
        match = is_rough_match(text, self.short_description)
        
        return match
        
        # text = text.lower()
        # for stop_word in constants.STOP_WORDS:
        #     if text.startswith(stop_word.lower() + ' '):
        #         text = text[(len(stop_word)+1):]
        
        # exact_tests = [
        #     ((self.material.name, self.name, self.location), Match.FullWithDetail),
        #     ((self.material.name, self.name), Match.FullWithDetail),
        #     ((self.name, self.location), Match.FullWithDetail),
        #     ((self.name, ), Match.Full)
        # ]
        
        # for test_elements, match_type in exact_tests:
        #     target = ' '.join(x or '' for x in test_elements).lower().strip()
        #     if text == target:
        #         return match_type
        
        # if text in self.name.lower():
        #     return Match.Partial
        
        # return Match.NoMatch
    
    @commands.LOOK
    def on_look(self, player: Player):
        return f"You see " + self.short_description
    
    @commands.SMELL
    def on_smell(self, player: Player):
        if self.material.smell:
            return "It smells " + select_one(self.material.smell)
        
        return None
    
    @commands.TASTE
    def on_taste(self, player: Player):
        if self.material.taste:
            return "It tastes " + select_one(self.material.taste)
        
        return None

    def can_take(self, player: Player) -> typ.Tuple[bool, Optional[str]]:
        """Called when a player tries to take an item.  Should return `True` if the item
        can be taken, else False

        Args:
            player (Player): [description]

        Returns:
            bool: True if item can be taken, else False
            Optional[str]: optional message describing failure/success.  I.e. "It's too hot"
        """
        if self.is_scenery:
            return False, "You can't take that"
        
        if self.currently_in == player.inventory:
            return False, "You already have that"
        
        return True, None

    @commands.TAKE
    def on_take(self, player):
        can_take, fail_msg = self.can_take(player)
        
        if not can_take:
            return fail_msg
        
        return player.inventory.on_put_in(player, self)
    
    @commands.DISCARD
    def on_drop(self, player):
        if self not in player.inventory.items:
            return "You can't drop a thing you don't have"
        
        player.inventory.remove(self)
        player.inventory.used_space -= self.size
        
        player.room.add(self, "on the floor")
        
        return f"You drop the {self.name}"

class GameRoom(GameEntity):
    def __init__(self, title: str, description: Optional[str] = None, objects: typ.Dict[str, typ.List[GameItem]] = {}):
        super().__init__()
        self.items = []
        self.name = title
        self.description = description
        
        self.add_objects(objects)
    
    def add(self, item: GameItem, location: str):
        item.location = location
        self.items.append(item)
        item.currently_in = self
        
    def add_objects(self, objects: typ.Dict[str, typ.List[GameItem]]):
        for location, obj_list in objects.items():
            if isinstance(obj_list, GameItem):
                self.add(obj_list, location)
            else:
                for obj in obj_list:
                    self.add(obj, location)
        
    def remove(self, item: GameItem):
        if item not in self.items:
            raise ValueError(f"{item} isn't in {self}")
        
        item.location = None
        self.items.remove(item)
        if item.currently_in == self:
            item.currently_in = None
    
    @commands.LOOK
    def on_look(self, player: Player):
        if self.description is not None:
            desc = self.description + "\n\n"
        else:
            desc = "You are in " + self.name + ".  "
            
        scenery_desc = phrasing.describe_items([x for x in self.items if x.is_scenery and not x.is_secret])
        if scenery_desc:
            desc += scenery_desc + "\n\n"
            
        desc += phrasing.describe_items([x for x in self.items if not x.is_scenery and not x.is_secret])
        
        return desc