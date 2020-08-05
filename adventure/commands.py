import re
import typing as typ
from collections import namedtuple
from typing import Optional

from .base import GameEntity, Player
from .constants import SELF_WORDS, STOP_WORDS
from .enums import Match

CmdDef = namedtuple('CmdDef', ['desc', 'verbs', 'num_objs', 'func', 'target', 'examples'])

KNOWN_COMMANDS = [
    CmdDef(
        desc = 'Examine your surroundings', 
        verbs = ['look', 'look around'], 
        num_objs = 0, 
        func = 'on_look', 
        target = 'room',
        examples = ['look around', 'look in bag']
    ),
    CmdDef(
        desc = "Take something and add it to your inventory",
        verbs = ['take', 'get', 'pick up', 'acquire', 'grab', 'snatch'], 
        num_objs = 1,
        func = 'on_take',
        target = 0,
        examples = ['take sword', 'pick up coins']
    ),
    CmdDef(
        desc = "Discard an item",
        verbs = ['drop', 'get rid of', 'lose', 'discard', 'ditch'],
        num_objs = 1, 
        func = 'on_drop',
        target = 0,
        examples = ['drop string', 'ditch the broad']
    ),
    CmdDef(
        desc = "Show the player's inventory",
        verbs = ['i', 'inventory', 'show inventory', 'what do i have'],
        num_objs = 0,
        func = 'on_look',
        target = 'inventory',
        examples = []
    ),
    CmdDef(
        desc = "Quit the game",
        verbs = ['quit', 'exit', 'q', 'end', 'stop'],
        num_objs = 0,
        func = 'quit',
        target = 'self',
        examples = []
    ),
    CmdDef(
        desc = "Open a door or container",
        verbs = ['open', ],
        num_objs = 1,
        func = 'on_open',
        target = 0,
        examples = ['open tin can']
    ),
    CmdDef(
        desc = "Open a door or container with something",
        verbs = ['open', ],
        num_objs = 2,
        func = 'on_open',
        target = 0,
        examples = ['open door with key', 'open safe with blowtorch']
    ),
    CmdDef(
        desc = "See game help",
        verbs = ['help', 'what do i do', '?', 'fuck'],
        num_objs = 0,
        func = 'show_help',
        target = 'self',
        examples = ["Help!  Help!  I'm in a help menu and don't know how to ask for help!"]
    ),
    CmdDef(
        desc = "Smell a thing",
        verbs = ['smell', 'sniff'],
        num_objs = 1,
        func = 'on_smell',
        target = 0,
        examples = ['smell yourself', 'smell']
    ),
    CmdDef(
        desc = "Taste a thing",
        verbs = ['taste', 'lick'],
        num_objs = 1,
        func = 'on_taste',
        target = 0,
        examples = ['taste your lint', 'taste the door']
    )
]

CommandMatch = namedtuple("CommandMatch", ['cmd_def', 'verb', 'args'])

def get_help_string():
    results = []
    
    for cmd in KNOWN_COMMANDS:
        result = cmd.desc + ":\n"
        result += "  - " + ', '.join(cmd.verbs)
        
        result += "\n\n Ex: " + ', '.join('"' + x + '"' for x in cmd.examples)
        results.append(result)
        
    return '\n\n\n'.join(results)

class CommandParser():
    def __init__(self, player):
        self.player = player
    
    def _match_obj(self, desc: str, look_in: GameEntity) -> typ.Tuple[Match, typ.List[GameEntity]]:
        matches = []
        
        for item in look_in.items:
            m = item.matches_name(desc)
            if m == Match.FullWithDetail:
                return (m, [item])
            
            if m != Match.NoMatch:
                matches.append((m, item))
            
        best = max((x[0] for x in matches), default=Match.NoMatch)
        matches = [x[1] for x in matches if x[0] == best]
        
        return (best, matches)
    
    def find_object(self, desc: str) -> typ.Tuple[Match, typ.List[GameEntity]]:
        m1, m1_objs = self._match_obj(desc, self.player.inventory)
        m2, m2_objs = self._match_obj(desc, self.player.room)
        
        for sw in STOP_WORDS:
            desc = re.sub(" +", " ", re.sub("(^| )" + sw + "($| )", " ", desc))
        
        if desc.strip().lower() in SELF_WORDS:
            return Match.Full, [self.player]
        
        if m1 > m2:
            return m1, m1_objs
        elif m2 > m1:
            return m2, m2_objs
        return m1, m1_objs + m2_objs
        
    def parse_command(self, cmd: str) -> typ.Tuple[Match, typ.List[CommandMatch]]:
        cmd = cmd.lower().strip()
        
        matches = {
            Match.Full: [],
            Match.Partial: []
        }
        
        if cmd == "debug":
            print("Trying to debug....")
            import code
            code.interact("** DEBUGGING **", local={'player': self.player, 'self': self})
        
        for cmd_def in KNOWN_COMMANDS:
            for verb in cmd_def.verbs:
                if cmd_def.num_objs == 0 and cmd == verb:
                    matches[Match.Full].append(CommandMatch(cmd_def, verb, []))
                    
                elif cmd_def.num_objs == 1 and cmd.startswith(verb + ' '):
                    obj_match, objs = self.find_object(cmd[(len(verb)+1):])
                    
                    if obj_match != Match.NoMatch:
                        for obj in objs:
                            matches[min(Match.Full, obj_match)].append(CommandMatch(cmd_def, verb, [obj]))
                elif cmd_def.num_objs > 1 and cmd.startswith(verb + ' '):
                    print("Not supported yet")
                        
        if matches[Match.Full]:
            return Match.Full, matches[Match.Full][0]
                
        return Match.NoMatch, []
