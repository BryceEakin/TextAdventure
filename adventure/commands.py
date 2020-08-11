import abc
import typing as typ

import inspect, functools
from collections import defaultdict
from .enums import Match
from .constants import CURRENT_OBJECT_WORDS

import re

GameEntity = "adventure.base.GameEntity"

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

class _CommandContext():
    def __init__(self, player, current_context_obj=None, addl_contexts = []):
        self._player = player
        self._current_context_obj = current_context_obj
        self._addl_contexts = addl_contexts or []
        
        self.reset_context()
    
    def reset_context(self, cls_limit=None, exclude_objs=None, limit_to=None):
        self._search_context = [self._player.inventory, self._player.room] + self._addl_contexts + ([] if self._current_context_obj is None else [self._current_context_obj])
        self._cls_limit = cls_limit
        self._exclude_objs = exclude_objs
        self._limit_to = limit_to
    
    @property
    def player(self):
        return self._player
    
    @property
    def room(self):
        return self._player.room
    
    def _match_obj(self, desc: str, look_in: GameEntity) -> typ.Tuple[Match, typ.List[GameEntity]]:
        matches = []
        
        if not hasattr(look_in, "items"):
            return (Match.NoMatch, [])
        
        for item in look_in.items:
            if getattr(item, 'is_secret', False):
                continue
            
            if self._exclude_objs and item in self._exclude_objs:
                continue
            
            if self._cls_limit is not None and not isinstance(item, self._cls_limit):
                continue
            
            if self._limit_to and item not in self._limit_to:
                continue
            
            m = item.matches_name(desc)
            if m == Match.FullWithDetail:
                return (m, [item])
            
            if m != Match.NoMatch:
                matches.append((m, item))
            
        best = max((x[0] for x in matches), default=Match.NoMatch)
        matches = [x[1] for x in matches if x[0] == best]
        
        return (best, matches)
    
    def find_objects(self, desc: str) -> typ.Tuple[Match, typ.List[GameEntity]]:
        best_m = Match.NoMatch
        best_objs = []
        
        desc = desc.lower().strip()
        if desc in CURRENT_OBJECT_WORDS and self._current_context_obj is not None and self._current_context_obj in self._search_context:
            return Match.Full, [self._current_context_obj]
        
        for ctx in self._search_context:
            m, objs = self._match_obj(desc, ctx)
            
            if m > best_m:
                best_m, best_objs = m, objs
            elif m == best_m:
                best_objs.extend(objs)
            
        return best_m, list(set(best_objs))
    
    def available_objects(self):
        for ctx in self._search_context:
            if not hasattr(ctx, 'items'):
                continue
            
            for item in ctx.items:
                if item.is_secret:
                    continue
                
                if self._exclude_objs and item in self._exclude_objs:
                    continue
                
                if self._cls_limit is not None and not isinstance(item, self._cls_limit):
                    continue
                
                if self._limit_to and item not in self._limit_to:
                    continue
                
                yield item
                
            yield ctx
    
    def narrow_context(self, obj):
        self._search_context = [obj]

