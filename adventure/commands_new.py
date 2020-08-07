import abc
import typing as typ

import inspect, functools
from collections import defaultdict

def _get_class_that_defined_method(meth):
    if isinstance(meth, functools.partial):
        return get_class_that_defined_method(meth.func)
    if inspect.ismethod(meth) or (inspect.isbuiltin(meth) and getattr(meth, '__self__', None) is not None and getattr(meth.__self__, '__class__', None)):
        for cls in inspect.getmro(meth.__self__.__class__):
            if meth.__name__ in cls.__dict__:
                return cls
        meth = getattr(meth, '__func__', meth)  # fallback to __qualname__ parsing
    if inspect.isfunction(meth):
        cls = getattr(inspect.getmodule(meth),
                      meth.__qualname__.split('.<locals>', 1)[0].rsplit('.', 1)[0],
                      None)
        if isinstance(cls, type):
            return cls
    return getattr(meth, '__objclass__', None)


class CommandPattern():
    JUST_VERB = "{verb}"
    VERB_AND_OBJECT = "{verb} {object}"


class Command():
    _REGISTERED_CLASS_LISTENERS = defaultdict(list)
    _REGISTERED_GENERIC_LISTENERS = defaultdict(list)
    _REGISTERED_OBJECT_LISTENERS = defaultdict(list)
    _REGISTERED_OBJECT_EXCLUSIONS = defaultdict(list)
    
    def __init__(self,
                 description: str,
                 pattern: str,
                 verbs: typ.List[str],
                 examples: typ.List[str] = []
                 ):
        pass

    def __call__(self, fn):
        cls = _get_class_that_defined_method(fn)
        if cls is None or not any(x.__name__ == 'GameEntity' for x in cls.mro()):
            raise ValueError(
                "Can only be used as a decorator on functions in GameEntity subclasses.  Use .register_*() functions instead"
            )
            
        Command._REGISTERED_CLASS_LISTENERS[(self, cls)].append(fn)
        
        return fn

    @property
    def allows_generic(self):
        return True

    def register_generic_handler(self, fn):
        if not self.allows_generic:
            raise RuntimeError("This command doesn't support generic handlers")
        
        Command._REGISTERED_GENERIC_LISTENERS[self].insert(0, fn)
        return fn
        
    def register_object_handler(self, fn, obj):
        Command._REGISTERED_OBJECT_LISTENERS[(self, obj)].append(fn)
        return fn
    
    def unregister_object_handler(self, obj):
        if (self, obj) in Command._REGISTERED_OBJECT_LISTENERS:
            del Command._REGISTERED_OBJECT_LISTENERS[(self, obj)]
            
    def unregister_generic_handler(self, fn):
        if fn in _REGISTERED_GENERIC_LISTENERS[self]:
            _REGISTERED_CLASS_LISTENERS[self].remove(fn)

class _ParseToken(abc.ABC):
    def __init__(self, children):
        self._children = children
        if children is None or len(children) == 0 or all(x is None for x in children):
            self._children = None
        
    @abc.abstractmethod
    def parse(self, txt, context): pass
    
    def _parse_children(self, txt_list, context):
        res = {}
        
        if self._children is None:
            return res
        
        for child, txt in zip(self._children, txt_list):
            if child is None:
                if txt is None or txt.strip() == '':
                    continue
                
                return None
            
            child_res = child.parse(txt, context)
            
            if child_res is None:
                return None
            
            res.update(child)
            
        return res
    

class _OptionalToken(_ParseToken):
    def __init__(self, inner_token, default_vals={}):
        super.__init__([])
        self.token = inner_token
        self.default_vals = default_vals
        
    def parse(self, txt, context):
        if txt.strip() == '':
            return dict(self.default_vals)
        return self.token.parse(txt, context)
    
class _MultiMatchToken(_ParseToken):
    def __init__(self, options, l_child, r_child):
        super().__init__([l_child, r_child])
        self.options = [o.lower() for o in options]
        
    def parse(self, txt, context):
        txt = txt.lower()
        
        for opt in self.options:
            if opt not in txt:
                continue
            
            splits = txt.split(opt)
            
            for i in range(1, len(splits)):
                res = self._parse_children([
                    opt.join(splits[:i]),
                    opt.join(splits[i:])
                ])
            
                if res is not None:
                    return res
        
        return None    
        
class _ParseStringArg(_ParseToken):
    def __init__(self, default_txt = None, require_quotes=True):
        self.default_txt = default_txt
        self.require_quotes = require_quotes
    
    def parse(self, text, context):
        if text is None or text.strip() == '':
            return {'arg': self.default_txt}
        
        if text[0] == '"' and text[-1] == '"':
            return {'arg': text[1:-1]}
        
        if self.require_quotes:
            return None
        
        return {'arg': text}
        

