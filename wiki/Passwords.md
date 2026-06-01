# Password System

## Overview

Yu-Gi-Oh! GX Duel Academy uses 8-digit numerical passwords to unlock individual cards. Each of the game's 1200 cards corresponds to a unique password. When a correct password is entered via the in-game password menu, the corresponding card is added to the player's collection.

The password system is implemented at ROM address `0x080d5b88` (function `FUN_080d5b88`) and reverse-engineered in `src/ygogxda/passwords.py`.

## Entering Passwords In-Game

1. From the main menu, select **Deck Edit** → **Password**.
2. Use the D-pad to select digits and press A to confirm each digit.
3. After entering all 8 digits, the game validates the password.
4. If valid, the corresponding card is added to your collection.

> **Note**: Not all cards can be obtained through password entry — some are exclusive to dueling, exams, or shop packs.

## Password Algorithm

### Hash Function (`forward_hash`)

```
def forward_hash(digits: bytes) -> int:
    hash = 0
    for i in range(8):
        hash = digits[i] + hash * 16
    return hash
```

Each digit (0-9) is treated as its raw byte value (0x00-0x09). The 8-digit string is iterated, building a hash by repeatedly multiplying by 16 and adding the next digit. This is equivalent to interpreting the digit sequence as a base-16 number where each digit position holds values 0-9 (rather than 0-15).

### Padding Function

```
padding(card_id) = (card_id * 0x343fd + 0x269ec3) >> 0x10 | 0x9ec30000
```

Generates a 32-bit pad value from the card's ordinal index.

### Key Table

A table of 1201 32-bit keys is stored at the `CARD_PASSWORD_KEYS` region in ROM. These keys are derived from the original game and form a one-to-one mapping between passwords and card ordinals.

### Expected Hash

```
expected_hash(card_id) = keys[card_id] ^ padding(card_id)
```

### Password Validation

A password string is valid if `forward_hash(password_bytes)` equals `expected_hash(card_id)` for some `card_id` in the range `[1, 1200]`. The matching `card_id` is returned as the ordinal.

### Password Generation (`inverse_hash` / `unlock`)

To generate a password for a given card ordinal:

1. Compute `expected_hash(card_id)`.
2. Decompose the 32-bit hash back into 8 decimal digits:

```
def inverse_hash(hashed):
    digits = ''
    for i in reversed(range(8)):
        digit = hashed // 16**i
        hashed %= 16**i
        digits += str(digit)
    return digits
```

### Example

```
card_id = 1 (Blue-Eyes White Dragon)
key[1]   = 0x17a01110
padding  = 0x9ec30029
expected = 0x17a01110 ^ 0x9ec30029 = 0x89631139
digits   = inverse_hash(0x89631139) = "89631139"
```

## Complete Password Table

All 1200 cards have valid passwords. The table below lists every password organized by ordinal.

### Ordinals 1–100

| Ordinal | Password | Card Name |
|---------|----------|-----------|
| 1 | `89631139` | Blue-Eyes White Dragon |
| 2 | `15025844` | Mystical Elf |
| 3 | `88819587` | Baby Dragon |
| 4 | `15303296` | Ryu-Kishin |
| 5 | `41392891` | Feral Imp |
| 6 | `87796900` | Winged Dragon, Guardian of the Fortress #1 |
| 7 | `40575313` | Shadow Specter |
| 8 | `87564352` | Blackland Fire Dragon |
| 9 | `40453765` | Swamp Battleguard |
| 10 | `72842870` | Tyhone |
| 11 | `45231177` | Flame Swordsman |
| 12 | `71625222` | Time Wizard |
| 13 | `08124921` | Right Leg of the Forbidden One |
| 14 | `44519536` | Left Leg of the Forbidden One |
| 15 | `70903634` | Right Arm of the Forbidden One |
| 16 | `07902349` | Left Arm of the Forbidden One |
| 17 | `33396948` | Exodia the Forbidden One |
| 18 | `70781052` | Summoned Skull |
| 19 | `32274490` | Skull Servant |
| 20 | `05053103` | Battle Ox |
| 21 | `31339260` | Zombie Warrior |
| 22 | `94119974` | Two-Headed King Rex |
| 23 | `46986414` | Dark Magician |
| 24 | `29491031` | The Snake Hair |
| 25 | `66889139` | Gaia the Dragon Champion |
| 26 | `06368038` | Gaia The Fierce Knight |
| 27 | `28279543` | Curse of Dragon |
| 28 | `54541900` | Karbonala Warrior |
| 29 | `26202165` | Sangan |
| 30 | `52584282` | Hercules Beetle |
| 31 | `40640057` | Kuriboh |
| 32 | `76812113` | Harpie Lady |
| 33 | `12206212` | Harpie Lady Sisters |
| 34 | `90357090` | Silver Fang |
| 35 | `14977074` | Garoozis |
| 36 | `41462083` | Thousand Dragon |
| 37 | `13039848` | Giant Soldier of Stone |
| 38 | `48305365` | Axe Raider |
| 39 | `38289717` | Crawling Dragon #2 |
| 40 | `74677422` | Red-Eyes B. Dragon |
| 41 | `06840573` | Barox |
| 42 | `95727991` | Catapult Turtle |
| 43 | `68516705` | Mystic Horseman |
| 44 | `94905343` | Rabid Horseman |
| 45 | `93889755` | Crass Clown |
| 46 | `66672569` | Dragon Zombie |
| 47 | `92667214` | Clown Zombie |
| 48 | `55550921` | Battle Warrior |
| 49 | `92944626` | Wings of Wicked Flame |
| 50 | `28933734` | Mask of Darkness |
| 51 | `22026707` | Curtain of the Dark Ones |
| 52 | `15150365` | White Magical Hat |
| 53 | `41544074` | Kamionwizard |
| 54 | `13215230` | Dream Clown |
| 55 | `75582395` | Faith Bird |
| 56 | `37421579` | Charubin the Fire Knight |
| 57 | `52800428` | Fiend's Hand |
| 58 | `34460851` | Flame Manipulator |
| 59 | `00732302` | Temple of Skulls |
| 60 | `36121917` | Monster Egg |
| 61 | `99510761` | Lord of the Lamp |
| 62 | `62403074` | Rhaimundos of the Red Sword |
| 63 | `53581214` | Fire Reaper |
| 64 | `53293545` | Firegrass |
| 65 | `56342351` | M-Warrior #1 |
| 66 | `92731455` | M-Warrior #2 |
| 67 | `28725004` | Tainted Wisdom |
| 68 | `54098121` | Mysterious Puppeteer |
| 69 | `17881964` | Darkfire Dragon |
| 70 | `80770678` | Spirit of the Harp |
| 71 | `16768387` | Big Eye |
| 72 | `53153481` | Armaill |
| 73 | `42431843` | Ancient Brain |
| 74 | `88435542` | Fire Eye |
| 75 | `01641882` | Fusionist |
| 76 | `63545455` | Mech Mole Zombie |
| 77 | `75356564` | Petit Dragon |
| 78 | `98818516` | Frenzied Panda |
| 79 | `61201220` | Phantom Ghost |
| 80 | `38142739` | Petit Angel |
| 81 | `96851799` | Hinotama Soul |
| 82 | `85639257` | Aqua Madoor |
| 83 | `58528964` | Flame Ghost |
| 84 | `84916669` | Doriado |
| 85 | `11901678` | B. Skull Dragon |
| 86 | `19066538` | Roaring Ocean Snake |
| 87 | `46461247` | Trap Master |
| 88 | `80516007` | Rare Fish |
| 89 | `16899564` | Beautiful Headhuntress |
| 90 | `42883273` | Wodan the Resident of the Forest |
| 91 | `89272878` | Guardian of the Labyrinth |
| 92 | `40826495` | Dissolverock |
| 93 | `75376965` | Enchanting Mermaid |
| 94 | `00549481` | Prevent Rat |
| 95 | `37043180` | Dimensional Warrior |
| 96 | `51371017` | Princess of Tsurugi |
| 97 | `59036972` | Mavelus |
| 98 | `58314394` | Ground Attacker Bugroth |
| 99 | `10071456` | Protector of the Throne |
| 100 | `83464209` | Mystical Sheep #2 |

### Ordinals 101–200

