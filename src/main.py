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
    thumbdata = ygo.location_thumbs()
    # Loop over each variation
    for period, images in zip(periods,thumbdata):
        # Loop over each location
        for idx, image in enumerate(images):
            # Save it!
            image.save(f"/tmp/bg-{period}-{idx:04d}.png")

def example_extract_duelist_sprites(ygo):
    for duelist_index, variations in enumerate(ygo.duelist_sprites()):
        # Loop over each location
        for variation_index, image in enumerate(variations):
            # Save it!
            image.save(f"/tmp/duelist-{duelist_index:02d}-variation-{variation_index}.png")

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

def main():
    ygo = YugiohROM(ROM_FILENAME)
    assert(ygo.game_title == 'YUGIOHGXDA')
    assert ygo.game_code in ('BYGE', 'BYGP')

    example_patch_card(ygo)
    example_password_handling(ygo)
    example_extract_card_artwork(ygo)
    example_extract_duelist_sprites(ygo)
    example_extract_places_thumbnail(ygo)

if __name__ == '__main__':
    main()
