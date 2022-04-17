from ygogxda.rom import YugiohROM
from ygogxda.utils import text_padding 

ROM_FILENAME    = 'yugioh_gx_duel_academy.gba'
SAMPLE_FILENAME = 'card_custom_zeszin.png'

def main():
    ygo = YugiohROM(ROM_FILENAME)
    # Check game title field
    assert(ygo.game_title == 'YUGIOHGXDA')

    # Input a wrong password
    card_id = ygo.passwords.enter('WRONGPASS')
    assert(card_id == 0)
    # Unlocks "Calamity of the Wicked"
    password = ygo.passwords.unlock(719)
    assert(password == '01224927')
    card_id = ygo.passwords.enter(password)
    # Consistency tests
    assert(card_id == 719)
    assert(ygo.card_names[card_id] == 'Calamity of the Wicked')
    assert(ygo.card_texts[card_id] == \
            "Can be activated when your opponent's Monster attacks. "
            "Destroys all Spell and Trap cards on the Field.")

    # Loop over and extract card artworks
    for idx,artwork in enumerate(ygo.card_images):
        artwork.save(f"/tmp/card-{idx:04d}.png")

    # Patch 1 - Change Mystic Elf artwork
    from PIL import Image
    import numpy as np

    # Get the memory region for this card 
    card_bitmap = ygo.card_image(2)

    # Open a image
    new_artwork = Image.open(SAMPLE_FILENAME)

    # FIXME ok this is too awk...
    data = new_artwork.getdata()
    data = np.array(data).reshape(80,80)
    # FIXME How to explain this???
    blocks = np.array([np.hsplit(split,10) for split in np.vsplit(data,10)])
    new_data = list(blocks.flatten())
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
    # Analogous process...
    card_name = ygo.card_name(2)
    new_text = 'zeszinCoringa'
    # Pad the custom text with zeros
    padding  = b'\x00' * (len(card_name) - len(new_text))
    # Overwrite memory region
    card_name[:] = bytes(new_text,'ascii') + padding
    # Apply second patch!
    ygo.patch(card_name)

    # Some direct tweeks!
    licensed = ygo.rom[YugiohROM.LICENSED_BY_1]
    licensed[:] = text_padding("SEEEGAAAA... no wait!",len(licensed))
    ygo.patch(licensed)
    licensed = ygo.rom[YugiohROM.LICENSED_BY_2]
    licensed[:] = text_padding("SEEEGAAAA... no wait!",len(licensed))
    ygo.patch(licensed)

    # Save it and it's done!
    ygo.save('/tmp/zeszinLUL.gba')

if __name__ == '__main__':
    main()