| Ordinal | Password | Card Name |
|---------|----------|-----------|
| 101 | `72520073` | Dark Artist |
| 102 | `71407486` | Fireyarou |
| 103 | `44287299` | Masaki the Legendary Swordsman |
| 104 | `70681994` | Dragoness the Wicked Knight |
| 105 | `33064647` | One-Eyed Shield Dragon |
| 106 | `38942059` | Sonic Maid |
| 107 | `61854111` | Legendary Sword |
| 108 | `37120512` | Sword of Dark Destruction |
| 109 | `04614116` | Dark Energy |
| 110 | `40619825` | Axe of Despair |
| 111 | `77007920` | Laser Cannon Armor |
| 112 | `03492538` | Insect Armor with Laser Cannon |
| 113 | `39897277` | Elf's Light |
| 114 | `46009906` | Beast Fangs |
| 115 | `02370081` | Steel Shell |
| 116 | `39774685` | Vile Germs |
| 117 | `65169794` | Black Pendant |
| 118 | `01557499` | Silver Bow and Arrow |
| 119 | `38552107` | Horn of Light |
| 120 | `64047146` | Horn of the Unicorn |
| 121 | `01435851` | Dragon Treasure |
| 122 | `37820550` | Electro-Whip |
| 123 | `63224564` | Cyber Shield |
| 124 | `90219263` | Elegant Egotist |
| 125 | `36607978` | Mystical Moon |
| 126 | `63102017` | Stop Defense |
| 127 | `99597615` | Malevolent Nuzzler |
| 128 | `15052462` | Violet Crystal |
| 129 | `91595718` | Book of Secret Arts |
| 130 | `98374133` | Invigoration |
| 131 | `25769732` | Machine Conversion Factory |
| 132 | `51267887` | Raise Body Heat |
| 133 | `98252586` | Follow Wind |
| 134 | `77027445` | Power of Kaishin |
| 135 | `87430998` | Forest |
| 136 | `23424603` | Wasteland |
| 137 | `50913601` | Mountain |
| 138 | `86318356` | Sogen |
| 139 | `22702055` | Umi |
| 140 | `59197169` | Yami |
| 141 | `53129443` | Dark Hole |
| 142 | `12580477` | Raigeki |
| 143 | `58074572` | Mooyan Curry |
| 144 | `38199696` | Red Medicine |
| 145 | `11868825` | Goblin's Secret Remedy |
| 146 | `47852924` | Soul of the Pure |
| 147 | `84257639` | Dian Keto the Cure Master |
| 148 | `76103675` | Sparks |
| 149 | `46130346` | Hinotama |
| 150 | `73134081` | Final Flame |
| 151 | `19523799` | Ookazi |
| 152 | `46918794` | Tremendous Fire |
| 153 | `72302403` | Swords of Revealing Light |
| 154 | `18807108` | Spellbinding Circle |
| 155 | `45895206` | Dark-Piercing Light |
| 156 | `33951077` | Super War-Lion |
| 157 | `70345785` | Yamadron |
| 158 | `69123138` | Zera The Mant |
| 159 | `32012841` | Millennium Shield |
| 160 | `05405694` | Black Luster Soldier |
| 161 | `31890399` | Fiend's Mirror |
| 162 | `94773007` | Jirai Gumo |
| 163 | `30778711` | Shadow Ghoul |
| 164 | `99551425` | Labyrinth Tank |
| 165 | `97590747` | La Jinn the Mystical Genie of the Lamp |
| 166 | `23995346` | Blue-Eyes Ultimate Dragon |
| 167 | `25655502` | Bickuribox |
| 168 | `52040216` | Harpie's Pet Dragon |
| 169 | `98049915` | Mystic Lamp |
| 170 | `51828629` | Giltia the D. Knight |
| 171 | `87322377` | Launcher Spider |
| 172 | `24311372` | Zoa |
| 173 | `50705071` | Metalzoa |
| 174 | `86100785` | Zone Eater |
| 175 | `86088138` | Ocubeam |
| 176 | `12472242` | Leghul |
| 177 | `58861941` | Ooguchi |
| 178 | `85255550` | Swordsman from a Foreign Land |
| 179 | `84133008` | Monster Eye |
| 180 | `46700124` | Machine King |
| 181 | `09293977` | Metal Dragon |
| 182 | `45688586` | Mechanical Spider |
| 183 | `08471389` | Giga-Tech Wolf |
| 184 | `07359741` | Mechanicalchaser |
| 185 | `70138455` | Blast Juggler |
| 186 | `69015963` | Cyber-Stein |
| 187 | `32809211` | Jinzo #7 |
| 188 | `31786629` | Thunder Dragon |
| 189 | `94566432` | Kaiser Dragon |
| 190 | `31560081` | Magician of Faith |
| 191 | `93343894` | Water Magician |
| 192 | `93221206` | Ancient Elf |
| 193 | `28593363` | Deepsea Shark |
| 194 | `81386177` | Bottom Dweller |
| 195 | `23771716` | 7 Colored Fish |
| 196 | `86164529` | Aqua Dragon |
| 197 | `85448931` | Guardian of the Sea |
| 198 | `58831685` | Giant Red Seasnake |
| 199 | `47986555` | Millennium Golem |
| 200 | `73481154` | Destroyer Golem |

### Ordinals 201–300

| Ordinal | Password | Card Name |
|---------|----------|-----------|
| 201 | `09653271` | Kaminari Attack |
| 202 | `74703140` | Punished Eagle |
| 203 | `10202894` | Skull Red Bird |
| 204 | `46696593` | Crimson Sunbird |
| 205 | `09076207` | Armed Ninja |
| 206 | `72869010` | Soul Hunter |
| 207 | `35752363` | Vermillion Sparrow |
| 208 | `71746462` | Sea Kamen |
| 209 | `08131171` | Sinister Serpent |
| 210 | `07019529` | Insect Soldiers of the Sky |
| 211 | `33413638` | Cockroach Knight |
| 212 | `60802233` | Kuwagata α |
| 213 | `33691040` | Pragtical |
| 214 | `95952802` | Flower Wolf |
| 215 | `21347810` | Rainbow Flower |
| 216 | `94230224` | Needle Ball |
| 217 | `67629977` | Hoshiningen |
| 218 | `93013676` | Maha Vailo |
| 219 | `56907389` | Musician King |
| 220 | `28563545` | Dragon Seeker |
| 221 | `54652250` | Man-Eater Bug |
| 222 | `16229315` | Gale Dogra |
| 223 | `89112729` | Cyber Saurus |
| 224 | `16507828` | Bracchio-raidus |
| 225 | `11384280` | Cannon Soldier |
| 226 | `46657337` | Muka Muka |
| 227 | `46534755` | Fire Kraken |
| 228 | `08327462` | Skullbird |
| 229 | `71107816` | The Bistro Butcher |
| 230 | `08201910` | Star Boy |
| 231 | `07489323` | Milus Radiant |
| 232 | `60862676` | Flame Cerebrus |
| 233 | `32751480` | Mystical Sand |
| 234 | `69140098` | Gemini Elf |
| 235 | `95144193` | Kwagar Hercules |
| 236 | `21817254` | Mega Thunderball |
| 237 | `07805359` | Niwatori |
| 238 | `60694662` | Skelengel |
| 239 | `07089711` | Hane-Hane |
| 240 | `69572024` | Tongyo |
| 241 | `32355828` | Skelgon |
| 242 | `21239280` | Bone Mouse |
| 243 | `94022093` | Behegon |
| 244 | `21417692` | Dark Elf |
| 245 | `20394040` | Lava Battleguard |
| 246 | `56789759` | Tyhone #2 |
| 247 | `93788854` | The Wandering Doomed |
| 248 | `29172562` | Steel Ogre Grotto #1 |
| 249 | `28450915` | Invader from Another Dimension |
| 250 | `55444629` | Lesser Dragon |
| 251 | `81843628` | Needle Worm |
| 252 | `54622031` | Great Mammoth of Goldfine |
| 253 | `80727036` | Man-eating Black Shark |
| 254 | `43500484` | Darkworld Thorns |
| 255 | `42348802` | Trakadon |
| 256 | `15237615` | Empress Judge |
| 257 | `78010363` | Witch of the Black Forest |
| 258 | `03170832` | Takuhee |
| 259 | `33508719` | Morphing Jar |
| 260 | `32485271` | Rose Spectre of Dunn |
| 261 | `68658728` | Little Chimera |
| 262 | `93920745` | Penguin Soldier |
| 263 | `20315854` | Fairy Dragon |
| 264 | `28470714` | Bladefly |
| 265 | `17358176` | Lady of Faith |
| 266 | `54752875` | Twin-Headed Thunder Dragon |
| 267 | `29929832` | Marine Beast |
| 268 | `56413937` | Warrior of Tradition |
| 269 | `29802344` | Snakeyashi |
| 270 | `17968114` | Amazon of the Seas |
| 271 | `80741828` | Witch's Apprentice |
| 272 | `05901497` | Queen's Double |
| 273 | `41396436` | Blue-Winged Crown |
| 274 | `40173854` | Amphibious Bugroth |
| 275 | `02830619` | Flame Viper |
| 276 | `65623423` | Gruesome Goo |
| 277 | `02118022` | Hyosube |
| 278 | `64501875` | Hibikime |
| 279 | `90873992` | Warrior Elimination |
| 280 | `32268901` | Salamandra |
| 281 | `95051344` | Eternal Rest |
| 282 | `22046459` | Megamorph |
| 283 | `68540058` | Metalmorph |
| 284 | `21323861` | Acid Rain |
| 285 | `94716515` | Eradicating Aerosol |
| 286 | `20101223` | Breath of Light |
| 287 | `56606928` | Eternal Draught |
| 288 | `82878489` | Bright Castle |
| 289 | `29267084` | Shadow Spell |
| 290 | `55761792` | Black Luster Ritual |
| 291 | `81756897` | Zera Ritual |
| 292 | `18144506` | Harpie's Feather Duster |
| 293 | `54539105` | War-Lion Ritual |
| 294 | `81933259` | Beastly Mirror Ritual |
| 295 | `43417563` | Commencement Dance |
| 296 | `80811661` | Hamburger Recipe |
| 297 | `43694075` | Novox's Prayer |
| 298 | `15083728` | House of Adhesive Tape |
| 299 | `42578427` | Eatgaboon |
| 300 | `77754944` | Widespread Ruin |

