import abc
import re
import sys
import typing as typ
from collections import namedtuple
from dataclasses import dataclass, field
from time import sleep
from typing import Optional

from . import phrasing
from .base import GameEntity, GameItem, GameRoom, Player
from .commands import CommandMatch, CommandParser, get_help_string
from .enums import Match


@dataclass
class GameDefinition():
    title: str
    starting_room: Optional[GameRoom] = None
    inventory_size: int = 3
    initial_inventory_items: typ.List[GameItem] = field(default_factory=list)
    default_player_name: str = "Kara Anderson"
    opening_exposition: str = """Hello {{player.name}}.\n\nYou awake, groggy and unsure where you are."""


class UserInterface(abc.ABC):
    @abc.abstractmethod
    def display_text(self, text: str) -> None: pass
    
    @abc.abstractmethod
    def get_selection(self, 
                      prompt: str, 
                      choice_list: typ.List[str],
                      default_index: int=0) -> int: pass
    
    @abc.abstractmethod
    def get_response(self, prompt: Optional[str] = None, default: str = '') -> str: pass

    
class TerminalInterface(UserInterface):
    def __init__(self, char_delay=0.02, newline_delay=0.25):
        self.char_delay = char_delay
        self.newline_delay = newline_delay
    
    def display_text(self, text):
        print()
        
        c_delay = self.char_delay
        l_delay = self.newline_delay
        
        lines = text.split("\n")
        
        if len(lines) > 10:
            c_delay *= 0.1
            l_delay *= 5/len(lines)
            
        
        for line in text.split("\n"):
            if c_delay == 0:
                print(line, end='')
            else:
                for c in line:
                    print(c, end='')
                    sys.stdout.flush()
                    sleep(c_delay)
            
            print()
            sleep(l_delay)
        print()
    
    def get_selection(self, prompt, choice_list, default_index=0) -> int:
        choice_list[default_index] = choice_list[default_index].upper()
        
        print()
        
        if len(choice_list) < 5:
        
            res_map = {'': default_index}
            
            for idx, item in enumerate(choice_list):
                res_map[item.lower()] = idx
                if item[0].lower() not in res_map and len(item) > 1:
                    res_map[item[0].lower()] = idx
                    choice_list[idx] = "(" + item[0] + ")" + item[1:]
            
            while True:
                self.display_text(prompt + "  [ " + " / ".join(choice_list) + " ]")
                choice = res_map.get(input("> ").lower(), None)
                print()
                if choice is not None:
                    return choice
                
                self.display_text("That's not one of the options...")
                
        raise NotImplementedError()
    
    def get_response(self, prompt=None, default=''):
        prompt = prompt or ''
        result = input(prompt + "> ")
        
        if not result:
            print("> " + default)
        print()
        return result or default


class GameEngine():
    def __init__(self, game_desc: GameDefinition):
        self.game_desc = game_desc
        self.player = None
        self.__quitting = False
        self.__interface = None
    
    def display_text(self, txt):
        if self.__interface:
            self.__interface.display_text(self._fill_text(txt))
        else:
            print(txt)
    
    def get_response(self, prompt=None, default=''):
        if not self.__interface:
            return None
        
        if prompt:
            prompt = self._fill_text(prompt)
            
        if default:
            default = self._fill_text(default)
            
        result = self.__interface.get_response(prompt, default=default)
        return result

    
    def _fill_text(self, txt):
        if self.player is None:
            return txt
        
        locals = {
            'player': self.player,
            'room': self.player.room
        }
        
        pieces = re.split("\\{(\\{[^\\}]+\\})\\}", txt)
        
        def try_eval(piece):
            try:
                return eval(piece, None, locals)
            except Exception as ex:
                return piece
        
        pieces = [
            x if not (x[0] == '{' and x[-1] == '}') 
            else try_eval(x[1:-1])
            for x in pieces
        ]
        
        return ''.join(pieces)
        
    def run(self, interface: UserInterface):
        self.__quitting = False
        self.__interface = interface
        
        title_block = "#" * (len(self.game_desc.title) + 4)
        self.display_text(
            "\n  " + title_block + "\n  # " + self.game_desc.title + " #\n  " + title_block
        )
        
        player_name = self.get_response(
            f'\n\nWhat is your name, brave adventurer? (Default is "{self.game_desc.default_player_name}")', 
            default=self.game_desc.default_player_name
        )
        
        self.player = Player(
            name=player_name,
            initial_inventory=self.game_desc.initial_inventory_items
        )
        self.player.room = self.game_desc.starting_room
        
        parser = CommandParser(self.player)
        
        self.display_text(self.game_desc.opening_exposition)
        
        last_context = None
        
        while not self.__quitting:
            self.display_text("What do you do?")
            cmd_match, cmd = parser.parse_command(
                self.get_response(default='look around'),
                last_context
            )
            
            if cmd_match != Match.NoMatch:
                obj_lookup = {
                    'inventory': self.player.inventory,
                    'self': self,
                    'room': self.player.room,
                }
                obj_lookup.update(enumerate(cmd.args))
                
                act_on = obj_lookup[cmd.cmd_def.target]
                
                if isinstance(act_on, GameItem):
                    last_context = act_on
                else:
                    last_context = None
                
                if not hasattr(act_on, cmd.cmd_def.func):
                    self.display_text(f"You can't {cmd.verb} that")
                else:
                    out_msg = getattr(act_on, cmd.cmd_def.func)(
                        self.player, 
                        *[x for i,x in enumerate(cmd.args) if i != cmd.cmd_def.target]
                    )
                    if out_msg:
                        self.display_text(out_msg)
                    else:
                        self.display_text(phrasing.nothing_happens())
            else:
                self.display_text("DEBUG: " + repr((cmd_match, cmd)))
    
    def show_help(self, player):
        return get_help_string()
        
    def quit(self, player):
        if self.__interface is not None:
            choice = self.__interface.get_selection(
                "Are you sure you want to quit?",
                [ "Yes", "No", "Cancel" ],
                2
            )
            
            if choice == 0:
                self.__quitting = True
                return "Thanks for playing!  Later..."
        else:
            self.__quitting = True
            return "Thanks for playing!  Later..."
            
        return "Nevermind then"
