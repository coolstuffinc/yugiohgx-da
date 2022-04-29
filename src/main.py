from ygogxda.rom import YugiohROM
from ygogxda.memory import mem_region
from ygogxda.utils import text_padding, \
                          split_blocks, \
                          join_blocks

ROM_FILENAME    = 'yugioh_gx_duel_academy.gba'
SAMPLE_FILENAME = 'card_custom_zeszin.png'

def example_patch_card(ygo):
    # Patch 1 - Change Mystic Elf artwork
    from PIL import Image
    import numpy as np

    # Get the memory region for this card
    card_bitmap = ygo.card_image(2)

    # Open a image
    new_artwork = Image.open(SAMPLE_FILENAME)

    # FIXME ok this is too awk...
    data = new_artwork.getdata()
    # Square the bitmap
    data = np.array(data).reshape(80,80)
    # FIXME How to explain this???
    new_data = split_blocks(data,(10,10))
    new_data = list(new_data.flatten())
    # Write the memory region, mind the "[:]"
    card_bitmap[:] = new_data

    # Patch it!
    ygo.patch(card_bitmap)

    # Patch 2 - Change Mystic Elf card text
    # Get the card text memory region
    card_text = ygo.card_text(2)
    # Build new patched text (It is important to keep the same size)
    new_text = 'WhySoSerious? zeszinLUL'
    # Pad the custom text with zeros
    padding  = b'\x00' * (len(card_text) - len(new_text))
    # Overwrite memory region
    card_text[:] = bytes(new_text,'ascii') + padding

    # Apply second patch!
    ygo.patch(card_text)

    # Patch 3 - Change Mystic Elf card name
    # Analogous process... this time using a helper
    card_name = ygo.card_name(2)
    card_name[:] = text_padding('zeszinCoringa',len(card_name))
    # Apply second patch!
    ygo.patch(card_name)

    # Some direct tweeks! using a helper to pad the string this time!
    licensed = ygo.rom[YugiohROM.LICENSED_BY_1]
    licensed[:] = text_padding("SEEEGAAAA... no wait!",len(licensed))
    # patch
    ygo.patch(licensed)
    licensed = ygo.rom[YugiohROM.LICENSED_BY_2]
    licensed[:] = text_padding("SEEEGAAAA... no wait!",len(licensed))
    # patch
    ygo.patch(licensed)

    # Save it and it's done!
    ygo.save('/tmp/zeszinLUL.gba')

def example_extract_card_artwork(ygo):
    # Loop over and extract card artworks
    for idx,artwork in enumerate(ygo.card_images):
        artwork.save(f"/tmp/card-{idx:04d}.png")

def example_password_handling(ygo):
    # Input a wrong password
    card_id = ygo.passwords.enter('WRONGPASS')
    assert(card_id == 0)
    # Find the card id for a given card name
    card_id = ygo.card_names.index("Calamity of the Wicked")
    assert(card_id == 719)
    # Retrieve the password for the card id
    password = ygo.passwords.unlock(card_id)
    assert(password == '01224927')
    # Enter the reversed password and get the unlocked card_id
    card_id = ygo.passwords.enter(password)
    # Ensure the unlocked card id is what we were looking for
    assert(card_id == 719)
    assert(ygo.card_names[card_id] == 'Calamity of the Wicked')
    assert(ygo.card_texts[card_id] ==
            "Can be activated when your opponent's Monster attacks. "
            "Destroys all Spell and Trap cards on the Field.")

def example_extract_places_thumbnail(ygo):
    periods = ['morning', 'afternoon', 'night']
    thumbdata = ygo._read_places_thumb()
    # Loop over each variation
    for period, images in zip(periods,thumbdata):
        # Loop over each location
        for idx, image in enumerate(images):
            # Save it!
            image.save(f"/tmp/bg-{period}-{idx:04d}.png")

def example_extract_duelist_sprites(ygo):
    duelist_sprites = ygo._read_duelists_sprites()
    for variations in duelist_sprites:
        # Loop over each location
        for image in variations:
            # Save it!
            image.save(f"/tmp/duelist-{id(variations)}-{id(image)}.png")

