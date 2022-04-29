class YugiohGraphics:
    def __init__(self, bitmaps, palettes):
        self.bitmaps   = bitmaps
        self.palettes  = palettes

    def artworks(self):
        bmp = self.bitmaps.reshape(1201,10,10,8,8)
        pal = self.palettes
        for idx in range(self.num_cards):
            bitmap  = bmp[idx]
            palette = pal[idx]
            blocks = [[bitmap[i,j] for j in range(10)]
                                   for i in range(10)]
            array = np.block(blocks)
            image = Image.fromarray(array)
            image.putpalette(palette, rawmode="RGB;15")
            yield image
