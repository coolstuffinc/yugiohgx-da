def japanese_enc_test():
    japanese_encodings = ['cp932', 'euc_jp', 'euc_jis_2004', 'euc_jisx0213', 'iso2022_jp', 'iso2022_jp_1', 'iso2022_jp_2', 'iso2022_jp_2004', 'iso2022_jp_3', 'iso2022_jp_ext', 'shift_jis', 'shift_jis_2004', 'shift_jisx0213']
    japanese_blue_eyes_lil = 0xF284F299F08BF1D0F1D2F1E8F084F289F29DF1D2F1F6F084F1F7F297F1E2F2A1.to_bytes(32,'little')
    japanese_blue_eyes_big = 0xF284F299F08BF1D0F1D2F1E8F084F289F29DF1D2F1F6F084F1F7F297F1E2F2A1.to_bytes(32,'big')
    # 0xF2 - katakana
    # 0xF1 - hiragana
    japanese_rendered = 'ブルーアイズ•ホワイト•ドラゴン'
    for enc in japanese_encodings:
        try:
            print(enc)
            render = japanese_rendered.encode(enc)
            target = japanese_blue_eyes_lil
            print(*map(lambda e: e[1] - e[0], zip(render,target)))
            print('>', render)
            print('<', target)
            print()
        except: pass
    return
    with open("japanese_lil.txt", "wb") as f:
        f.write(japanese_blue_eyes_lil)
    with open("japanese_big.txt", "wb") as f:
        f.write(japanese_blue_eyes_big)

    print(japanese_encodings)
    for enc in japanese_encodings:
        try:
            print(japanese_blue_eyes_lil.decode(enc))
        except: pass
        try:
            print(japanese_blue_eyes_lil[::-1].decode(enc))
        except: pass
        try:
            print(japanese_blue_eyes_big.decode(enc))
        except: pass
        try:
            print(japanese_blue_eyes_big[::-1].decode(enc))
        except: pass
