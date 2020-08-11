from .base import GameItem, GameEntity, Player
from . import materials, commands, utils
from .engine import GameEngine
from .enums import Match

from typing import Optional
import typing as typ

class GameContainer(GameItem):
    def __init__(self, article, name, capacity, items = [], material=materials.DEFAULT, location=None):
        super().__init__(article, name, items=items, material=material, size=capacity, include_items_in_description=False)
        
        self.capacity = capacity
        self.used_space = sum(i.size for i in items)
    
    @commands.PUT_IN
    def on_put_in(self, player: Player, item: GameItem) -> Optional[str]:
        if self.capacity - self.used_space >= item.size:
            self.add(item)
            
            return f"You put the {item.name} in {self.possessive_or_the(player)} {self.name}"
        
        return f"There isn't room for that in {self.possessive_or_the(player)} {self.name}"
    
    @commands.LOOK
    def on_look(self, player):
        result = f"You look in {self.possessive_or_the(player)} {self.name}."
        
        if not self.items:
            result += "  There's nothing there."
        else:
            result += "  You see...\n * " + '\n * '.join([x.short_description for x in self.items])
            
        return result
    
    # @commands.TAKE
    # def on_take(self, player: Player) -> Optional[str]:
    #     if self.capacity > player.inventory.capacity:
    #         if self.used_space + player.inventory.used_space > self.capacity:
    #             return "Not enough space to fit all the stuff you already have and all the stuff in there into your inventory.  Dump some shit."
            
    #         oth = player.inventory
    #         player.inventory = self
            
    #         for item in oth.items:
    #             self.on_put_in(player, item)
                
    #         oth.items.clear()
    #         oth.delete()
                
    #         return f"You swap out your {oth.name} for the {self.name} and have more room in your inventory!"
        
    #     return super().on_take(player)
        
    def delete(self):
        super().delete()
        
        for item in self.items:
            item.delete()

class Door(GameItem):
    def __init__(self, 
                 article, 
                 name, 
                 is_locked:bool = True, 
                 is_secret:bool = False,
                 goes_to: Optional[str] = None,
                 material=materials.WOOD
                 ):
        super().__init__(article, name, is_secret=is_secret, material=material)
        self.is_locked = is_locked
        self._goes_to = goes_to
        
    @property
    def goes_to(self):
        return GameEngine.get_room(self._goes_to)
    
    @goes_to.setter
    def goes_to(self, room:str):
        self._goes_to = room
        
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
    
    @commands.ENTER
    def on_enter(self, player):
        if self.is_secret or self.is_locked:
            return None
        
        if self.goes_to is None:
            return "It leads nowhere.  You're still in the "
        
        return player.move_to(self.goes_to)
    