### Ordinals 301–400

| Ordinal | Password | Card Name |
|---------|----------|-----------|
| 301 | `76806714` | Turtle Oath |
| 302 | `39399168` | Resurrection of Chakra |
| 303 | `41182875` | Javelin Beetle Pact |
| 304 | `78577570` | Garma Sword Oath |
| 305 | `31066283` | Revival of Dokurorider |
| 306 | `77454922` | Fortress Whale's Oath |
| 307 | `04849037` | Performance of Sword |
| 308 | `30243636` | Hungry Burger |
| 309 | `76232340` | Sengenjin |
| 310 | `03627449` | Skull Guardian |
| 311 | `39111158` | Tri-Horned Dragon |
| 312 | `66516792` | Serpent Night Dragon |
| 313 | `02504891` | Skull Knight |
| 314 | `38999506` | Cosmo Queen |
| 315 | `65393205` | Chakra |
| 316 | `91782219` | Crab Turtle |
| 317 | `38277918` | Mikazukinoyaiba |
| 318 | `64271667` | Meteor Dragon |
| 319 | `90660762` | Meteor B. Dragon |
| 320 | `27054370` | Firewing Pegasus |
| 321 | `90844184` | Garma Sword |
| 322 | `26932788` | Javelin Beetle |
| 323 | `62337487` | Fortress Whale |
| 324 | `99721536` | Dokurorider |
| 325 | `76792184` | Dark Magic Ritual |
| 326 | `30208479` | Magician of Black Chaos |
| 327 | `65570596` | Red Archery Girl |
| 328 | `02964201` | Ryu-Ran |
| 329 | `38369349` | Manga Ryu-Ran |
| 330 | `65458948` | Toon Mermaid |
| 331 | `91842653` | Toon Summoned Skull |
| 332 | `64631466` | Relinquished |
| 333 | `27125110` | Thousand-Eyes Idol |
| 334 | `63519819` | Thousand-Eyes Restrict |
| 335 | `90908427` | Steel Ogre Grotto #2 |
| 336 | `26302522` | Blast Sphere |
| 337 | `62397231` | Hyozanryu |
| 338 | `99785935` | Alpha The Magnet Warrior |
| 339 | `64335804` | Red-Eyes Black Metal Dragon |
| 340 | `81480460` | Barrel Dragon |
| 341 | `05640330` | Hannibal Necromancer |
| 342 | `42035044` | Panther Warrior |
| 343 | `05818798` | Gazelle the King of Mythical Beasts |
| 344 | `31812496` | Stone Statue of the Aztecs |
| 345 | `77207191` | Berfomet |
| 346 | `04796100` | Chimera the Flying Mythical Beast |
| 347 | `30190809` | Gear Golem the Moving Fortress |
| 348 | `77585513` | Jinzo |
| 349 | `66362965` | The Fiend Megacyber |
| 350 | `02851070` | Reflect Bounder |
| 351 | `39256679` | Beta The Magnet Warrior |
| 352 | `38033121` | Dark Magician Girl |
| 353 | `64428736` | Alligator's Sword |
| 354 | `91512835` | Insect Queen |
| 355 | `64306248` | Skull-Mark Ladybug |
| 356 | `26185991` | Pinch Hopper |
| 357 | `53183600` | Blue-Eyes Toon Dragon |
| 358 | `50400231` | Satellite Cannon |
| 359 | `86099788` | The Last Warrior from Another Planet |
| 360 | `12493482` | Dunames Dark Witch |
| 361 | `75372290` | Total Defense Shogun |
| 362 | `11761845` | Beast of Talwar |
| 363 | `48766543` | Cyber-Tech Alligator |
| 364 | `11549357` | Gamma The Magnet Warrior |
| 365 | `26376390` | Copycat |
| 366 | `15259703` | Toon World |
| 367 | `41426869` | Black Illusion Ritual |
| 368 | `14315573` | Negate Attack |
| 369 | `40703222` | Multiply |
| 370 | `79571449` | Graceful Charity |
| 371 | `01248895` | Chain Destruction |
| 372 | `74137509` | Graceful Dice |
| 373 | `00126218` | Skull Dice |
| 374 | `73915051` | Scapegoat |
| 375 | `72892473` | Card Destruction |
| 376 | `35686187` | Tragedy |
| 377 | `99789342` | Dark Magic Curtain |
| 378 | `23615409` | Insect Barrier |
| 379 | `66788016` | Fissure |
| 380 | `04206964` | Trap Hole |
| 381 | `24094653` | Polymerization |
| 382 | `51482758` | Remove Trap |
| 383 | `20871001` | Blue Medicine |
| 384 | `56260110` | Raimei |
| 385 | `83764718` | Monster Reborn |
| 386 | `19159413` | De-Spell |
| 387 | `55144522` | Pot of Greed |
| 388 | `82542267` | Gravedigger Ghoul |
| 389 | `18937875` | Burning Spear |
| 390 | `55321970` | Gust Fan |
| 391 | `17814387` | Reinforcements |
| 392 | `44209392` | Castle Walls |
| 393 | `17092736` | Ancient Telescope |
| 394 | `43487744` | White Hole |
| 395 | `16970158` | Call of the Grave |
| 396 | `42364257` | Anti Raigeki |
| 397 | `79759861` | Tribute to the Doomed |
| 398 | `05758500` | Soul Release |
| 399 | `41142615` | The Cheerful Coffin |
| 400 | `78637313` | Call of the Dark |

### Ordinals 401–500

