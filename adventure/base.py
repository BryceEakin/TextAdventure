import abc
import typing as typ
from typing import Optional

from . import constants, materials, phrasing
from .enums import Match
from .utils import select_one

Player = "adventure.base.Player"
GameItem = "adventure.base.GameItem"

class GameEntity():
    def on_tick(self) -> typ.Optional[str]:
        """Called on every entity in the current environment after every accepted user command"""
        pass
    
    def on_attack(self, player: Player, weapon: typ.Optional[GameItem]) -> Optional[str]:
        """Called when a player attacks this entity

        Args:
            player (Player): [description]
            weapon (GameItem): [description]

        Returns:
            Optional[str]: [description]
        """
        pass
    
    def on_smell(self, player: Player) -> Optional[str]:
        """Called when a player tries to smell this entity

        Args:
            player (Player): [description]

        Returns:
            Optional[str]: [description]
        """
        pass
    
    def on_taste(self, player: Player) -> Optional[str]:
        """Called when a player tries to taste this entity

        Args:
            player (Player): [description]

        Returns:
            Optional[str]: [description]
        """
        pass
    
    def on_open(self, player: Player, with_obj: typ.Optional[GameItem]) -> Optional[str]:
        """Called when a player tries to open this entity

        Args:
            player (Player): [description]
            with_obj (typ.Optional[GameItem]): key, lockpick, can opener maybe, etc.

        Returns:
            Optional[str]: [description]
        """
        pass
    
    def on_read(self, player: Player) -> Optional[str]:
        """Called when player reads this item

        Args:
            player (Player): [description]

        Returns:
            Optional[str]: [description]
        """
        pass

    
    def on_take(self, player: Player) -> Optional[str]:
        """Called when player tries to take/get this entity.  

        Args:
            player (Player): [description]

        Returns:
            typ.Optional[str]: [description]
        """
        pass
        
    def on_look(self, player: Player) -> Optional[str]:
        """Called when a player tries to look at the item.

        Args:
            player (Player): [description]

        Returns:
            Optional[str]: [description]
        """
        pass
    
    def on_look_under(self, player: Player) -> Optional[str]:
        """Called when a player tries to look under the item.

        Args:
            player (Player): [description]

        Returns:
            Optional[str]: [description]
        """
        pass
    
    def on_eat(self, player: Player) -> Optional[str]:
        """Called when a player tries to eat the item

        Args:
            player (Player): [description]

        Returns:
            Optional[str]: [description]
        """
        pass
    
    def on_put_in(self, player: Player, item: GameItem) -> Optional[str]:
        """Called when a player tries to put something in this

        Args:
            player (Player): [description]
            item (GameItem): Item to put into this entity

        Returns:
            Optional[str]: [description]
        """
        pass
    
    def on_drop(self, player: Player) -> Optional[str]:
        """Drop the item from your inventory

        Args:
            player (Player): [description]

        Returns:
            Optional[str]: [description]
        """
        pass
            
    def delete(self):
        pass
    
    
class Player(GameEntity):
    def __init__(self, initial_inventory = [], name='Player McPlayerface'):
        self.name = name
        self.inventory = GameContainer("some", "pockets", capacity=3, initial_items=initial_inventory)
        self.inventory.currently_in = self
        
        self.room = None

    def on_smell(self, player):
        return phrasing.foul_smelling_person(player == self)