class Command():
    _DEFERRED_CLASS_REGISTERS = []
    _REGISTERED_CLASS_LISTENERS = defaultdict(list)
    _REGISTERED_GENERIC_LISTENERS = defaultdict(list)
    _REGISTERED_OBJECT_LISTENERS = defaultdict(list)
    _REGISTERED_OBJECT_EXCLUSIONS = defaultdict(list)
    
    _KNOWN_COMMANDS = []
    
    def __init__(self,
                 description: str,
                 pattern: str,
                 verbs: typ.List[str],
                 args_list: typ.List[str] = [],
                 examples: typ.List[str] = []
                 ):
        self.description = description
        self.parser = _parse_pattern(pattern, verbs)
        self.pattern = pattern
        self.verbs = verbs
        self.args_list = args_list
        self.examples = examples
        
        Command._KNOWN_COMMANDS.append(self)

    def __call__(self, fn):
        cls = _get_class_that_defined_method(fn)
        
        if cls is None:
            Command._DEFERRED_CLASS_REGISTERS.append((self, fn))
        elif not any(x.__name__ == 'GameEntity' for x in cls.mro()):
            raise ValueError(
                "Can only be used as a decorator on functions in GameEntity subclasses.  Use .register_*() functions instead"
            )
        else:
            Command._REGISTERED_CLASS_LISTENERS[(self, cls)].append(fn)
        
        return fn

    def __repr__(self):
        return f"<Command: {self.description}>"

    @property
    def help_string(self):
        result = self.description + ":\n"
        result += "  - " + ', '.join(self.verbs)
        
        if self.examples:
            result += "\n\n Ex: " + ', '.join('"' + x + '"' for x in self.examples)
        return result

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
       
    @staticmethod
    def _run_search(text, context, cmd_obj, handlers, cls=None):
        match, match_info = cmd_obj.parser.parse(text, context)
        match_info['command'] = cmd_obj
        
        if match == Match.NoMatch:
            handlers = []
        
        # Make the handler apply to the specific object if there is one
        if 'object' in match_info and match_info['object'] is not None:
            if cls and not isinstance(match_info['object'], cls):
                return Match.NoMatch, {}
            
            handlers = [h.__get__(match_info['object'], match_info['object'].__class__) for h in handlers]
        elif cls is not None:
            return Match.NoMatch, {}
            
        if cls:
            match_info['class_matched'] = cls
            
        # Add the command arguments to the handler if the command requires them
        if cmd_obj.args_list:
            if any(arg not in match_info for arg in cmd_obj.args_list):
                handlers = []
                match = Match.NoMatch
                # print("Matched command, but not all args found?", cmd_obj, match_info)
            else:
                handlers = [functools.partial(h, *([context.player] + [match_info[k] for k in cmd_obj.args_list])) for h in handlers]
        else:
            handlers = [functools.partial(h, *[context.player]) for h in handlers]
            
        match_info['handlers'] = handlers
        
        return match, match_info
       
    @staticmethod     
    def evaluate_command(text, player, current_context_obj = None):
        context = _CommandContext(player, current_context_obj=current_context_obj)
        run_search = functools.partial(Command._run_search, text, context)
        
        while Command._DEFERRED_CLASS_REGISTERS:
            cmd, fn = Command._DEFERRED_CLASS_REGISTERS.pop()
            
            cls = _get_class_that_defined_method(fn)
            if cls is not None:
                Command._REGISTERED_CLASS_LISTENERS[(cmd, cls)].append(fn)
            else:
                print(fn)
                print(fn.__qualname__)
                print(dir(fn))
                raise NotImplementedError("Can't find class in which method was defined")
                
        
        best_match_type, best_match_list = Match.NoMatch, []
        
        for (cmd_obj, target_cls), handlers in Command._REGISTERED_CLASS_LISTENERS.items():
            context.reset_context(cls_limit=target_cls, exclude_objs=Command._REGISTERED_OBJECT_EXCLUSIONS[target_cls])
            match, match_info = run_search(cmd_obj, handlers, target_cls)
            
            if match > best_match_type:
                best_match_type, best_match_list = match, [match_info]
            elif match == best_match_type:
                was_found = False
                for idx in range(len(best_match_list)):
                    if 'object' in best_match_list[idx] and best_match_list[idx]['object'] == match_info['object']:
                        was_found = True
                        if issubclass(target_cls, best_match_list[idx]['class_matched']):
                            best_match_list[idx] = match_info
                if not was_found:
                    best_match_list.append(match_info)
        
        for (cmd_obj), handlers in Command._REGISTERED_GENERIC_LISTENERS.items():
            context.reset_context()
            match, match_info = run_search(cmd_obj, handlers)
            
            if match > best_match_type:
                best_match_type, best_match_list = match, [match_info]
            elif match == best_match_type:
                best_match_list.append(match_info)
        
        for (cmd_obj, obj), handlers in Command._REGISTERED_OBJECT_LISTENERS.items():
            context.reset_context(limit_to = [obj])
            match, match_info = run_search(cmd_obj, handlers)
            
            if match > best_match_type:
                best_match_type, best_match_list = match, [match_info]
            elif match == best_match_type:
                best_match_list.append(match_info)
            
        if best_match_type == Match.NoMatch:
            best_match_list.clear()
            
        return best_match_type, best_match_list