| Ordinal | Password | Card Name |
|---------|----------|-----------|
| 401 | `04031928` | Change of Heart |
| 402 | `77414722` | Magic Jammer |
| 403 | `03819470` | Seven Tools of the Bandit |
| 404 | `24068492` | Just Desserts |
| 405 | `51452091` | Royal Decree |
| 406 | `90330453` | Last Day of Witch |
| 407 | `26725158` | Exile of the Wicked |
| 408 | `53119267` | Magical Thorn |
| 409 | `99518961` | Restructer Revolution |
| 410 | `26902560` | Fusion Sage |
| 411 | `98495314` | Sword of Deep-Seated |
| 412 | `25880422` | Block Attack |
| 413 | `51275027` | The Unhappy Maiden |
| 414 | `88279736` | Robbin' Goblin |
| 415 | `13945283` | Wall of Illusion |
| 416 | `50930991` | Neo the Magic Swordsman |
| 417 | `86325596` | Baron of the Fiend Sword |
| 418 | `13723605` | Man-Eating Treasure Chest |
| 419 | `49218300` | Sorcerer of the Doomed |
| 420 | `12607053` | Waboku |
| 421 | `44095762` | Mirror Force |
| 422 | `19613556` | Heavy Storm |
| 423 | `55608151` | Gryphon Wing |
| 424 | `16762927` | Gravekeeper's Servant |
| 425 | `70368879` | Upstart Goblin |
| 426 | `82003859` | Toll |
| 427 | `18591904` | Final Destiny |
| 428 | `45986603` | Snatch Steal |
| 429 | `81380218` | Chorus of Sanctuary |
| 430 | `17375316` | Confiscation |
| 431 | `44763025` | Delinquent Duo |
| 432 | `70046172` | Rush Recklessly |
| 433 | `16430187` | The Reliable Guardian |
| 434 | `42829885` | The Forceful Sentry |
| 435 | `79323590` | Chain Energy |
| 436 | `05318639` | Mystical Space Typhoon |
| 437 | `42703248` | Giant Trunade |
| 438 | `74191942` | Painful Choice |
| 439 | `00596051` | Snake Fang |
| 440 | `34124316` | Cyber Jar |
| 441 | `61528025` | Banisher of the Light |
| 442 | `97017120` | Giant Rat |
| 443 | `23401839` | Senju of the Thousand Hands |
| 444 | `60806437` | UFO Turtle |
| 445 | `96890582` | Flash Assailant |
| 446 | `23289281` | Karate Man |
| 447 | `95178994` | Giant Germ |
| 448 | `22567609` | Nimble Momonga |
| 449 | `95956346` | Shining Angel |
| 450 | `57839750` | Mother Grizzly |
| 451 | `84834865` | Flying Kamakiri #1 |
| 452 | `20228463` | Ceremonial Bell |
| 453 | `57617178` | Sonic Bird |
| 454 | `83011277` | Mystic Tomato |
| 455 | `56594520` | Gaia Power |
| 456 | `82999629` | Umiiruka |
| 457 | `19384334` | Molten Destruction |
| 458 | `45778932` | Rising Air Current |
| 459 | `81777047` | Luminous Spark |
| 460 | `18161786` | Mystic Plasma Zone |
| 461 | `44656491` | Messenger of Peace |
| 462 | `37580756` | Michizure |
| 463 | `02130625` | Numinous Healer |
| 464 | `01918087` | Minor Goblin Official |
| 465 | `37313786` | Gamble |
| 466 | `74701381` | DNA Surgery |
| 467 | `36280194` | Backup Soldier |
| 468 | `63689843` | Attack and Receive |
| 469 | `36468556` | Ceasefire |
| 470 | `62867251` | Light of Intervention |
| 471 | `08951260` | Respect Play |
| 472 | `61740673` | Imperial Order |
| 473 | `98139712` | Skull Invitation |
| 474 | `71044499` | Nobleman of Crossout |
| 475 | `17449108` | Nobleman of Extermination |
| 476 | `43434803` | The Shallow Grave |
| 477 | `70828912` | Premature Burial |
| 478 | `16227556` | Inspection |
| 479 | `79106360` | Morphing Jar #2 |
| 480 | `06104968` | Bubonic Vermin |
| 481 | `42599677` | Flame Champion |
| 482 | `78984772` | Twin-Headed Fire Dragon |
| 483 | `05388481` | Darkfire Soldier #1 |
| 484 | `31477025` | Mr. Volcano |
| 485 | `78861134` | Darkfire Soldier #2 |
| 486 | `04266839` | Kiseitai |
| 487 | `30655537` | Cyber Falcon |
| 488 | `67049542` | Dark Bat |
| 489 | `03134241` | Flying Kamakiri #2 |
| 490 | `30532390` | Harpie's Brother |
| 491 | `66927994` | Oni Tank T-34 |
| 492 | `02311603` | Overdrive |
| 493 | `78193831` | Buster Blader |
| 494 | `35316708` | Time Seal |
| 495 | `98299011` | Gift of The Mystical Elf |
| 496 | `60082869` | Dust Tornado |
| 497 | `97077563` | Call of the Haunted |
| 498 | `23471572` | Solomon's Lawbook |
| 499 | `96355986` | Enchanted Javelin |
| 500 | `75347539` | Valkyrion the Magna Warrior |

### Ordinals 501–600

| Ordinal | Password | Card Name |
|---------|----------|-----------|
| 501 | `03366982` | Alligator's Sword Dragon |
| 502 | `14898066` | Vorse Raider |
| 503 | `83555666` | Ring of Destruction |
| 504 | `95132338` | Aqua Chorus |
| 505 | `22537443` | Sebek's Blessing |
| 506 | `57482479` | Luminous Soldier |
| 507 | `56369281` | Wolf Axwielder |
| 508 | `83764996` | The Illusory Gentleman |
| 509 | `45547649` | Birdface |
| 510 | `82642348` | Kryuel |
| 511 | `18036057` | Airknight Parshath |
| 512 | `45425051` | Fairy King Truesdale |
| 513 | `17214465` | Maiden of the Aqua |
| 514 | `44203504` | Robotic Knight |
| 515 | `17192817` | Molten Behemoth |
| 516 | `79575620` | Injection Fairy Lily |
| 517 | `06979239` | Woodland Sprite |
| 518 | `42364374` | Arsenal Bug |
| 519 | `79853073` | Kinetic Soldier |
| 520 | `31242786` | Souleater |
| 521 | `78636495` | Slate Warrior |
| 522 | `04035199` | Shapesnatch |
| 523 | `02792265` | Servant of Catabolism |
| 524 | `98456117` | Boneheimer |
| 525 | `12883044` | Flame Dancer |
| 526 | `00423705` | Gearfried the Iron Knight |
| 527 | `46821314` | Humanoid Slime |
| 528 | `73216412` | Worm Drake |
| 529 | `05600127` | Humanoid Worm Drake |
| 530 | `31987274` | Flying Fish |
| 531 | `67371383` | Amphibian Beast |
| 532 | `27671321` | Lightning Conger |
| 533 | `52121290` | Spherous Lady |
| 534 | `87303357` | Shining Abyss |
| 535 | `86281779` | Gadget Soldier |
| 536 | `13676474` | Grand Tiki Elder |
| 537 | `49064413` | The Masked Beast |
| 538 | `86569121` | Melchid the Four-Face Beast |
| 539 | `57882509` | Mask of Weakness |
| 540 | `94377247` | Curse of the Masked Beast |
| 541 | `20765952` | Mask of Dispel |
| 542 | `29549364` | Mask of Restrict |
| 543 | `56948373` | Mask of the Accursed |
| 544 | `82432018` | Mask of Brutality |
| 545 | `55226821` | Lightning Blade |
| 546 | `21598948` | Fairy Box |
| 547 | `53582587` | Torrential Tribute |
| 548 | `22493811` | Multiplication of Ants |
| 549 | `58775978` | Nightmare's Steelcage |
| 550 | `94163677` | Infinite Cards |
| 551 | `57953380` | Card of Safe Return |
| 552 | `62279055` | Magic Cylinder |
| 553 | `35346968` | Solemn Wishes |
| 554 | `24294108` | Burning Land |
| 555 | `97687912` | Fairy Meteor Crush |
| 556 | `23171610` | Limiter Removal |
| 557 | `85742772` | Gravity Bind |
| 558 | `58621589` | Shadow of Eyes |
| 559 | `84620194` | Girochin Kuwagata |
| 560 | `21015833` | Hayabusa Knight |
| 561 | `83994646` | 4-Starred Ladybug of Doom |
| 562 | `10992251` | Gradius |
| 563 | `79870141` | Mad Sword Beast |
| 564 | `05265750` | Skull Mariner |
| 565 | `32269855` | The All-Seeing White Tiger |
| 566 | `78658564` | Goblin Attack Force |
| 567 | `04042268` | Island Turtle |
| 568 | `31447217` | Wingweaver |
| 569 | `67532912` | Science Soldier |
| 570 | `04920010` | Souls of the Forgotten |
| 571 | `30325729` | Dokuroyaiba |
| 572 | `66719324` | Rain of Mercy |
| 573 | `04542651` | Yellow Luster Shield |
| 574 | `94425169` | Spring of Rebirth |
| 575 | `63391643` | Thousand Knives |
| 576 | `90502999` | Ground Collapse |
| 577 | `65475294` | The Unfriendly Amazon |
| 578 | `91869203` | Amazon Archer |
| 579 | `64752646` | Fire Princess |
| 580 | `90147755` | Lady Assailant of Flames |
| 581 | `27132350` | Fire Sorcerer |
| 582 | `53530069` | Spirit of the Breeze |
| 583 | `90925163` | Dancing Fairy |
| 584 | `58818411` | Empress Mantis |
| 585 | `85802526` | Cure Mermaid |
| 586 | `21297224` | Hysteric Fairy |
| 587 | `58696829` | Bio-Mage |
| 588 | `84080938` | The Forgiving Maiden |
| 589 | `21175632` | St. Joan |
| 590 | `57579381` | Marie the Fallen One |
| 591 | `83968380` | Jar of Greed |
| 592 | `10352095` | Scroll of Bewitchment |
| 593 | `56747793` | United We Stand |
| 594 | `83746708` | Mage Power |
| 595 | `19230407` | Offerings to the Doomed |
| 596 | `33767325` | Meteor of Destruction |
| 597 | `69162969` | Lightning Vortex |
| 598 | `32541773` | The Portrait's Secret |
| 599 | `68049471` | The Gross Ghost of Fled Dreams |
| 600 | `05434080` | Headless Knight |

### Ordinals 601–700