class _FixedTextToken(_ParseToken):
    def __init__(self, pattern, l_child, r_child):
        super().__init__([l_child, r_child])
        self._pattern = pattern.lower()
        
    def parse(self, text, context):
        text = text.lower()
        if self._pattern not in text:
            return None
        
        splits = text.split(self._pattern)
        
        for i in range(1, len(splits)):
            res = self._parse_children([
                self._pattern.join(splits[:i]), 
                self._pattern.join(splits[i:])
            ], context)
            
            if res is not None:
                return res
                
        return None

def _parse_block(pattern, verbs):
    if pattern.strip() == '':
        return None
    
    is_optional = False
    if pattern[0] == '[' and pattern[-1] == ']':
        is_optional = True
        pattern = pattern[1:-1]
    
    bits = []
    bits = re.split("(\\{[^\\}]+\\})", pattern)
    
    are_fixed = [x[0] != '{' for x in bits]
    
    if any(are_fixed):
        idx = list([i for i, x in enumerate(are_fixed) if x])[0]
        l_child = _parse_block(''.join(bits[:idx]))
        r_child = _parse_block(''.join(bits[(idx+1):]))
        return _FixedTextToken(bits[idx], l_child, r_child)
        

def _parse_pattern(pattern, verbs):
    bits = [_parse_block(x) for x in re.split("(\\[[^\\]]+\\])", pattern)]
    


LOOK = Command(
    "Examine an item or your surroundings",
    "{verb}[ {object:room}]",
    ['look', 'look around', 'look at', 'look inside', 'look in', 'examine', 'scrutinize'],
    ["look around", "look in bag", "look at the tin can"]
)

TAKE = Command(
    "Take something and add it to your inventory",
    "{verb} {object} [from {object_in:room}]",
    ['take', 'get', 'pick up', 'acquire', 'grab','snatch'],
    ["take sword", "pick up coins", "snatch lint from the bag"]
)

DISCARD = Command(
    "Discard an item",
    CommandPattern.VERB_AND_OBJECT,
    ['drop', 'get rid of', 'lose', 'discard', 'ditch'],
    ["drop string", "ditch the broadsword"]
)

SHOW_INVENTORY = Command(
    "Show the player's inventory",
    CommandPattern.JUST_VERB,
    ['i', 'inventory', 'show inventory', 'what do i have']
)

QUIT = Command(
    "Quit the game",
    CommandPattern.JUST_VERB,
    ['quit', 'exit', 'q', 'end', 'stop']
)

OPEN = Command(
    "Open a door or container",
    "{verb} {object}[ with {object_arg:None}]",
    ['open', ],
    ['open the door', 'open the chest with the crowbar']
)

HELP = Command(
    "See game help",
    CommandPattern.JUST_VERB,
    ['help', 'what do i do', '?', 'ugg']
)

SMELL = Command(
    "Smell a thing",
    CommandPattern.VERB_AND_OBJECT,
    ['smell', 'sniff'],
    ['smell yourself', 'smell the tin can']
)

TASTE = Command(
    "Taste a thing",
    CommandPattern.VERB_AND_OBJECT,
    ['taste', 'lick'],
    ['taste your lint', 'taste the door']
)

UNLOCK = Command(
    "Unlock a locked thing",
    "{verb} {object}[ with {object_arg:None}]",
    ['unlock', 'force open', 'pry open'],
    ['unlock the door with the metal key', 'force open the chest with the pry bar']
)

ENTER = Command(
    "Enter a room",
    CommandPattern.VERB_AND_OBJECT,
    ['enter', 'penetrate', 'run in to', 'run into', 'run through', 'sally forth towards', 'go into' ,'go in to', 'go to', 'go'],
    ['enter the dining room', 'run through the door', 'penetrate the arboretum']
)

SAY = Command(
    "Say somthing out loud",
    '{verb} "{string_arg}"[ to {object:any}]',
    ['say', 'speak', 'announce', 'yell', 'scream', 'whisper'],
    ['say "abracadabra"', 'whisper "password" to door', 'say "you are an idiot" to the vagabond']
)

PUT_IN = Command(
    "Put a thing in a container",
    '{verb} {object_arg} in {object}',
    ['put', 'place', 'store', 'sequester'],
    ['put the knife in the cabinet', 'store the scroll in the chest', 'sequester the Congress in Hell']
)