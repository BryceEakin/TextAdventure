import enum

class Match(enum.IntEnum):
    NoMatch = 0,
    Partial = 1,
    Full = 2,
    FullWithDetail = 3