| Ordinal | Password | Card Name |
|---------|----------|-----------|
| 601 | `67227834` | Dark Magician's Tome of Black Magic |
| 602 | `94212438` | Destiny Board |
| 603 | `30606547` | The Dark Door |
| 604 | `67105242` | Earthbound Spirit |
| 605 | `66989694` | The Earl of Demise |
| 606 | `92377303` | Dark Sage |
| 607 | `29762407` | Cathedral of Nobles |
| 608 | `28649820` | Embodiment of Apophis |
| 609 | `81439173` | Foolish Burial |
| 610 | `27827272` | Makiu |
| 611 | `80316585` | Cyber Harpie Lady |
| 612 | `89194033` | Mystical Beast Serket |
| 613 | `16589042` | Swift Gaia the Fierce Knight |
| 614 | `52077741` | Obnoxious Celtic Guard |
| 615 | `88472456` | Zombyra the Dark |
| 616 | `41855169` | Jowgen the Spiritualist |
| 617 | `88240808` | Kycoo the Ghost Destroyer |
| 618 | `14644902` | Summoner of Illusions |
| 619 | `40133511` | Bazoo the Soul-Eater |
| 620 | `77527210` | Soul of Purity and Light |
| 621 | `13522325` | Spirit of Flames |
| 622 | `40916023` | Aqua Spirit |
| 623 | `76305638` | The Rock Spirit |
| 624 | `12800777` | Garuda the Wind Spirit |
| 625 | `45894482` | Gilasaurus |
| 626 | `44072894` | Supply |
| 627 | `71466592` | Maryokutai |
| 628 | `33950246` | Royal Command |
| 629 | `33737664` | Graverobber's Retribution |
| 630 | `69122763` | Deal of Phantom |
| 631 | `32015116` | Blind Destruction |
| 632 | `05494820` | Cyclon Laser |
| 633 | `31893528` | Spirit Message "I" |
| 634 | `67287533` | Spirit Message "N" |
| 635 | `94772232` | Spirit Message "A" |
| 636 | `30170981` | Spirit Message "L" |
| 637 | `33550694` | Fusion Gate |
| 638 | `06343408` | Miracle Dig |
| 639 | `94004268` | Amazoness Swords Woman |
| 640 | `93260132` | Enchanted Arrow |
| 641 | `55821894` | Amazoness Fighter |
| 642 | `54704216` | Nightmare Wheel |
| 643 | `17597059` | Byser Shock |
| 644 | `16475472` | Lesser Fiend |
| 645 | `42647539` | Ryu-Kishin Clown |
| 646 | `14531242` | Opticlops |
| 647 | `77910045` | Fatal Abacus |
| 648 | `76075810` | Throwstone Unit |
| 649 | `02460565` | Marauding Captain |
| 650 | `75953262` | Warrior Dai Grepher |
| 651 | `74131780` | Exiled Force |
| 652 | `01525329` | The Hunter with 7 Weapons |
| 653 | `32807846` | Reinforcement of the Army |
| 654 | `95281259` | The Warrior Returning Alive |
| 655 | `31553716` | Spear Dragon |
| 656 | `93346024` | The Dragon dwelling in the Cave |
| 657 | `20831168` | Lizard Soldier |
| 658 | `93220472` | Cave Dragon |
| 659 | `29618570` | Gray Wing |
| 660 | `55013285` | Troop Dragon |
| 661 | `54178050` | Dragon's Rage |
| 662 | `80163754` | Burst Breath |
| 663 | `17658803` | Luster Dragon #2 (sic) |
| 664 | `53046408` | Emergency Provisions |
| 665 | `80441106` | Keldo |
| 666 | `52824910` | Kaiser Glider |
| 667 | `29228529` | Spell Reproduction |
| 668 | `82108372` | Mudora |
| 669 | `28106077` | Cestus of Dagla |
| 670 | `81985784` | Des Feral Imp |
| 671 | `17484499` | Reversal of Graves |
| 672 | `54878498` | Kelbek |
| 673 | `16268841` | Zolga |
| 674 | `16135253` | Agido |
| 675 | `78706415` | Fiber Jar |
| 676 | `14291024` | Gradius' Option |
| 677 | `77084837` | Inaba White Rabbit |
| 678 | `03078576` | Yata-Garasu |
| 679 | `40473581` | Susa Soldier |
| 680 | `76862289` | Yamata Dragon |
| 681 | `02356994` | Great Long Nose |
| 682 | `75745607` | Hino-Kagu-Tsuchi |
| 683 | `38538445` | Fushi No Tori |
| 684 | `00295517` | A Legendary Ocean |
| 685 | `24623598` | Disappear |
| 686 | `29401950` | Bottomless Trap Hole |
| 687 | `81172176` | Fiend Comedian |
| 688 | `80233946` | Gora Turtle |
| 689 | `16222645` | Sasuke Samurai |
| 690 | `43716289` | Poison Mummy |
| 691 | `89111398` | Dark Dust Spirit |
| 692 | `15383415` | Swarm of Scarabs |
| 693 | `41872150` | Swarm of Locusts |
| 694 | `78266168` | Giant Axe Mummy |
| 695 | `14261867` | 8-Claws Scorpion |
| 696 | `40659562` | Guardian Sphinx |
| 697 | `77044671` | Pyramid Turtle |
| 698 | `03549275` | Dice Jar |
| 699 | `76922029` | Don Zaloog |
| 700 | `02326738` | Des Lacooda |

### Ordinals 701–800

| Ordinal | Password | Card Name |
|---------|----------|-----------|
| 701 | `38699854` | Book of Taiyou |
| 702 | `14087893` | Book of Moon |
| 703 | `76532077` | Bottomless Shifting Sand |
| 704 | `65810489` | Statue of the Wicked |
| 705 | `38299233` | Needle Wall |
| 706 | `37576645` | Reckless Greed |
| 707 | `90960358` | Toon Dark Magician Girl |
| 708 | `99747800` | Legendary Fiend |
| 709 | `89997728` | Toon Table of Contents |
| 710 | `16392422` | Toon Masked Sorcerer |
| 711 | `42386471` | Toon Gemini Elf |
| 712 | `79875176` | Toon Cannon Soldier |
| 713 | `15270885` | Toon Goblin Attack Force |
| 714 | `42664989` | Card of Sanctity |
| 715 | `04335645` | Newdoria |
| 716 | `02047519` | Hidden Soldier |
| 717 | `38445524` | Gil Garth |
| 718 | `65830223` | Coffin Seller |
| 719 | `01224927` | Calamity of the Wicked |
| 720 | `00102380` | Lava Golem |
| 721 | `62873545` | Master of Dragon Soldier |
| 722 | `99267150` | F.G.D. |
| 723 | `25652259` | Queen's Knight |
| 724 | `62651957` | X-Head Cannon |
| 725 | `24530661` | Master Kyonshee |
| 726 | `51934376` | Kabazauls |
| 727 | `97923414` | Inpachi |
| 728 | `24317029` | Gravekeeper's Spy |
| 729 | `50712728` | Gravekeeper's Curse |
| 730 | `37101832` | Gravekeeper's Guard |
| 731 | `63695531` | Gravekeeper's Spear Soldier |
| 732 | `99690140` | Gravekeeper's Vassal |
| 733 | `99877698` | Gravekeeper's Cannonholder |
| 734 | `51534754` | Yomi Ship |
| 735 | `86801871` | Cobra Jar |
| 736 | `85562745` | Dark Room of Nightmare |
| 737 | `47233801` | Dark Snake Syndrome |
| 738 | `73628505` | Terraforming |
| 739 | `10012614` | Banner of Courage |
| 740 | `46411259` | Metamorphosis |
| 741 | `41398771` | Curse of Aging |
| 742 | `04178474` | Raigeki Break |
| 743 | `76848240` | Non Aggression Area |
| 744 | `65622692` | Y-Dragon Head |
| 745 | `02111707` | XY-Dragon Cannon |
| 746 | `64500000` | Z-Metal Tank |
| 747 | `91998119` | XYZ-Dragon Cannon |
| 748 | `64788463` | King's Knight |
| 749 | `90876561` | Jack's Knight |
| 750 | `99050989` | Drillago |
| 751 | `12143771` | People Running About |
| 752 | `58538870` | Oppressed People |
| 753 | `85936485` | United Resistance |
| 754 | `11321183` | Dark Blade |
| 755 | `47415292` | Pitch-Dark Dragon |
| 756 | `10209545` | Decayed Commander |
| 757 | `47693640` | Zombie Tiger |
| 758 | `73698349` | Giant Orc |
| 759 | `46571052` | Vampire Orchis |
| 760 | `12965761` | Des Dendle |
| 761 | `48148828` | D.D. Crazy Beast |
| 762 | `84636823` | Spell Canceller |
| 763 | `73398797` | Paladin of White Dragon |
| 764 | `09786492` | White Dragon Ritual |
| 765 | `72575145` | Demotion |
| 766 | `71453557` | Autonomous Action Unit |
| 767 | `08842266` | Poison of the Old Man |
| 768 | `60519422` | Kishido Spirit |
| 769 | `38992735` | Wave-Motion Cannon |
| 770 | `65396880` | Huge Revolution |
| 771 | `91781589` | Thunder of Ruler |
| 772 | `64274292` | Meteorain |
| 773 | `27053506` | Secret Barrel |
| 774 | `99724761` | XZ-Tank Cannon |
| 775 | `25119460` | YZ-Tank Dragon |
| 776 | `98502113` | Dark Paladin |
| 777 | `11813953` | Great Angus |
| 778 | `48202661` | Aitsu |
| 779 | `84696266` | Sonic Duck |
| 780 | `11091375` | Luster Dragon #1 (sic) |
| 781 | `47480070` | Amazoness Paladin |
| 782 | `46363422` | Skilled White Magician |
| 783 | `73752131` | Skilled Dark Magician |
| 784 | `09156135` | Apprentice Magician |
| 785 | `45141844` | Old Vindictive Magician |
| 786 | `08034697` | Magical Marionette |
| 787 | `71413901` | Breaker the Magical Warrior |
| 788 | `07802006` | Magical Plant Mandragola |
| 789 | `34206604` | Magical Scientist |
| 790 | `70791313` | Royal Magical Library |
| 791 | `07180418` | Armor Exe |
| 792 | `33184167` | Tribe-Infecting Virus |
| 793 | `69579761` | Des Koala |
| 794 | `69456283` | Koitsu |
| 795 | `34029630` | Pitch-Black Power Stone |
| 796 | `61127349` | Big Bang Shot |
| 797 | `34906152` | Mass Driver |
| 798 | `60391791` | Senri Eye |
| 799 | `06390406` | Emblem of Dragon Destroyer |
| 800 | `33784505` | Jar Robber |

