from .utils import charset_decode

class GBAHeader:
    """
    This class holds the GBA header information, as follows:

    | start | size | asm dt | C dt      | field name       | description
    | ------|------|--------|---------- |----------------- |-------------------
    | 0     |   4  | addr   | pointer   | rom_entry_point  | Branch entry point
    | 4     | 156  | db[156]| byte[156] | nintendo_logo    | Nintendo Logo
    | 160   |  12  | ds     | string    | game_title       | Game Title
    | 172   |   4  | ds     | string    | game_code        | Game Code
    | 176   |   2  | char[2]| char[2]   | maker_code       | Maker Code
    | 178   |   1  | db     | byte      | fixed_value      | Fixed Value
    | 179   |   1  | db     | byte      | main_unit_code   | Main Unit Code
    | 180   |   1  | db     | byte      | device_type      | Device Type
    | 181   |   7  | db[7]  | byte[7]   | reserved         | Reserved area
    | 188   |   1  | db     | byte      | software_vers    | Software Version
    | 189   |   1  | db     | byte      | complement_check | Complement Check
    | 190   |   2  | db[2]  | byte[2]   | reserved2        | Reserved area
    """
    STRUCT_FMT = '<I156s12s4s2s1b1b1b7s1b1b2s'
    def __init__(self, data):
        fields = ('rom_entry_point', 'nintendo_logo',    'game_title',
                  'game_code',       'maker_code',       'fixed_value',
                  'main_unit_code',  'device_type',      'reserved',
                  'software_vers',   'complement_check', 'reserved2')
        for idx, field in enumerate(fields):
            setattr(self, field, data[idx])