def get_help_string(verb=None):
    results = []
    
    if verb:
        verb = verb.lower().strip()
        
        for cmd in Command._KNOWN_COMMANDS:
            if verb in cmd.verbs:
                return cmd.help_string
        
        results.append(f"Couldn't find specific results matching '{verb}'...")
    
    for cmd in Command._KNOWN_COMMANDS:
        results.append(cmd.help_string)
        
    return '\n\n\n'.join(results)

class _ParseToken(abc.ABC):
    def __init__(self, children):
        self._children = children
        if children is None or len(children) == 0 or all(x is None for x in children):
            self._children = [None, None]
        
    @abc.abstractmethod
    def parse(self, txt, context): pass
    
    @property
    def _parse_first(self):
        return False or any(x is not None and x._parse_first for x in (self._children or []))
    
    def _parse_children(self, txt_list, context):
        res = {}
        match = True
        
        if self._children is None:
            return match, res
        
        child_txts = list(zip(self._children, txt_list))
        child_txts.sort(key=lambda x: 1 if x[0] is None or not x[0]._parse_first else 0)
        
        for child, txt in child_txts:
            if child is None:
                if txt is None or txt.strip() == '':
                    continue
                
                return False, {}
            
            child_match, child_res = child.parse(txt, context)
            
            match = match and child_match
            res.update(child_res)
            
        return match, res

def _eval_default(default_text, context):
    default_text = default_text.lower()
    
    if default_text == 'any':
        opts = list(context.available_objects())
        if opts and len(opts) > 0:
            return True, opts[0]
        return False, None
    
    if default_text == 'room':
        return True, context.room
    
    if default_text == 'none':
        return True, None
    
    return False, None

class _OptionalToken(_ParseToken):
    def __init__(self, inner_token, default_vals={}):
        super().__init__([])
        self.token = inner_token
        self.default_vals = default_vals
        
    def parse(self, text, context):
        bits = text.split(' ')
        
        for l_idx in range(0, (1 if self._children[0] is None else len(bits)+1)):
            for r_idx in range(len(bits), (len(bits)-1 if self._children[1] is None else l_idx-1), -1):
                l_text = ' '.join(bits[0:l_idx])
                r_text = ' '.join(bits[r_idx:])
                
                child_match, res = self._parse_children([l_text, r_text], context)
                if not child_match:
                    continue
        
                if ''.join(bits[l_idx:r_idx]).strip() == '':
                    for k, v in self.default_vals.items():
                        m, eval_v = _eval_default(v, context)
                        if not m:
                            return False, None
                        res[k] = eval_v
                    return child_match, res
        
                m, c_res = self.token.parse(''.join(bits[l_idx:r_idx]), context)
                if m:
                    res.update(c_res)
                    return True, res
        
        return False, {}

class _MultiMatchToken(_ParseToken):
    def __init__(self, options, l_child, r_child, name='verb'):
        super().__init__([l_child, r_child])
        self.options = [o.lower() for o in options]
        self.name = name
        
    def parse(self, txt, context):
        txt = txt.lower()
        
        for opt in self.options:
            if opt not in txt:
                continue
            
            splits = txt.split(opt)
            
            for i in range(0, len(splits)):
                match, res = self._parse_children([
                    opt.join(splits[:i]),
                    opt.join(splits[i:])
                ], context)
            
                if match:
                    res[self.name] = opt
                    return match, res
        
        return False, {}

class _StringArg(_ParseToken):
    def __init__(self):
        super().__init__([])
    
    def parse(self, text, context):
        if text is None or text.strip() == '':
            return False, {}
        
        return True, {'arg': text}