### Ordinals 801–900

| Ordinal | Password | Card Name |
|---------|----------|-----------|
| 801 | `32062913` | Mega Ton Magical Cannon |
| 802 | `68057622` | Continuous Destruction Punch |
| 803 | `95451366` | Exhausting Spell |
| 804 | `21840375` | Hidden Book of Spell |
| 805 | `68334074` | Miracle Restoring |
| 806 | `20727787` | Disarmament |
| 807 | `53112492` | Anti-Spell |
| 808 | `99517131` | The Spell Absorbing Life |
| 809 | `26905245` | Metal Reflect Slime |
| 810 | `52090844` | Bowganian |
| 811 | `13944422` | Granadora |
| 812 | `86327225` | Shinato, King of a Higher Plane |
| 813 | `13722870` | Dark Flare Knight |
| 814 | `49217579` | Mirage Knight |
| 815 | `12600382` | Exodia Necross |
| 816 | `48094997` | Battle Footballer |
| 817 | `11987744` | Nin-Ken Dog |
| 818 | `47372349` | Acrobat Monkey |
| 819 | `09817927` | Gyaku-Gire Panda |
| 820 | `07572887` | D. D. Warrior Lady |
| 821 | `33977496` | Thousand Needles |
| 822 | `60365591` | Shinato's Ark |
| 823 | `33244944` | Contract with Exodia |
| 824 | `68304813` | Precious Cards from Beyond |
| 825 | `94793422` | Rod of the Mind's Eye |
| 826 | `57182235` | Token Thanksgiving |
| 827 | `93671934` | Morale Boost |
| 828 | `29843091` | Ojama Trio |
| 829 | `28121403` | Really Eternal Rest |
| 830 | `50725996` | Dark Magician Knight |
| 831 | `87210505` | Knight's Title |
| 832 | `13604200` | Sage's Stone |
| 833 | `49003308` | Gagagigo |
| 834 | `86498013` | D. D. Trainer |
| 835 | `12482652` | Ojama Green |
| 836 | `49881766` | Archfiend Soldier |
| 837 | `11548522` | Outstanding Dog Marron |
| 838 | `73431236` | Iron Blacksmith Kotetsu |
| 839 | `46820049` | Mefist the Infernal General |
| 840 | `34853266` | Tsukuyomi |
| 841 | `60258960` | Legendary Flame Lord |
| 842 | `97642679` | Dark Master - Zorc |
| 843 | `33031674` | Incandescent Ordeal |
| 844 | `69035382` | Contract with the Abyss |
| 845 | `96420087` | Contract with the Dark Master |
| 846 | `95308449` | Final Countdown |
| 847 | `21070956` | Altar for Tribute |
| 848 | `57069605` | Frozen Soul |
| 849 | `56120475` | Sakuretsu Armor |
| 850 | `82529174` | Ray of Hope |
| 851 | `42941100` | Ojama Yellow |
| 852 | `79335209` | Ojama Black |
| 853 | `15734813` | Soul Tiger |
| 854 | `42129512` | Big Koala |
| 855 | `78613627` | Des Kangaroo |
| 856 | `14618326` | Crimson Ninja |
| 857 | `77491079` | Gale Lizard |
| 858 | `04896788` | Spirit of the Pot of Greed |
| 859 | `77379481` | Sasuke Samurai #3 |
| 860 | `75946257` | Witch Doctor of Chaos |
| 861 | `01434352` | Chaos Necromancer |
| 862 | `74823665` | Inferno |
| 863 | `00218704` | Fenrir |
| 864 | `47606319` | Gigantes |
| 865 | `73001017` | Silpheed |
| 866 | `09596126` | Chaos Sorcerer |
| 867 | `36584821` | Gren Maju Da Eiza |
| 868 | `72989439` | Black Luster Soldier - Envoy of the Beginning |
| 869 | `09373534` | Fuhma Shuriken |
| 870 | `35762283` | Heart of the Underdog |
| 871 | `08251996` | Ojama Delta Hurricane!! |
| 872 | `61044390` | Chaos End |
| 873 | `97439308` | Chaos Greed |
| 874 | `60912752` | D. D. Borderline |
| 875 | `96316857` | Recycle |
| 876 | `23701465` | Primal Seed |
| 877 | `69196160` | Thunder Crash |
| 878 | `95194279` | Dimension Distortion |
| 879 | `22589918` | Reload |
| 880 | `68073522` | Soul Absorption |
| 881 | `21466326` | Blasting the Ruins |
| 882 | `94256039` | Tower of Babel |
| 883 | `57139487` | Chain Disappearance |
| 884 | `83133491` | Zero Gravity |
| 885 | `20522190` | Dark Mirror Force |
| 886 | `82301904` | Chaos Emperor Dragon - Envoy of the End |
| 887 | `43793530` | Giga Gagagigo |
| 888 | `79182538` | Mad Dog of Darkness |
| 889 | `16587243` | Neo Bug |
| 890 | `42071342` | Sea Serpent Warrior of Darkness |
| 891 | `78060096` | Terrorking Salmon |
| 892 | `05464695` | Blazing Inpachi |
| 893 | `41859700` | Burning Algae |
| 894 | `78243409` | The Thing in the Crater |
| 895 | `04732017` | Molten Zombie |
| 896 | `40737112` | Dark Magician of Chaos |
| 897 | `03510565` | Stealth Bird |
| 898 | `30914564` | Sacred Crane |
| 899 | `76909279` | Enraged Battle Ox |
| 900 | `03493978` | Don Turtle |

### Ordinals 901–1000

