from dataclasses import dataclass
import typing as typ

@dataclass(frozen=True)
class Material():
    """Describes a material which objects, surfaces, etc can be made of
    """
    name: str
    smell: typ.Union[str, typ.List[str]] = None
    taste: typ.Union[str, typ.List[str]] = None
    combustible: bool = False
    fragile: bool = False
    consumable: bool = False
    solid: bool = True

DEFAULT = Material(name="non-descript")

METAL = Material(name="metal", 
                 smell=["metallic", "like rust"], 
                 taste="metallic")

RUSTY_TIN = Material(name="rusty tin", 
                     smell=["like rust"],
                     taste=["sharp... maybe you shouldn't taste it anymore", "metallic", "rusty"])

BRITTLE_METAL = Material(name="metal", 
                         smell=["metallic", "like rust"], 
                         taste="metallic",
                         fragile=True)

STONE = Material(name="stone",
                 smell=["earthy", "...rocky? rocky", "stoned"],
                 taste=["earthy"])

CONCRETE = Material(name="concrete")
DIRT = Material(name="dirt", 
                smell=["earthy", "like the great outdoors", "like glorious worm poo"],
                taste=["earthy", "like the physical manifestation of the idea 'why did I just taste dirt'"])
MUD = Material(name="mud",
               smell="muddy",
               taste="like you need a mental exam for tasting mud.  It's mud, bro",
               solid=False)

WOOD = Material(name="wood",
                smell=["of pine", 
                       "of cherry",
                       "faintly of eucalyptus",
                       "strongly of cedar",
                       "of hickory", 
                       "like baking ham"],
                taste="pulpy",
                combustible=True)

GLASS = Material(name="glass",
                 fragile=True)

WATER = Material(name="water",
                 smell="like water",
                 taste="like water",
                 solid=False,
                 consumable=True)

ICE = Material(name="ice",
               smell="like cold water",
               taste="an unflavored popsicle",
               fragile=True)

THICK_ICE = Material(name="thick ice",
                     smell="like cold water",
                     taste="an unflavored popsicle",
                     fragile=False)

LEATHER = Material(name="leather")
PAPER = Material(name="paper", combustible=True)
CARDBOARD = Material(name="cardboard", combustible=True)

