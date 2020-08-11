import abc
import re
import sys
import typing as typ
from collections import namedtuple
from dataclasses import dataclass, field
from time import sleep
from typing import Optional

from . import phrasing, commands
from .base import GameEntity, GameItem, GameRoom, Player
from .enums import Match

from nameparser import HumanName


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
    def __init__(self):
        self.game_desc = None
        self.player = None
        self.__quitting = False
        self.__interface = None
        
        self.__rooms = {}
    
    def add_room(self, id: str, room: GameRoom):
        self.__rooms[id] = room
        
    def get_room(self, id: str, silent=False):
        if not silent:
            return self.__rooms[id]
        return self.__rooms.get(id, None)
    
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
            else str(try_eval(x[1:-1]))
            for x in pieces
        ]
        
        return ''.join(pieces)
        
    def run(self, game_desc: GameDefinition, interface: UserInterface):
        self.game_desc = game_desc
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
            name=HumanName(player_name),
            initial_inventory=self.game_desc.initial_inventory_items
        )
        self.player.room = self.get_room(self.game_desc.starting_room)
        
        self.display_text(self.game_desc.opening_exposition)
        
        last_context = None
        
        while not self.__quitting:
            self.display_text("What do you do?")
            
            user_response = self.get_response(default='look around')
            
            if user_response.lower() == 'debug':
                print("Trying to debug....")
                import code
                code.interact("** DEBUGGING **", local={'player': self.player})
                continue
            
            cmd_match, cmd_list = commands.Command.evaluate_command(
                user_response,
                self.player,
                last_context
            )
            
            if cmd_match != Match.NoMatch and len(cmd_list) > 0:
                if len(cmd_list) == 1:
                    cmd = cmd_list[0]
                    if 'handlers' in cmd and len(cmd['handlers']) > 0:
                        for fn in cmd['handlers']:
                            result = fn()
                            if result:
                                self.display_text(result)
                            else:
                                self.display_text(phrasing.nothing_happens())
                    else:
                        self.display_text(f"You can't {cmd.get('verb', 'do')} that")
                        
                    if isinstance(cmd.get('object', None), GameItem):
                        last_context = cmd['object']
                    else:
                        last_context = None
                elif not cmd_list:
                    self.display_text(f"That was ambiguous -- can you be more specific?  Type 'help' for examples")
                    
                    self.display_text(f"DEBUG: \n{cmd_match}\n{cmd_list}")
                else:
                    self.display_text(f"That was ambiguous -- can you be more specific?  Type 'help {cmd_list[0]['verb']}' for examples")
                    
                    self.display_text(f"DEBUG: \n{cmd_match}\n{cmd_list}")
                
            else:
                self.display_text("That didn't make much sense to me.  Type 'help' if you aren't sure what you can do")
                
                self.display_text(f"DEBUG: \n{cmd_match}\n{cmd_list}")
    
    def show_inventory(self, player):
        return player.inventory.on_look(player)
    
    def show_help(self, player, wants_help_with=None):
        return commands.get_help_string(wants_help_with)
        
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

GameEngine = GameEngine()

commands.HELP.register_generic_handler(GameEngine.show_help)
commands.QUIT.register_generic_handler(GameEngine.quit)
commands.SHOW_INVENTORY.register_generic_handler(GameEngine.show_inventory)