class GameItem(GameEntity):
    def __init__(self, 
                 article: str, 
                 name: str,
                 is_scenery: bool = False,
                 material: materials.Material = materials.DEFAULT,
                 verb: str = "is",
                 combustible: typ.Optional[bool] = None,
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
        
        self.currently_in = None
    
    def possessive_or_the(self, relative_to: Player):
        item = self
        while item.currently_in is not None:
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
        if self.material == materials.DEFAULT:
            return self.article + " " + self.name
        return f"{self.article} {self.material.name} {self.name}"
    
    def __repr__(self):
        return self.short_description
    
    def matches_name(self, text:str) -> Match:
        """Check whether user provided text might refer to this item

        Args:
            text (str): The user description of an item

        Returns:
            Match: [description]
        """
        text = text.lower()
        for stop_word in constants.STOP_WORDS:
            if text.startswith(stop_word.lower() + ' '):
                text = text[(len(stop_word)+1):]
        
        exact_tests = [
            ((self.material.name, self.name, self.location), Match.FullWithDetail),
            ((self.material.name, self.name), Match.FullWithDetail),
            ((self.name, self.location), Match.FullWithDetail),
            ((self.name, ), Match.Full)
        ]
        
        for test_elements, match_type in exact_tests:
            target = ' '.join(x or '' for x in test_elements).lower().strip()
            if text == target:
                return match_type
        
        if text in self.name.lower():
            return Match.Partial
        
        return Match.NoMatch
    
    def on_look(self, player: Player):
        if self.material != materials.DEFAULT:
            return f"You see {self.article} {self.name} made of {self.material.name}"
        return f"You see {self.article} {self.name}"
    
    def on_smell(self, player: Player):
        if self.material.smell:
            return "It smells " + select_one(self.material.smell)
        
        return super().on_smell(player)
    
    def on_taste(self, player: Player):
        if self.material.taste:
            return "It tastes " + select_one(self.material.taste)
        
        return super().on_taste(player)

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

    def on_take(self, player):
        can_take, fail_msg = self.can_take(player)
        
        if not can_take:
            return fail_msg
        
        return player.inventory.on_put_in(player, self)
            
    def on_drop(self, player):
        if self not in player.inventory.items:
            return "You can't drop a thing you don't have"
        
        player.inventory.remove(self)
        player.room.add(self, "on the floor")
        
        return f"You drop the {self.name}"

class GameContainer(GameItem):
    def __init__(self, article, name, capacity, initial_items = [], material=materials.DEFAULT, location=None):
        super().__init__(article, name, material=material, size=capacity)
        self.items = list(initial_items)
        self.capacity = capacity
        self.used_space = sum(i.size for i in initial_items)
        
        for item in self.items:
            item.currently_in = self
            item.location = None
        
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
        
    def on_put_in(self, player: Player, item: GameItem) -> Optional[str]:
        if self.capacity - self.used_space >= item.size:
            self.add(item)
            
            return f"You put the {item.name} in {self.possessive_or_the(player)} {self.name}"
        
        return f"There isn't room for that in {self.possessive_or_the(player)} {self.name}"
    
    def on_look(self, player):
        result = f"You look in {self.possessive_or_the(player)} {self.name}."
        
        if not self.items:
            result += "  There's nothing there."
        else:
            result += "  You see...\n * " + '\n * '.join([x.short_description for x in self.items])
            
        return result
    
    def on_take(self, player: Player) -> Optional[str]:
        if self.capacity > player.inventory.capacity:
            if self.used_space + player.inventory.used_space > self.capacity:
                return "Not enough space to fit all the stuff you already have and all the stuff in there into your inventory.  Dump some shit."
            
            oth = player.inventory
            player.inventory = self
            
            for item in oth.items:
                self.on_put_in(player, item)
                
            oth.items.clear()
            oth.delete()
                
            return f"You swap out your {oth.name} for the {self.name} and have more room in your inventory!"
        
        return super().on_take(player)
        
    def delete(self):
        super().delete()
        
        for item in self.items:
            item.delete()

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
            
    def on_look(self, player: Player):
        if self.description is not None:
            desc = self.description + "\n\n"
        else:
            desc = "You are in " + self.name + ".  "
            
        scenery_desc = phrasing.describe_items([x for x in self.items if x.is_scenery])
        if scenery_desc:
            desc += scenery_desc + "\n\n"
            
        desc += phrasing.describe_items([x for x in self.items if not x.is_scenery])
        
        return desc
