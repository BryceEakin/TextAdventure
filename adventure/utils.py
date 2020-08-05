import random
import typing as typ

def select_one(items: typ.List[str]) -> str:
    if isinstance(items, str):
        return items
    
    return random.choice(items)