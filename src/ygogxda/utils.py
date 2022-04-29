import struct
import operator
import numpy as np

c_declare_format = '''\
const {type} {name}_{address:08x}{size} =
{data};
'''
c_name_format = '{name}_{address:08x}'
c_array_declare = lambda elements: \
        '{ %s }' % (','.join(elements))
c_array_content = lambda payload: \
        c_array_declare('0x%02x' % (byte) for byte in payload)
c_array_generate = lambda data, dtype, address, prefix: \
    c_declare_format.format(**{
        'type': dtype,
        'size': str([len(data)]),
        'data': c_array_content(data) if '*' not in dtype else c_array_declare(data),
        'address': address,
        'name': prefix
    })

sucessive = lambda f, array: f(array[1:], array[:-1])
sucessive_sum = lambda array: sucessive(vectorial_sum,array)
sucessive_sub = lambda array: sucessive(vectorial_sub,array)
vectorial_sub = lambda u, v:  tuple(map(operator.sub, u, v))
vectorial_sum = lambda u, v:  tuple(map(operator.add, u, v))
vectorial_tuple = lambda u: tuple(map(lambda e: (e,), u))
scalar_vector = lambda s: iter(lambda: s,1)

rgb2gba = lambda red, green, blue:    (((  red >> 3) & 31)
                                    | (((green >> 3) & 31) <<  5)
                                    | ((( blue >> 3) & 31) << 10))
gba2rgb = lambda color:  ((color &  31) << 3,       # red
                         ((color >>  5) & 31) << 3, # green
                         ((color >> 10) & 31) << 3) # blue
rgb2int = lambda rgb: (rgb[0] << 16) | (rgb[1] << 8) | rgb[2]

charset_decode = lambda buffer: (
        buffer.replace(b'\xf2\xa4',b'\N{GREEK SMALL LETTER ALPHA}') # ɑ
              .replace(b'\xf0\x80',b'')
              .replace(b'\xf0\xf3',b'')
              .replace(b'\xf0\xae',b'')
              .replace(b'\xf0\x9d',b'')
              .replace(b'\x81\xf4',bytes('♪','utf-8'))
              .replace(b'\x00',b'')
              .decode('utf-8'))

text_padding = lambda string, size: bytes(string,'ascii') + b'\x00' * (size - len(string))

split_blocks = lambda array2D, blocks: np.array([
    np.hsplit(split,blocks[0])
    for split in np.vsplit(array2D,blocks[1])
])

join_blocks = lambda array2D, blocks: np.block([
    [array2D[i,j] for j in range(blocks[1])]
                  for i in range(blocks[0])
])