| Ordinal | Password | Card Name |
|---------|----------|-----------|
| 901 | `39892082` | Balloon Lizard |
| 902 | `65287621` | Dark Driceratops |
| 903 | `38670435` | Black Tyranno |
| 904 | `65064143` | Anti-Aircraft Flower |
| 905 | `64342551` | Amphibious Bugroth MK-3 |
| 906 | `37721209` | Levia-Dragon - Daedalus |
| 907 | `22609617` | Mataza the Zapper |
| 908 | `68007326` | Guardian Angel Joan |
| 909 | `95492061` | Manju of the Ten Thousand Hands |
| 910 | `21887179` | Getsu Fuhma |
| 911 | `57281778` | Ryu Kokki |
| 912 | `34370473` | Gryphon's Feather Duster |
| 913 | `60764581` | Stray Lambs |
| 914 | `97169186` | Smashing Ground |
| 915 | `69542930` | Dedication through Light and Darkness |
| 916 | `96947648` | Salvage |
| 917 | `22431243` | Ultra Evolution Pill |
| 918 | `59820352` | Earth Chant |
| 919 | `21219755` | Destruction Ring |
| 920 | `94192409` | Compulsory Evacuation Device |
| 921 | `21597117` | A Hero Emerges |
| 922 | `57585212` | Self-Destruct Button |
| 923 | `84970821` | Curse of Darkness |
| 924 | `20374520` | Begone, Knave! |
| 925 | `56769674` | DNA Transplant |
| 926 | `83258273` | Robbin' Zombie |
| 927 | `19252988` | Trap Jammer |
| 928 | `56647086` | Invader of Darkness |
| 929 | `17185260` | Inferno Hammer |
| 930 | `43580269` | Emes the Infinity |
| 931 | `70074904` | D. D. Assailant |
| 932 | `76895648` | Dangerous Machine TYPE-6 |
| 933 | `39674352` | Gogiga Gagagigo |
| 934 | `66073051` | Warrior of Zera |
| 935 | `02468169` | Sealmaster Meisei |
| 936 | `39552864` | Mystical Shine Ball |
| 937 | `65957473` | Metal Armored Bug |
| 938 | `52768103` | KA-2 Des Scissors |
| 939 | `98162242` | Needle Burrower |
| 940 | `25551951` | Blowback Dragon |
| 941 | `51945556` | Zaborg the Thunder Monarch |
| 942 | `87340664` | Atomic Firefly |
| 943 | `24435369` | Mermaid Knight |
| 944 | `50823978` | Piranha Army |
| 945 | `83228073` | Two Thousand Needles |
| 946 | `19612721` | Disc Fighter |
| 947 | `82005435` | Lady Ninja Yae |
| 948 | `81383947` | White Magician Pikeru |
| 949 | `18378582` | Archlord Zerato |
| 950 | `80161395` | Mystik Wok |
| 951 | `17655904` | Burst Stream of Destruction |
| 952 | `43040603` | Monster Gate |
| 953 | `56433456` | The Sanctuary in the Sky |
| 954 | `82828051` | Earthquake |
| 955 | `45311864` | Goblin Thief |
| 956 | `82705573` | Backfire |
| 957 | `44595286` | Light of Judgment |
| 958 | `44472639` | Solar Ray |
| 959 | `70861343` | Ninjitsu Art of Transformation |
| 960 | `16255442` | Beckoning Light |
| 961 | `43250041` | Draining Shield |
| 962 | `79649195` | Armor Break |
| 963 | `31305911` | Marshmallon |
| 964 | `30683373` | Shield Crash |
| 965 | `03072077` | Return Zombie |
| 966 | `30461781` | Corpse of Yata-Garasu |
| 967 | `27288416` | Mokey Mokey |
| 968 | `53776525` | Gigobyte |
| 969 | `99171160` | Kozaky |
| 970 | `26566878` | Fiend Scorpion |
| 971 | `52550973` | Pharaoh's Servant |
| 972 | `89959682` | Pharaonic Protector |
| 973 | `25343280` | Spirit of the Pharaoh |
| 974 | `51838385` | Theban Nightmare |
| 975 | `88236094` | Aswan Apparition |
| 976 | `24221739` | Protector of the Sanctuary |
| 977 | `51616747` | Nubian Guard |
| 978 | `13409151` | Desertapir |
| 979 | `50593156` | Sand Gambler |
| 980 | `49771608` | Absorbing Kid from the Sky |
| 981 | `48659020` | Spirit Caller |
| 982 | `43714890` | Man-Thro' Tro' |
| 983 | `42598242` | Special Hurricane |
| 984 | `78986941` | Order to Charge |
| 985 | `78864369` | Soul Reversal |
| 986 | `67048711` | 7 |
| 987 | `66926224` | The Law of the Normal |
| 988 | `02314238` | Dark Magic Attack |
| 989 | `78697395` | The Third Sarcophagus |
| 990 | `04081094` | The Second Sarcophagus |
| 991 | `31076103` | The First Sarcophagus |
| 992 | `93747864` | Desert Sunlight |
| 993 | `39131963` | Des Counterblow |
| 994 | `66526672` | Labyrinth of Nightmare |
| 995 | `92924317` | Soul Resurrection |
| 996 | `53569894` | Pyramid of Light |
| 997 | `25236056` | Rare Metal Dragon |
| 998 | `52624755` | Peten the Dark Clown |
| 999 | `15013468` | Andro Sphinx |
| 1000 | `51402177` | Sphinx Teleia |

### Ordinals 1001–1100

| Ordinal | Password | Card Name |
|---------|----------|-----------|
| 1001 | `87997872` | Theinen the Great Sphinx |
| 1002 | `14391920` | Inferno Tempest |
| 1003 | `13179332` | Charcoal Inpachi |
| 1004 | `49563947` | Neo Aqua Madoor |
| 1005 | `86652646` | Skull Dog Marron |
| 1006 | `12057781` | Goblin Calligrapher |
| 1007 | `36262024` | Red-Eyes B. Chick |
| 1008 | `04041838` | Ninja Grandmaster Sasuke |
| 1009 | `67934141` | Ultimate Baseball Kid |
| 1010 | `04929256` | Mobius the Frost Monarch |
| 1011 | `30314994` | Element Dragon |
| 1012 | `93107608` | Howling Insect |
| 1013 | `39191307` | Masked Dragon |
| 1014 | `66690411` | Mind on Air |
| 1015 | `91862578` | Enraged Muka Muka |
| 1016 | `28357177` | Hade-Hane |
| 1017 | `64751286` | Penumbral Soldier Lady |
| 1018 | `90140980` | Ojama King |
| 1019 | `27134689` | Master of Oz |
| 1020 | `53539634` | Sanwitch |
| 1021 | `90928333` | Dark Factory of Mass Production |
| 1022 | `26412047` | Hammer Shot |
| 1023 | `52817046` | Mind Wipe |
| 1024 | `52684508` | Inferno Fire Blast |
| 1025 | `27967615` | Fusion Weapon |
| 1026 | `54351224` | Ritual Weapon |
| 1027 | `53239672` | Spirit Barrier |
| 1028 | `89628781` | Ninjitsu Art of Decoy |
| 1029 | `52417194` | Heavy Slump |
| 1030 | `51394546` | Cemetary Bomb |
| 1031 | `14778250` | Tricky |
| 1032 | `41172955` | Green Gadget |
| 1033 | `13955608` | Red Gadget - Stronghold |
| 1034 | `86445415` | Red Gadget |
| 1035 | `13839120` | Yellow Gadget |
| 1036 | `75622824` | Tricky's Magic 4 |
| 1037 | `35322812` | Woodborg Inpachi |
| 1038 | `62327910` | Mighty Guard |
| 1039 | `08715625` | Bokoichi the Freightening Car |
| 1040 | `34100324` | Harpie Girl |
| 1041 | `61505339` | The Creator |
| 1042 | `97093037` | The Creator Incarnate |
| 1043 | `28143906` | Roc from the Valley of Haze |
| 1044 | `64538655` | Sasuke Samurai #4 |
| 1045 | `91932350` | Harpie Lady 1 |
| 1046 | `27927359` | Harpie Lady 2 |
| 1047 | `54415063` | Harpie Lady 3 |
| 1048 | `90810762` | Raging Flame Sprite |
| 1049 | `26205777` | Thestalos the Firestorm Monarch |
| 1050 | `53693416` | Eagle Eye |
| 1051 | `89698120` | Tactical Espionage Expert |
| 1052 | `26082229` | Invasion of Flames |
| 1053 | `52571838` | Creeping Doom Manta |
| 1054 | `88975532` | Pitch-Black Warwolf |
| 1055 | `15960641` | Mirage Dragon |
| 1056 | `14148099` | Big Core |
| 1057 | `87621407` | Dekoichi the Battlechanted Locomotive |
| 1058 | `13026402` | A-Team: Trap Disposal Unit |
| 1059 | `40410110` | Homunculus the Alchemic Being |
| 1060 | `86805855` | Dark Blade the Dragon Knight |
| 1061 | `13803864` | Mokey Mokey King |
| 1062 | `75782277` | Harpies' Hunting Ground |
| 1063 | `01965724` | Mokey Mokey Smackdown |
| 1064 | `47453433` | Back to Square One |
| 1065 | `74848038` | Monster Reincarnation |
| 1066 | `13626450` | Malice Dispersion |
| 1067 | `49010598` | Divine Wrath |
| 1068 | `49998907` | Fruits of Kozaky's Studies |
| 1069 | `01781310` | Fuh-Rin-Ka-Zan |
| 1070 | `48276469` | Chain Burst |
| 1071 | `01669772` | Spell Purification |
| 1072 | `36931229` | Castle Gate |
| 1073 | `36119641` | Space Mambo |
| 1074 | `62113340` | Divine Dragon Ragnarok |
| 1075 | `08508055` | Chu-Ske the Mouse Fighter |
| 1076 | `35052053` | Insect Knight |
| 1077 | `60229110` | Granmarg the Rock Monarch |
| 1078 | `60102563` | Maji-Gire Panda |
| 1079 | `95789089` | Kangaroo Champ |
| 1080 | `22873798` | Hyena |

### Ordinals 1081–1200

