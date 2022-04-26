import struct
import numpy as np

BASE_ADDRESS = 0x08000000

# Build a contiguous memory region
mem_region = lambda address, size: slice(address,address+size)
# Offset region by  base address (REAL)
mem_offset = lambda base_address, key: \
                    slice(key.start+base_address, 
                          key.stop +base_address,
                          key.step)
# Real (Ex. [0800:0000h:0800:1000h]) to Virtual ([0:1000])
real_to_virt = lambda key: mem_offset(-BASE_ADDRESS,key)
virt_to_real = lambda key: mem_offset(+BASE_ADDRESS,key) 
is_virt_address = lambda region, key: ((key.start or 0) - region.start) < 0
is_real_address = lambda region, key: not is_virt_address(region,key)

class MemoryEmulator:
    def __init__(self, payload, region=None, p_size=4, endian='<'):
        if type(payload) is str:
            self._payload = self.read(payload)
        elif type(payload) is bytearray:
            self._payload = payload
        self.pointer_size = p_size
        if p_size == 4:
            self._ptr_pfx = 'I'
        if p_size == 8:
            self._ptr_pfx = 'Q'
        self.endian = endian
        self.region = region if region != None else mem_region(BASE_ADDRESS,len(self._payload))

    def read(self,filename):
        with open(filename,'rb') as f:
            payload = bytearray(f.read())
        return payload

    def write(self,filename):
        with open(filename,'wb') as f:
            f.write(self._payload)

    def __len__(self):
        return self.region.stop - self.region.start

    def __getitem__(self, key):
        virt_key = key if is_virt_address(self.region,key) \
                  else real_to_virt(key)
        real_key = key if is_real_address(self.region,key) \
                  else virt_to_real(key)
        return MemoryEmulator(self._payload[virt_key],
                  region=real_key,
                  p_size=self.pointer_size,
                  endian=self.endian)

    def __setitem__(self, key, value):
        virt_key = key if is_virt_address(self.region,key) else real_to_virt(key)
        self._payload[virt_key] = value

    def read_pointers(self, number=1, **kwargs):
        fmt      = f'{self.endian}{number}{self._ptr_pfx}'
        pointers = self.read_struct(fmt, **kwargs)
        return pointers

    def read_struct(self, fmt, **kwargs):
        size    = struct.calcsize(fmt)
        payload = self.read_bytes(size, **kwargs)
        data    = struct.unpack(fmt,payload)
        return data if len(data) > 1 else data[0]

    def read_array(self, shape, dtype='B', **kwargs):
        dt      = np.dtype(f'{shape}{dtype}')
        dt      = dt.newbyteorder(self.endian)
        size    = dt.itemsize
        payload = self.read_bytes(size, **kwargs)
        matrix  = np.frombuffer(payload,dtype=dt).flatten().reshape(shape)
        return matrix

    def read_integer(self, number=1, dtype='I', **kwargs):
        fmt     = f'{self.endian}{number}{dtype}'
        integers = self.read_struct(fmt, **kwargs)
        return integers 

    def read_bytes(self, size, offset=0):
        key = mem_region(offset,size)
        virt_key = key if is_virt_address(self.region,key) \
                       else real_to_virt(key)
        payload = self._payload[virt_key]
        return payload
        