def example_test(ygo):
    from PIL import Image
    """
    load_memory_512__________(MEM_VRAM_BACK + 0x5cc0, 0x09458458, 10, 2);
    load_data_in_word_chuncks(PALETTE_p_200 + 0x10,   0x09514d40,    32);
    """
    mem_bitmap  = ygo.rom[0x0945c958:]
    mem_palette = ygo.rom[0x09514d40,32]

    bitmap1 = mem_bitmap1.read_array(2048)
    palette = mem_palette.read_array(32)
    bitmap1 = bitmap1.reshape(8,-1,order='F').T
    image = Image.fromarray(bitmap1)
    image.putpalette(palette, rawmode="RGB;15")
    image.save(f'/tmp/test-{id(image)}.png')

    """
    load_memory_512__________(MEM_VRAM_BACK + 0x6600, 0x0945c958, 12, 5);
    load_memory_512__________(MEM_VRAM_BACK + 0x5ac0, 0x0945d138, 10, 1);
    load_data_in_word_chuncks(PALETTE_p_200 + 0x40,   0x094592f8,    32);
    """
    mem_bitmap1 = ygo.rom[0x0945c958:]
    mem_bitmap2 = ygo.rom[0x0945d138:]
    mem_palette = ygo.rom[0x094592f8,32]
    """
    load_memory_512__________(MEM_VRAM_BACK + 0x3200, 0x09458978, 19, 4);
    load_memory_512__________(MEM_VRAM_BACK + 0x5d80, 0x0945d278,  5, 2);
    load_memory_512__________(MEM_VRAM_BACK + 0x5780, 0x09532fcc
                                                        + 0x1080,  5, 3);
    load_data_in_word_chuncks(PALETTE_p_200 + 0x30,   0x0945c318,    32);
    """
    mem_bitmap1 = ygo.rom[0x09458978:]
    mem_bitmap2 = ygo.rom[0x0945d278:]
    mem_bitmap3 = ygo.rom[0x09532fcc:]
    mem_palette = ygo.rom[0x0945c318,32]

    bitmap1 = mem_bitmap1.read_array(2048)
    palette = mem_palette.read_array(32)
    bitmap1 = bitmap1.reshape(8,-1,order='F').T
    image = Image.fromarray(bitmap1)
    image.putpalette(palette, rawmode="RGB;15")
    image.save(f'/tmp/test-{id(image)}.png')

    bitmap2 = mem_bitmap2.read_array(2048)
    palette = mem_palette.read_array(32)
    bitmap2 = bitmap2.reshape(8,-1,order='F').T
    image = Image.fromarray(bitmap2)
    image.putpalette(palette, rawmode="RGB;15")
    image.save(f'/tmp/test-{id(image)}.png')

    bitmap3 = mem_bitmap3.read_array(2048)
    palette = mem_palette.read_array(32)
    bitmap3 = bitmap3.reshape(8,-1,order='F').T
    image = Image.fromarray(bitmap3)
    image.putpalette(palette, rawmode="RGB;15")
    image.save(f'/tmp/test-{id(image)}.png')

    """
    load_memory_512__________(MEM_VRAM_BACK + 0x6180, 0x090bb858, 8, 8);
    load_data_in_word_chuncks(PALETTE_p_200 + 0x20,   0x0945c938,   32);
    """
    mem_bitmap1 = ygo.rom[0x090bb858,2048]
    mem_palette = ygo.rom[0x0945c938,32]

    bitmap1 = mem_bitmap1.read_array(2048)
    palette = mem_palette.read_array(32)
    bitmap1 = bitmap1.reshape(8,-1,order='F').T
    image = Image.fromarray(bitmap1)
    image.putpalette(palette, rawmode="RGB;15")
    image.save(f'/tmp/test-{id(image)}.png')

    """
    load_data_in_word_chuncks(MEM_VRAM_BACK + 0x58c0, 0x09528fa8, 320);
    load_data_in_word_chuncks(PALETTE_p_200 + 0x70,   0x09529e48,  32);
    """
    mem_bitmap1 = ygo.rom[0x09528fa8,320]
    mem_palette = ygo.rom[0x09529e48, 32]

    bitmap1 = mem_bitmap1.read_array(320)
    palette = mem_palette.read_array(32)
    bitmap1 = bitmap1.reshape(4,-1,order='F').T
    image = Image.fromarray(bitmap1)
    image.putpalette(palette, rawmode="RGB;15")
    image.save(f'/tmp/test-{id(image)}.png')

    """
    load_data_in_word_chuncks(MEM_VRAM_BACK + 0x5960, 0x09529568, 64);
    load_data_in_word_chuncks(PALETTE_p_200,          0x0944d1cc, 32);
    """
    mem_bitmap1 = ygo.rom[0x09529568,64]
    mem_palette = ygo.rom[0x0944d1cc,32]

    bitmap1 = mem_bitmap1.read_array(64)
    palette = mem_palette.read_array(32)
    bitmap1 = bitmap1.reshape(8,-1,order='F').T
    image = Image.fromarray(bitmap1)
    image.putpalette(palette, rawmode="RGB;15")
    image.save(f'/tmp/test-{id(image)}.png')

def _some_4x8_digits_and_icons(ygo):
    # Some
    from PIL import Image
    mem_palette = ygo.rom[mem_region(0x09458958,8*4)]
    mem_bitmap  = ygo.rom[mem_region(0x094586d8,160*4)]
    palette = mem_palette.read_array(4*8)
    bitmap  =  mem_bitmap.read_array(4*160)
    size = bitmap.shape[0]
    bitmap = bitmap.reshape(4,-1,order='F').T
    image = Image.fromarray(bitmap)
    image.putpalette(palette, rawmode="RGB;15")
    image.save(f'/tmp/test-{id(bitmap)}.png')

def _(ygo):
    palettes = self.rom[0x08f61184:0x08f61184+1201*64]
    shape = (1201,64)
    data = palettes.read_array(shape,dtype='B') # words
    return data

    # FIXME under construction: showing the palettes
    #low_bmp = self._read_lo_card_bitmaps()
    #low_pal = self._read_lo_card_palettes()
    #bmp = hires_bmp.reshape(1201,10,10,8,8)
    pal = low_pal.reshape(1201,8,8)
    for idx in range(self.num_cards):
        palette = pal[idx]
        image = Image.new("RGB",palette.shape)
        data = tuple(map(gba2rgb,palette.flatten()))
        image.putdata(data)
        yield image

def main():
    ygo = YugiohROM(ROM_FILENAME)
    assert(ygo.game_title == 'YUGIOHGXDA')
    assert(ygo.game_code == 'BYGE'
        or ygo.game_code == 'BYGP')

    example_test(ygo)
    example_patch_card(ygo)
    example_password_handling(ygo)
    example_extract_card_artwork(ygo)
    example_extract_duelist_sprites(ygo)
    example_extract_places_thumbnail(ygo)

if __name__ == '__main__':
    main()
