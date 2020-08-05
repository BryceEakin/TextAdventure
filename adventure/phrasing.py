from .utils import select_one
import typing as typ

def natural_list(descs: typ.List[str], oxford_comma=False) -> str:
    if len(descs) == 0:
        return "Nothing"
    if len(descs) == 1:
        return descs[0]
    if len(descs) == 2:
        return descs[0] + (',' if oxford_comma else '') + " and " + descs[1]
    return descs[0] + ", " + natural_list(descs[1:], oxford_comma=True)


_DARK_ROOM = [
    "It's pitch black.",
    "It's so dark you can't see your own hands.",
    "You feel around but can't see a thing and are hopelessly turned around.",
    "Unless you get some light in here, you ain't seeing shit."
]

def dark_room():
    return select_one(_DARK_ROOM)


_ITEM_DESCRIPTIONS = [
    "There {2} {0} {1}.",
    "{1} you see {0}.",
    "{0} {2} {1}."
]
    
def describe_items(items: typ.List["adventure.base.GameItem"]) -> str:
    groups = {}
    if len(items) == 0:
        return ''
    
    for item in items:
        grp = groups.get(item.location, [])
        groups[item.location] = grp
        grp.append(item)
        
    descs = []
    for loc, grp in groups.items():
        desc = select_one(_ITEM_DESCRIPTIONS).format(
            natural_list([x.short_description for x in grp]),
            loc,
            grp[0].verb if len(grp) == 1 else "are"
        )
        
        descs.append(desc[0].upper() + desc[1:])
        
        
    return " ".join(descs)
    
_BAD_PERSON_SMELLS = [
    "sniff... sniff... Yeah, {0} could use a bath...",
    "Oooh, that's ripe.",
    "Maybe invest in some soap.  Or at least a clothespin for your nose.  Geez....",
    "The bouquet is rather complex, reminding you of wet garbage, left out for a several days."
]

def foul_smelling_person(is_you: bool = False):
    return select_one(_BAD_PERSON_SMELLS).format('you' if is_you else 'they')

_NOTHING_HAPPENS = [
    "... Nothing happens.",
    "(cricket)....   (cricket)....   ",
    "It wasn't very effective.",
    "Oh, sorry, was that supposed to make sense?  It didn't.",
    "A tiny ripple moves out possibly affecting something somewhere eventually.  Just not here or now.",
    "Yeah, that really didn't do anything"
]

def nothing_happens():
    return select_one(_NOTHING_HAPPENS)