class _MatchObject(_ParseToken):
    def __init__(self, entity_name, l_child, r_child):
        super().__init__([l_child, r_child])
        self.entity_name = entity_name
        
    def parse(self, text, context):
        text = text.lower().strip()
        if text == '':
            return False, {}
        
        bits = text.split(' ')
        
        for l_idx in range(0, (1 if self._children[0] is None else len(bits)+1)):
            for r_idx in range(len(bits), (len(bits)-1 if self._children[1] is None else l_idx-1), -1):
                l_text = ' '.join(bits[0:l_idx])
                r_text = ' '.join(bits[r_idx:])
                
                child_match, res = self._parse_children([l_text, r_text], context)
                if not child_match:
                    continue
        
                match, opts = context.find_objects(''.join(bits[l_idx:r_idx]))
                if opts:
                    res[self.entity_name] = opts[0]
                    return True, res
        return False, {}

class _ObjectInToken(_MatchObject):
    def __init__(self, l_child, r_child):
        super().__init__('object_in', l_child, r_child)
        
    @property
    def _parse_first(self):
        return True
        
    def parse(self, text, context):
        m, res = super().parse(text, context)
        context.narrow_context(res['object_in'])
        
        return m, res

class _FixedTextToken(_ParseToken):
    def __init__(self, pattern, l_child, r_child):
        super().__init__([l_child, r_child])
        self._pattern = pattern.lower()
        
    def parse(self, text, context):
        text = text.lower()
        if text == '':
            return self._parse_children(['', ''], context)
        
        if self._pattern not in text:
            return False, {}
        
        splits = text.split(self._pattern)
        
        for i in range(1, len(splits)):
            m, res = self._parse_children([
                self._pattern.join(splits[:i]), 
                self._pattern.join(splits[i:])
            ], context)
            
            if m:
                return m, res
                
        return False, {}