| Ordinal | Password | Card Name |
|---------|----------|-----------|
| 1081 | `58268433` | Blade Rabbit |
| 1082 | `94667532` | Mecha-Dog Marron |
| 1083 | `21051146` | Blast Magician |
| 1084 | `57046845` | Gearfried the Swordmaster |
| 1085 | `20939559` | Shadowslayer |
| 1086 | `52323207` | Golem Sentry |
| 1087 | `89718302` | Abare Ushioni |
| 1088 | `87751584` | Gatling Dragon |
| 1089 | `49140998` | A Feather of the Phoenix |
| 1090 | `76539047` | Poison Fangs |
| 1091 | `49328340` | Spiral Spear Strike |
| 1092 | `75417459` | Release Restraint |
| 1093 | `48206762` | Fulfillment of the Contract |
| 1094 | `74694807` | Re-Fusion |
| 1095 | `01689516` | The Big March of Animals |
| 1096 | `36361633` | Threatening Roar |
| 1097 | `63356631` | Phoenix Wing Wind Blast |
| 1098 | `09744376` | Good Goblin Housekeeping |
| 1099 | `62633180` | Assault on GHQ |
| 1100 | `08628798` | D.D. Dynamite |
| 1101 | `61411502` | Elemental Burst |
| 1102 | `97783659` | Blood Sucker |
| 1103 | `60577362` | Overpowering Eye |
| 1104 | `96561011` | Red-Eyes Darkness Dragon |
| 1105 | `34627841` | Kaibaman |
| 1106 | `21844576` | Elemental Hero Avian |
| 1107 | `58932615` | Elemental Hero Burstinatrix |
| 1108 | `84327329` | Elemental Hero Clayman |
| 1109 | `20721928` | Elemental Hero Sparkman |
| 1110 | `57116033` | Winged Kuriboh |
| 1111 | `83104731` | Ancient Gear Golem |
| 1112 | `10509340` | Ancient Gear Beast |
| 1113 | `56094445` | Ancient Gear Soldier |
| 1114 | `82482194` | Millennium Scorpion |
| 1115 | `45871897` | Lost Guardian |
| 1116 | `45159319` | Moai Interceptor Cannons |
| 1117 | `71544954` | Megarock Dragon |
| 1118 | `76321376` | Mine Golem |
| 1119 | `03810071` | Monk Fighter |
| 1120 | `49814180` | Master Monk |
| 1121 | `75209824` | Guardian Statue |
| 1122 | `02694423` | Medusa Worm |
| 1123 | `01571945` | White Ninja |
| 1124 | `63142001` | Batteryman AA |
| 1125 | `09637706` | Des Wombat |
| 1126 | `36021814` | King of the Skull Servants |
| 1127 | `62420419` | Reshef the Dark Being |
| 1128 | `99414168` | Elemental Mistress Doriado |
| 1129 | `35809262` | Elemental Hero Flame Wingman |
| 1130 | `61204971` | Elemental Hero Thunder Giant |
| 1131 | `61181383` | Battery Charger |
| 1132 | `97570038` | Kaminote Blow |
| 1133 | `23965037` | Doriado's Blessing |
| 1134 | `60369732` | Final Ritual of the Ancients |
| 1135 | `96458440` | Legendary Black Belt |
| 1136 | `22020907` | Hero Signal |
| 1137 | `85519211` | Minefield Eruption |
| 1138 | `21908319` | Kozaky's Self-Destruct Button |
| 1139 | `58392024` | Mispolymerization |
| 1140 | `20781762` | Rock Bombardment |
| 1141 | `83675475` | Token Feastevil |
| 1142 | `10069180` | Spell-Stopping Statute |
| 1143 | `56058888` | Royal Surrender |
| 1144 | `57902462` | Holy Knight Ishzark |
| 1145 | `10485110` | Ocean Dragon Lord - Neo-Daedalus |
| 1146 | `45945685` | Cycroid |
| 1147 | `71930383` | Patroid |
| 1148 | `18325492` | Gyroid |
| 1149 | `44729197` | Steamroid |
| 1150 | `71218746` | Drillroid |
| 1151 | `07602840` | UFOroid |
| 1152 | `70095154` | Cyber Dragon |
| 1153 | `06480253` | Wroughtweiler |
| 1154 | `79979666` | Elemental Hero Bubbleman |
| 1155 | `05368615` | Steam Gyroid |
| 1156 | `32752319` | UFOroid Fighter |
| 1157 | `74157028` | Cyber Twin Dragon |
| 1158 | `01546123` | Cyber End Dragon |
| 1159 | `37630732` | Power Bond |
| 1160 | `63035430` | Skyscraper |
| 1161 | `98585345` | Winged Kuriboh LV10 |
| 1162 | `25573054` | Transcendent Wings |
| 1163 | `61968753` | Bubble Shuffle |
| 1164 | `97362768` | Spark Gun |
| 1165 | `60246171` | Soitsu |
| 1166 | `97240270` | Mad Lobster |
| 1167 | `23635815` | Jerry Beans Man |
| 1168 | `96428622` | Cybernetic Cyclopean |
| 1169 | `22512237` | Mechanical Hound |
| 1170 | `85306040` | Goblin Elite Attack Force |
| 1171 | `22790789` | B.E.S. Crystal Core |
| 1172 | `58185394` | Giant Kozaky |
| 1173 | `84173492` | Indomitable Fighter Lei Lei |
| 1174 | `11678191` | Protective Soul Ailin |
| 1175 | `57062206` | Doitsu |
| 1176 | `84451804` | Des Frog |
| 1177 | `10456559` | T.A.D.P.O.L.E. |
| 1178 | `56840658` | Poison Draw Frog |
| 1179 | `83235263` | Tyranno Infinity |
| 1180 | `19733961` | Batteryman C |
| 1181 | `46128076` | Ebon Magician Curran |
| 1182 | `82112775` | D.D.M. - Different Dimension Master |
| 1183 | `18511384` | Fusion Recovery |
| 1184 | `45906428` | Miracle Fusion |
| 1185 | `71490127` | Dragon's Mirror |
| 1186 | `18895832` | System Down |
| 1187 | `44883830` | Des Croaking |
| 1188 | `70278545` | Pot of Generosity |
| 1189 | `43061293` | Fire Darts |
| 1190 | `70156997` | Spiritual Earth Art - Kurogane |
| 1191 | `06540606` | Spiritual Water Art - Aoi |
| 1192 | `42945701` | Spiritual Fire Art - Kurenai |
| 1193 | `79333300` | Spiritual Wind Art - Miyabi |
| 1194 | `05728014` | A Rival Appears! |
| 1195 | `32723153` | Magical Explosion |
| 1196 | `78211862` | Rising Energy |
| 1197 | `05606466` | D.D. Trap Hole |
| 1198 | `31000575` | Conscription |
| 1199 | `05438492` | Wasteland Amazon |
| 1200 | `25366484` | (unknown — no name in string table) |

## Usage via Toolchain

The password system is exposed via `pygogxda.passwords.YugiohPasswords`:

```python
from ygogxda.rom import YugiohROM

rom = YugiohROM("ygogxda.gba")

# Generate password for a card
password = rom.passwords.unlock(1)       # "89631139"

# Validate and look up a password
ordinal = rom.passwords.enter("89631139")  # 1

# Check validity
valid = rom.passwords.is_valid_password("89631139")  # True
```

From the CLI:

```
uv run ygogxda card lookup --ordinal 1
uv run ygogxda card lookup --password 89631139
```

## ROM Details

| Detail | Value |
|--------|-------|
| Password validation function | `FUN_080d5b88` |
| Key table region | `CARD_PASSWORD_KEYS` |
| Number of keys | 1201 (indices 0–1200) |
| Number of unlockable cards | 1200 (ordinals 1–1200) |
| Password format | 8 decimal digits (0–9) |
| Pseudo-cards | Key[0] is unused (no card ordinal 0) |

## Technical Notes

- The keys table (`CARD_PASSWORD_KEYS`) is read as 1201 little-endian 32-bit values starting at the region's base address.
- `padding(card_id)` uses integer arithmetic: `(card_id * 0x343fd + 0x269ec3) >> 0x10 | 0x9ec30000`. Note the right-shift by 0x10 (16 bits) and the OR with `0x9ec30000`.
- `forward_hash` builds the hash by treating each digit as a base-16 weight: `hash = d0*16^7 + d1*16^6 + ... + d7*16^0`, but where each `di` is in range 0–9 (not 0–15).
- `inverse_hash` decomposes the expected hash back into 8 decimal digits via repeated division by powers of 16.
- The mock ROM in `src/ygogxda/mock.py` uses key[0] as a dummy and only sets key[1] = `forward_hash("12345678") ^ padding(1)`, providing exactly 1 valid password for testing.
