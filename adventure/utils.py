import random
import typing as typ

from .constants import STOP_WORDS
from .enums import Match

import re

from nltk.metrics.distance import jaro_winkler_similarity

def select_one(items: typ.List[str]) -> str:
    if isinstance(items, str):
        return items
    
    return random.choice(items)

def is_rough_match(text, name, thresh = 0.8):
    
    text = text.lower()
    name = name.lower()
    
    for sw in STOP_WORDS:
        text = re.sub(' +', ' ', re.sub('(^| )' + sw + '($| )', ' ', text)).strip()
        name = re.sub(' +', ' ', re.sub('(^| )' + sw + '($| )', ' ', name)).strip()
    
    if text == name:
        return Match.Full
    
    splits = name.split(' ')
    
    for i in range(len(splits)):    
        if text == ' '.join(splits[i:]):
            return Match.Partial
        
        if jaro_winkler_similarity(text, ' '.join(splits[i:])) > thresh:
            return Match.Partial
    
    return Match.NoMatch
    