def _inner_parse_pattern(pattern, verbs, verbose=False, print_prefix=''):
    pattern = pattern.strip().lower()
    
    # print("Parsing", pattern)
    
    if verbose:
        print(print_prefix + "-'" + pattern + "'")
    
    if pattern == '':
        return None, {}
    
    # Parse {object}, {object:any}, {object_arg}, {object_arg:room}, {string_arg}, etc
    if re.match("^\\{[^\\}]+\\}$", pattern):
        if pattern[1:-1] == 'verb':
            return _MultiMatchToken(verbs, None, None), {}
        
        split = pattern[1:-1].split(":", 1)
        
        entity = split[0]
        if len(split) == 1:
            default = {}
        else:
            default = {entity: split[1]}
        
        if entity == 'object':
            return _MatchObject(entity, None, None), default
        if entity == 'object_arg':
            return _MatchObject('arg', None, None), default
        if entity == 'string_arg':
            return _StringArg(), default
        if entity == 'object_in':
            return _ObjectInToken(None, None), default
        
        print("Failed to parse", entity)
        return None, {}
        
    # Handle if this block is optional
    is_optional = False
    if pattern[0] == '[' and pattern[-1] == ']':
        is_optional = True
        pattern = pattern[1:-1]
    
    
    # Break text into optional blocks, then fixed text and entities
    bits = []
    bits = re.split("(\\[[^\\]]+\\])", pattern)
    bits = sum(([x] if x.startswith('[') else re.split("(\\{[^\\}]+\\})", x) for x in bits), [])
    bits = [x for x in bits if x.strip() != '']
    
    are_fixed = [(x != '' and x[0] not in {'{', '['}) for x in bits]
    
    if verbose:
        print(print_prefix + "  " + repr(bits))
        print(print_prefix + "  " + repr(are_fixed))
    
    # Start by selecting a fixed text bit if available
    if any(are_fixed):
        # Select fixed text in the middle to match first if available
        idxs = list([i for i, x in enumerate(are_fixed) if x])
        idx = idxs[len(idxs)//2]
        
        def_args = {}
        
        # Define parse tree children
        l_child, l_da = _inner_parse_pattern(''.join(bits[:idx]), verbs, verbose, print_prefix + " |")
        r_child, r_da = _inner_parse_pattern(''.join(bits[(idx+1):]), verbs, verbose, print_prefix + " |")
        
        if l_da:
            def_args.update(l_da)
        
        if r_da:
            def_args.update(r_da)
        
        token = _FixedTextToken(bits[idx], l_child, r_child)
        if is_optional:
            token = _OptionalToken(token, def_args)
            
        return token, def_args
    
    idx = len(bits) // 2
    
    l_child, l_da = _inner_parse_pattern(''.join(bits[:idx]), verbs, verbose, print_prefix + " |")
    r_child, r_da = _inner_parse_pattern(''.join(bits[(idx+1):]), verbs, verbose, print_prefix + " |")
    
    token, def_args = _inner_parse_pattern(bits[idx], verbs, verbose, print_prefix + " |")
    if token is None:
        print(bits, idx, verbs, token, def_args)
    
    if l_da:
        def_args.update(l_da)
        
    if r_da:
        def_args.update(r_da)
        
    if is_optional:
        token = _OptionalToken(token, def_args)
    
    token._children = [l_child, r_child]
    return token, def_args
    

def _parse_pattern(pattern, verbs):
    token, _ = _inner_parse_pattern(pattern, verbs)
    return token
    
class CommandPattern():
    JUST_VERB = "{verb}"
    VERB_AND_OBJECT = "{verb} {object}"

LOOK = Command(
    "Examine an item or your surroundings",
    "{verb}[ {object:room}]",
    ['look', 'look around', 'look at', 'look inside', 'look in', 'examine', 'scrutinize'],
    examples=["look around", "look in bag", "look at the tin can"]
)

TAKE = Command(
    "Take something and add it to your inventory",
    "{verb} {object} [from {object_in:room}]",
    ['take', 'get', 'pick up', 'acquire', 'grab','snatch'],
    examples=["take sword", "pick up coins", "snatch lint from the bag"]
)

DISCARD = Command(
    "Discard an item",
    CommandPattern.VERB_AND_OBJECT,
    ['drop', 'get rid of', 'lose', 'discard', 'ditch'],
    examples=["drop string", "ditch the broadsword"]
)

SHOW_INVENTORY = Command(
    "Show the player's inventory",
    CommandPattern.JUST_VERB,
    ['i', 'inventory', 'show inventory', 'what do i have'],
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
    args_list=['object_arg'],
    examples=['open the door', 'open the chest with the crowbar']
)

HELP = Command(
    "See game help",
    "{verb}[ with][ {string_arg:None}]",
    ['help', 'what do i do', '?', 'ugg'],
    args_list=['string_arg']
)

SMELL = Command(
    "Smell a thing",
    CommandPattern.VERB_AND_OBJECT,
    ['smell', 'sniff'],
    examples=['smell yourself', 'smell the tin can']
)

TASTE = Command(
    "Taste a thing",
    CommandPattern.VERB_AND_OBJECT,
    ['taste', 'lick'],
    examples=['taste your lint', 'taste the door']
)

UNLOCK = Command(
    "Unlock a locked thing",
    "{verb} {object}[ with {object_arg:None}]",
    ['unlock', 'force open', 'pry open'],
    args_list=['object_arg'],
    examples=['unlock the door with the metal key', 'force open the chest with the pry bar']
)

ENTER = Command(
    "Enter a room",
    CommandPattern.VERB_AND_OBJECT,
    ['enter', 'penetrate', 'run in to', 'run into', 'run through', 'sally forth towards', 'go into' ,'go in to', 'go to', 'go'],
    examples=['enter the dining room', 'run through the door', 'penetrate the arboretum']
)

SAY = Command(
    "Say somthing out loud",
    '{verb} "{string_arg}"[ to {object:room}]',
    ['say', 'speak', 'announce', 'yell', 'scream', 'whisper'],
    args_list=['string_arg'],
    examples=['say "abracadabra"', 'whisper "password" to door', 'say "you are an idiot" to the vagabond']
)

PUT_IN = Command(
    "Put a thing in a container",
    '{verb} {object_arg} in {object}',
    ['put', 'place', 'store', 'sequester'],
    args_list=['object_arg'],
    examples=['put the knife in the cabinet', 'store the scroll in the chest', 'sequester the Congress in Hell']
)