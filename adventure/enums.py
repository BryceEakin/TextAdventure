import enum

class Match(enum.IntEnum):
    NoMatch = 0,
    Incomplete = 1,
    Partial = 2,
    Full = 3,
    FullWithDetail = 4