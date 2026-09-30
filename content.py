"""All game content for "The Giants of Holst". build.py turns this into the TTS save + GM guide,
gen_art.py renders the art prompts. Positions are grid squares from the map centre (x right, z up/north).
Map is 22 x 14 squares."""
import math

STYLE = ("painterly dark fantasy illustration, muted earthy colours, dramatic light, "
         "hand-painted texture, highly detailed, no text, no letters")
MAP_STYLE = ("top-down orthographic battle map for a tabletop rpg, seen from directly above, "
             "painted fantasy map, detailed, even lighting, no text, no grid, no people")

# ---------------------------------------------------------------- heroes
# seat colour = class. fig = TTS built-in figurine.
HEROES = [
    dict(key="thief", name="Wren the Thief", color="Red", fig="rpg_THIEF", hp=18, defense=13,
         stats=dict(Might=0, Agility=3, Wits=2),
         attacks=[("Dagger", 5, "1d6+3", "melee"), ("Throwing knife", 5, "1d4+3", "range 6")],
         blurb="Quick hands, quicker feet. Advantage on sneaking and lockpicks.",
         portrait="a hooded rogue woman with twin daggers, sly smile, leather armour, city rooftops at dusk",
         cards=[
             ("Shadowstep", "Move up to 6 squares unseen. Your next attack this turn rolls 2 d20, keep the best.",
              "a rogue melting into deep shadow between buildings, only eyes visible"),
             ("Backstab", "Play after you hit: add +2d6 damage.",
              "a dagger striking from behind a pillar, dramatic motion"),
             ("Nimble Fingers", "Auto-succeed one lockpick, pickpocket or trap-disarm check.",
              "delicate hands picking an ornate lock with thin tools, candlelight"),
             ("Smoke Bomb", "Everyone in a 3x3 area is hidden until they act. Enemies can't target allies inside.",
              "a burst of thick grey smoke in a narrow street, silhouettes escaping"),
             ("Loaded Die", "Reroll any one die on the table, yours or anyone else's. Great at games of chance.",
              "close-up of a single ivory six-sided die with round pips on a worn wooden table, candlelight, blank table surface"),
             ("Poisoned Blade", "Your next hit also deals 1d6 at the start of the target's next 3 turns.",
              "a dagger dripping green poison over a vial"),
         ]),
    dict(key="fighter", name="Brannoc the Fighter", color="Blue", fig="rpg_KNIGHT", hp=30, defense=15,
         stats=dict(Might=3, Agility=1, Wits=0),
         attacks=[("Longsword", 5, "1d8+3", "melee"), ("Shield bash", 5, "1d4+3", "melee, push 1 square")],
         blurb="Veteran of the border wars. The only one who speaks a little Dravic.",
         portrait="a scarred armoured knight with longsword and dented shield, stern face, stormy sky",
         cards=[
             ("Cleave", "Make one attack roll against every enemy adjacent to you.",
              "a knight swinging a longsword in a wide arc, sparks flying"),
             ("Shield Wall", "Until your next turn, you and adjacent allies get +3 Defense.",
              "a raised battered shield taking a hail of arrows"),
             ("Taunt", "All enemies that can see you must attack you this round.",
              "a knight banging sword on shield, roaring a challenge"),
             ("Second Wind", "Heal 1d10+5 HP. Free action.",
              "a wounded knight rising to his feet, breathing hard, golden light"),
             ("Mighty Heave", "Throw an object or a human-sized foe up to 4 squares: 2d6 damage to what it hits.",
              "a knight hurling a heavy barrel at an enemy"),
             ("Street Dravic", "Understand and speak Dravic for one whole conversation. +5 to persuade or intimidate.",
              "a knight speaking with a ragged street child in a foreign city"),
         ]),
    dict(key="healer", name="Sister Maelis the Healer", color="Green", fig="rpg_WARRIOR", hp=22, defense=13,
         stats=dict(Might=1, Agility=0, Wits=3),
         attacks=[("Mace", 3, "1d6+1", "melee"), ("Sacred flame", 5, "1d8+1", "range 8, ignores shields")],
         blurb="Battle priest of the Dawn. Keeps everyone breathing.",
         portrait="a stout middle-aged battle priestess in chainmail holding a flanged mace, a golden sun pendant on her chest, kind stern face, braided hair, warm light",
         cards=[
             ("Mending Touch", "Heal an adjacent ally 2d8+3.",
              "glowing hands pressed on a wounded shoulder, soft golden light"),
             ("Prayer of Light", "Every ally within 6 squares heals 1d8.",
              "a priestess raising a holy symbol, rays of light over a group"),
             ("Blessing", "One ally adds +1d4 to all rolls until the end of the fight.",
              "a priestess tracing a glowing rune on a warrior's forehead"),
             ("Sanctuary", "Target can't be attacked until it attacks or the fight ends.",
              "a translucent golden dome protecting a kneeling figure"),
             ("Revive", "An ally at 0 HP stands up with half their HP.",
              "a fallen adventurer gasping back to life, light pouring down"),
             ("Speak with the Dying", "Ask a dying or dead creature 3 questions. It answers in a language you understand.",
              "a priestess kneeling beside a huge dying giant in a cave, ghostly light"),
         ]),
    dict(key="wizard", name="Aldric the Wizard", color="Purple", fig="rpg_MAGE", hp=16, defense=11,
         stats=dict(Might=0, Agility=1, Wits=3),
         attacks=[("Staff", 2, "1d6", "melee"), ("Arcane bolt", 5, "1d10", "range 10")],
         blurb="Royal court wizard. Fragile, clever, and loud.",
         portrait="an old bearded wizard with a crooked staff and star-embroidered robe, arcane glow",
         cards=[
             ("Fireball", "3x3 area: 3d6 fire, Agility DC 14 for half. Burns wicker shields to ash.",
              "a huge fireball exploding in a ruined street, wicker burning"),
             ("Tongues", "For this scene the whole party understands and speaks every language, including Giantish.",
              "an old bearded human wizard speaking, ribbons of swirling golden light flowing from his mouth, calm wise face"),
             ("Levitate", "Lift yourself or one ally up to 10 squares straight up, and set them down gently.",
              "an old wizard levitating in mid-air inside a tall dark cave shaft, feet high above the ground, robes billowing, glowing aura"),
             ("Mirror Image", "Until the fight ends, every attack against you: roll a d6, on 1-3 it hits an illusion instead.",
              "three identical wizards shimmering side by side"),
             ("Frost Nova", "Enemies adjacent to you take 1d6 and can't move on their next turn.",
              "a ring of ice exploding outwards from a wizard, frozen ground"),
             ("Detect Magic", "The GM points out every magic item and magical trap in this scene.",
              "a wizard's eye glowing, hidden objects shining through walls"),
         ]),
]

RULES = """d20 LITE - HOW TO PLAY
Check or attack: roll d20 + stat. Meet or beat the target.
  Attacks vs the enemy's Defense.  Checks: easy 10, hard 14, heroic 18.
  Natural 20: double damage dice. Natural 1: something goes wrong.
Your turn: move 6 squares + 1 action (attack, play a card, use an item, do a thing).
HP: track it on your counter. At 0 you are down; an ally can spend an action to stabilise you.
Cards: play any time it makes sense (most are an action). Each card works once,
  then comes back to your hand when the GM calls a REST.
Stats: Might (force, climbing, lifting), Agility (sneak, dodge, lockpick), Wits (notice, know, talk)."""

# ---------------------------------------------------------------- npcs
# attacks: (name, to-hit bonus or None, damage dice or None, note). Attack buttons roll these.
NPCS = {
    "giant_club": dict(name="Giant raider", fig="rpg_CYCLOP", hp=60, defense=12, attacks=[
        ("Club smash", 7, "2d8+4", "melee, reach 2"),
        ("Hurl rubble", 5, "2d6+2", "range 10"),
        ("Stomp", None, "1d8", "all adjacent: Agility DC 13 or take it and fall prone"),
    ], notes="WICKER SHIELD: ranged attacks against it get -5 unless the shield is burned. Moves 8."),
    "giant_eye": dict(name="Cyclops raider", fig="rpg_CYCLOP", hp=55, defense=12, attacks=[
        ("Club smash", 7, "2d8+4", "melee, reach 2"),
        ("Leash yank", None, None, "pulls its thrall back next to it"),
    ], notes="WICKER SHIELD: ranged -5. One eye: a blinding trick (sand, light) makes it miss next turn."),
    "giant_troll": dict(name="Hill giant", fig="rpg_CYCLOP", hp=65, defense=11, attacks=[
        ("Fist", 6, "2d6+4", "melee, reach 2"),
        ("Grab", 6, None, "target is held: Might DC 14 to break free, 1d6 each turn"),
    ], notes="WICKER SHIELD: ranged -5. Slow, moves 6."),
    "thrall": dict(name="Leashed thrall", fig="Figurine_Zeke", hp=8, defense=11, attacks=[
        ("Rusty knife", 3, "1d6", "melee"),
    ], notes="Captured looter on a chain. Cutting the leash (Agility DC 12) and the thrall runs off."),
    "street_kid": dict(name="Street kid", fig="rpg_KOBOLD", hp=5, defense=12, attacks=[
        ("Pickpocket", 6, None, "steals 1 gold if it beats the target's Defense"),
    ], notes="Speaks only Dravic. Works for the Bandit Baron."),
    "refugee": dict(name="Refugee", fig="Figurine_Mara", hp=6, defense=10, attacks=[], notes="Hungry and scared."),
    "noble": dict(name="Lady Oriska (noble)", fig="Figurine_Sir_Loin", flip=True, hp=10, defense=12, attacks=[],
                  notes="Pays 5 gold per carcass. Has a fat purse and a Healing Draught she'll trade for food."),
    "hunter": dict(name="Sewer hunter", fig="rpg_RANGER", hp=14, defense=13, attacks=[
        ("Short bow", 4, "1d8", "range 10"),
    ], notes="Rough, proud. Trade food for their Wolf-tooth Charm."),
    "carcass": dict(name="Fresh carcass", fig="rpg_WOLF", hp=1, defense=1, attacks=[], notes="Food.", dead=True),
    "rat_count": dict(name="Vasko, the Bandit Baron", fig="Figurine_Mara", hp=25, defense=13, attacks=[
        ("Rapier", 5, "1d8+2", "melee"),
        ("Baron's Bones: roll 3d6", None, "3d6", "dice game roll"),
        ("Baron's Bones: reroll 1 die", None, "1d6", "his free reroll each round (ring or rules)"),
        ("Lucky Ring reroll", None, "1d6", "extra reroll from the ring, once per round"),
    ], notes="Wears VASKO'S LUCKY RING (see notes). Laughs a lot, never blinks."),
    "guard": dict(name="Baron's bruiser", fig="Figurine_Knil", hp=20, defense=14, attacks=[
        ("Axe", 4, "1d10+2", "melee"),
    ], notes="Two of them. Loyal while Vasko is winning."),
    "log_giant": dict(name="Grask the Log-Thrower", fig="rpg_CYCLOP", hp=70, defense=12, attacks=[
        ("Log throw", None, "3d6", "2x2 area, Agility DC 14 for half; opening move"),
        ("Club smash", 7, "2d8+4", "melee, reach 2"),
        ("Roar", None, None, "all heroes within 6: Wits DC 12 or lose next move"),
    ], notes="Leader of the ambush. Wicker shield: ranged -5."),
    "dead_thug": dict(name="Trampled guildsman", fig="rpg_THIEF", hp=1, defense=1, attacks=[],
                      notes="Thieves' guild. Search: 3 gold, a guild token, cart keys.", dead=True),
    "dying_giant": dict(name="Hrothgul, dying giant", fig="rpg_CYCLOP", hp=6, defense=8, attacks=[
        ("Feeble swipe", 3, "1d6", "only if attacked"),
    ], notes="Speaks only Giantish (Tongues / Speak with the Dying / Street Dravic badly). See scene notes."),
    "dead_human": dict(name="Fallen guildsman", fig="rpg_THIEF", hp=1, defense=1, attacks=[], notes="Died fighting.",
                       dead=True),
    "princess": dict(name="Princess Isolde", fig="rpg_MAGE", hp=20, defense=12, attacks=[
        ("Moonfire", 6, "2d6", "range 10 (once she's healed)"),
    ], notes="Wounded (lying down, 4 HP). Heal her with the damage box (e.g. -8) and she stands up.",
        dead=True, start_hp=4, tint=(1.0, 0.75, 0.85)),
    "giant_rat": dict(name="Giant rat", fig="rpg_RAT", hp=6, defense=12, attacks=[
        ("Bite", 4, "1d6", "melee"),
    ], notes="Only attacks if the bell trap rings or it's cornered."),
}

# ---------------------------------------------------------------- scenes
# npcs: (npc key, x, z) ; heroes: 4 entry squares ; music: file in music/
def wall_line(prop, x1, z1, x2, z2, scale=1):
    """One prop per grid square from (x1, z1) to (x2, z2), turned to run along the line."""
    n = max(abs(x2 - x1), abs(z2 - z1))
    rot = math.degrees(math.atan2(-(z2 - z1), x2 - x1))       # TTS: rotY turns local +x clockwise seen from above
    return [(prop, x1 + (x2 - x1) * i / n, z1 + (z2 - z1) * i / n, rot, scale) for i in range(int(n) + 1)]


def rocks(x1, z1, x2, z2, seed, spacing=1.1, big=1.5):
    """Irregular low rock wall from (x1, z1) to (x2, z2): mixed rocks, jittered, random turn and size."""
    import random
    rnd = random.Random(seed)
    n = max(1, int(math.hypot(x2 - x1, z2 - z1) / spacing))
    out = []
    for i in range(n + 1):
        x = x1 + (x2 - x1) * i / n + rnd.uniform(-0.25, 0.25)
        z = z1 + (z2 - z1) * i / n + rnd.uniform(-0.25, 0.25)
        piece = rnd.choice(["rock_big", "rock_big", "rock_town", "rubble"])
        size = big * rnd.uniform(0.8, 1.2) * (0.7 if piece in ("rock_town", "rubble") else 1)
        out.append((piece, round(x, 2), round(z, 2), rnd.randrange(360), round(size, 2)))
    return out


def ring(prop, rx, rz, count, gap=None, scale=1):
    """Ellipse of props (walls turned along it); gap=(from, to) in degrees (0 = east) is left open."""
    out = []
    for i in range(count):
        a = 360 * i / count
        if gap and (gap[0] <= a <= gap[1] or gap[0] <= a - 360 <= gap[1]):
            continue
        t = math.radians(a)
        x, z = rx * math.cos(t), rz * math.sin(t)
        tangent = (-rx * math.sin(t), rz * math.cos(t))
        out.append((prop, round(x, 2), round(z, 2), math.degrees(math.atan2(-tangent[1], tangent[0])), scale))
    return out


SCENES = [
    dict(key="title", title="The Giants of Holst", fog=False, music="title.mp3",
         map_prompt="a royal parchment map of a mountainous fantasy kingdom with a walled city in a valley, giants' mountains to the north",
         heroes=[(-3, -3), (-1, -3), (1, -3), (3, -3)], npcs=[],
         notes="""PARTY SELECT. Players click their adventurer on the pick panel (top of screen). One each.
Read aloud:
  "By order of King Aldwin of Aldmere: Princess Isolde has not returned from Holst, in the
  land of Dravmark. She went as royal envoy to renew the Mountain Pact with the giants.
  Word is the giants have come down from the mountains and are raiding the towns. Find her.
  Bring her home."
Nobody speaks Dravic except the Fighter (a little). Give them 10 gold and 3 rations each.
Background (GM only): the giants' sacred Hearthstone was stolen from their mountain shrine and
fenced in Holst by the thieves' guild. The giants came to take it back - and everything else."""),

    dict(key="outskirts", title="1. The Outskirts of Holst", fog=True, music="outskirts.mp3", battle=True,
         map_prompt="ruined medieval town street with broken houses, smashed carts, huge footprints in mud, scattered debris, a round sewer grate in the cobbles",
         heroes=[(-7, -1), (-7, 0), (-6, -1), (-6, 0)],
         props=[("ruin_3x3", -8.5, 5.3), ("ruin_2x3", -10, 0.5), ("ruin_3x2", -9.5, -5.5), ("ruin_2x2", -2.5, 6.3),
                ("ruin_3x3", 6.3, 5.3), ("ruin_3x2", 9.5, 1.2, 90), ("ruin_4x2", 9.8, -4.5, 90),
                ("broken_cart", -6, 2.2, 20, 2), ("rubble", 0, 1.2, 0, 1.3), ("rubble", 2.3, -1.8, 40, 1.1),
                ("debris_wood", -6.3, -3.5, 0, 2), ("debris", 3.5, -5.5, 0, 2),
                ("Tileset_Barrel", -7, -3), ("Tileset_Barrel", -6.3, -2.6), ("Tileset_Chest", 1.5, 4.5)],
         npcs=[("street_kid", -4, 3), ("street_kid", -3, 4), ("street_kid", -5, 4),
               ("giant_club", 4.5, 2.5), ("giant_eye", 6, 0), ("giant_troll", 6, -3), ("giant_club", 3, 1),
               ("thrall", 3, 4), ("thrall", 4, -1), ("thrall", 4, -3)],
         notes="""Read aloud: "Holst's gate hangs open. Doors are smashed in, from above. Footprints the size
of a cart sink into the mud. Nothing moves - except three thin children watching you."
Clues: roofs torn off; a door ripped out whole; granaries empty; a broken wicker shield bigger than a door.
STREET KIDS (Dravic only): hands out, "Pénz? Pénz?" (money). Fighter can make out "coin" and "hungry".
  - Give them ANY gold or food -> note it. Later the Bandit Baron's crew vouches for the party (scene 3:
    Vasko starts friendly, first Baron's Bones round is won automatically) and the kids give the party the
    WARREN WHISTLE (magic: blow it, 1d4 street kids appear to help or distract, once).
  - Ignore/threaten them -> they vanish; one tries to pickpocket (Pickpocket button).
GIANTS: after a few minutes, ground shakes. Reveal the fog on the east side. Four giants round the
corner with thralls on chains, wicker shields raised. THIS FIGHT IS MEANT TO BE FLED.
  Switch to BATTLE music. Giants move 8 (hill giant 6), thralls 6. Let them feel the danger: first giant hit is big.
  Escape: the sewer grate (centre-south). Might DC 12 to lift, or the kids point at it and scatter.
  Anyone who jumps in: next scene."""),

    dict(key="sewer", title="2. The Sewer Warren", fog=True, music="sewer.mp3", rest=True,
         map_prompt="underground stone sewer cavern with a refugee camp, tents made of rags, small fires, a central channel of dark water, crates",
         heroes=[(-3, 1), (-3, 2), (-2, 1), (-2, 2)],
         props=[(("stone_wall_broken" if i % 3 == 1 else p), *rest) for i, (p, *rest) in enumerate(
                   wall_line("stone_wall", -6, 5, 6, 5) + wall_line("stone_wall", -8.5, -4, -8.5, 3.5)
                   + wall_line("stone_wall", 8.5, -4, 8.5, 3.5))]
               + [("tent", -5.5, 0.2, 0, 3), ("tent", -2.5, -1.3, 20, 2.6), ("tent", 5.3, 1.8, -10, 3.2),
                  ("campfire", -4, 3.3, 0, 2.5), ("campfire", -6, -2.5, 0, 2.5), ("campfire", 8, -3.2, 0, 2.5),
                  ("bedroll", -7, -1.5, 90, 2), ("bedroll", -1, -4.5, 30, 2), ("bedroll", 2, 2.8, 0, 2),
                  ("crate", -2, 3.6, 0, 2), ("crate", -1, 3.6, 90, 2), ("crate", 1.5, 3.6, 0, 2),
                  ("Tileset_Barrel", 2.6, 3.8), ("Tileset_Barrel", 5.2, -5.5), ("Tileset_Chest", 4.5, -0.6)],
         npcs=[("refugee", -4, 2), ("refugee", -4, -1.8), ("refugee", 0, 2.5), ("refugee", 2, -4),
               ("noble", 3, -1.5), ("hunter", 7.5, -0.5), ("hunter", 6.8, -2.6), ("carcass", 5, -2.5), ("carcass", 6.3, -1.4)],
         notes="""Read aloud: "You drop into stink and darkness. Then - firelight. Hundreds of people live down here
in rags and smoke. Holst didn't empty. It went underground."
FOOD SCENE: two rough hunters drag in carcasses. A noblewoman (Lady Oriska) pays 5 gold EACH, loudly.
Refugees stare. Food is worth more than gold here: 1 ration = 5 gold, or a favour.
  - Hunters sell their WOLF-TOOTH CHARM for 2 rations (magic: once, reroll a failed Agility or Might check).
  - Lady Oriska trades a HEALING DRAUGHT (heal 2d8+2) for 1 ration. Or steal it (Agility DC 14).
  - Sharing food with a refugee family: an old man tells them "the Bandit Baron knows everything in the drains".
ASKING ABOUT THE PRINCESS (language! Fighter DC 12 Wits, Tongues, or charades):
  "A lady in blue with glowing hands? The Bandit Baron's boys brought her through a week ago."
Anyone who asks around gets pointed to the Bandit Baron's den (east). If they paid the kids, a kid appears and leads them.
REST here is allowed (press REST): full HP, all cards back to hand."""),

    dict(key="den", title="3. The Bandit Baron's Den", fog=True, music="den.mp3",
         map_prompt="a smugglers den in an old underground cistern, a large round gambling table with candles, stolen furniture, rugs, crates of loot, a hidden door in the stone wall",
         heroes=[(-6, -1), (-6, 0), (-5, -1), (-5, 0)],
         props=ring("stone_wall", 9.3, 6.9, 50, gap=(-12, 12))
               + [("stall", 5.4, 0, 90, 1.4), ("lantern", 8.4, 1.4, 0, 1.2), ("lantern", 8.4, -1.4, 0, 1.2),
                  ("Tileset_Chest", 3.6, -4.6), ("Tileset_Chest", -6, -5), ("Tileset_Chest", 6.5, 4.2),
                  ("crate", -7, 2.5, 20, 2), ("crate", -7.4, 1.4, 70, 2), ("Tileset_Barrel", 5.3, 5),
                  ("Tileset_Barrel", -3.5, 5), ("debris_wood", -4, -5.5, 0, 2)],
         npcs=[("rat_count", 3.4, 0), ("guard", 5, 2), ("guard", 5, -2), ("street_kid", 2, 2), ("street_kid", 2, -2)],
         notes="""Read aloud: "Stolen chandeliers, three rugs on top of each other, a velvet throne with the stuffing
out. On it: a thin man in a noble's coat three sizes too big, rolling bones in one hand. Vasko,
the Bandit Baron. The street kids sit around him like cats."
He speaks broken Common: "Information is food. You want food, you play."
RAT'S BONES (dice game) - best of 3 rounds:
  1. Each side rolls 3d6 (players use table dice; Vasko: his button).
  2. Each side may reroll ANY of their dice once (Vasko: reroll button per die).
  3. Rank: TRIPLE > STRAIGHT (e.g. 3-4-5) > PAIR (higher pair wins) > highest total.
  One hero plays, others may "help" (cards: Loaded Die rerolls one die; Blessing adds +1d4 to the total).
  Stakes: party loses -> hand over all food and gold. Party wins -> he talks.
  THE RING: Vasko secretly rerolls once more per round with VASKO'S LUCKY RING (use its button).
    Wits DC 14 to notice his ring glowing when he rerolls. Calling it out: he laughs, sets it aside
    for "fairness" (no more ring rerolls) - and now it's on the table.
  STEALING THE RING (optional heist): Agility DC 16 while he's rolling (Nimble Fingers auto-succeeds,
    Smoke Bomb or a distraction gives +5). Caught -> the bruisers attack, kids scatter.
  VASKO'S LUCKY RING (magic): once per scene, reroll any die you can see.
IF THEY WIN: "The girl? Yes, I kept her. A princess eats a lot. Sold her to the guild boys, the
  Shadow Hands. They meant to ransom her to your king. Took her out by cart, north road, three days ago."
  He whistles; a kid leads them to the hidden door (east wall): the old smugglers' passage.
IF THEY LOSE: take their food and gold. He still sells the info for "a favour": they must carry a
  message out of the city. Then the same kid leads them to the door.
If paid the kids earlier: Vasko starts friendly and the first round is given to the party."""),

    dict(key="passage", title="4. The Smugglers' Passage", fog=True, music="passage.mp3",
         map_prompt="a long stone dungeon corridor three squares wide crossing the entire image from left to right, rough cave rock filling the areas above and below the corridor, cracked flagstones, a skeleton, puddles, torch sconces on the walls",
         heroes=[(-8, -0.5), (-8, 0.5), (-7, -0.5), (-7, 0.5)],
         props=rocks(-10, 2.2, 10, 2.2, 1) + rocks(-10, -2.2, 10, -2.2, 2) + rocks(-10.3, -1.2, -10.3, 1.2, 3)
               + [("rock_small", -4, 1.3, 0, 1.5), ("rock_small", 5, -1.3, 70, 1.5), ("debris", 2, 1.2, 0, 2),
                  ("lantern", 9.3, 1.3, 0, 1)],
         npcs=[("giant_rat", 8, 0.8), ("giant_rat", 8, -0.8)],
         notes="""Read aloud: "The door grinds shut behind you. The kid is gone. The tunnel runs west to east,
narrow and old. Your torch shows scratches on the floor - and a skeleton still holding a torch."
FOUR TRAPS, west to east. Wits DC 13 to spot each (Detect Magic reveals the gas vent's rune).
Disarm: Agility DC 13 (Nimble Fingers auto). Triggered effects:
  1. DART PLATE (column -6): darts from the walls, 2d4 to whoever steps on it.
  2. COLLAPSING FLOOR (column -1): 2x2 drops into a 3m pit. Agility DC 13 or fall, 1d6 +
     Might DC 12 to climb out (allies can help).
  3. SLEEP GAS VENT (column +4): Might DC 12 or sleep 1d4 minutes (real time is funny). Rune-marked.
  4. BELL TRIPWIRE (column +8): harmless... unless it rings: the 2 giant rats at the east end attack.
LOOT: the skeleton has a LANTERN OF TRUE SIGHT (magic: once, see through illusions/invisibility
for a scene) - hint: the princess will be hard to see in the cave.
Exit (far east): a hatch into a ditch well outside the city walls. Cart tracks in the mud."""),

    dict(key="cart", title="5. The Broken Cart", fog=True, music="cart.mp3", battle=True,
         map_prompt="a muddy country road through a pine forest, a smashed wooden cart on its side, broken wheel, scattered crates and cloth, huge footprints, a tree trunk lying across the road",
         heroes=[(-8, 0), (-8, 1), (-7, 0), (-7, 1)],
         props=[("broken_cart", 0.3, 0.3, 60, 3), ("log_large", 1.2, -4.1, -23, (7, 2.2, 2.2)),
                ("crate", -4.5, 3.1, 10, 2.2), ("crate", -2.4, 2.6, 40, 2.2), ("crate", 5.9, 0.4, 0, 2),
                ("stump", -3, 6, 0, 2), ("stump", 3, -6.2, 0, 2), ("rock_small", -5.5, -6, 0, 1.5)]
               + [("pine", x, z, (x * 37 + z * 11) % 360, 1.7) for x, z in [
                   (4, 6), (5.5, 5), (7, 6.5), (6, 3.8), (8.5, 3.2), (10.5, 3.5), (10.5, 6.8), (7.5, 1.5),
                   (9.5, 0), (10.5, -4), (9, -3.7), (10.5, -6.5), (6.8, -7), (-10.5, 0.5), (-9.5, -1.5),
                   (-10.5, -4), (-9, -6.5), (-10.5, -6.8), (-5, 6.5), (-3.8, 7)]]
               + [("oak", -10, 6, 0, 1.8), ("bush", -8, 4, 0, 1.5), ("bush", 3.2, 4.2, 0, 1.3)],
         npcs=[("dead_thug", -2, 1.5), ("dead_thug", 2, -1.5), ("dead_thug", -1, -2.5),
               ("log_giant", 8.8, 5, 45), ("giant_club", 10, -1.8, 35), ("giant_eye", 8.2, -5.5, 35)],
         notes="""Read aloud: "The tracks lead north into the pines. An hour later you find the cart - or what's
left of it. It's been stamped flat. So have the men who drove it."
INVESTIGATE (Wits DC 12): guild tokens (a black hand), a broken iron cage in the cart - empty, bent
OUTWARD, scorched. Something burned its way out. Giant footprints lead north-east.
GUILD LOCKBOX (under the cart, Agility DC 13 or cart keys): HEALING DRAUGHT (2d8+2) and a SMOKE EGG
(magic: works like Smoke Bomb, once).
AMBUSH: when they're busy at the cart, a whole tree trunk flies out of the woods. Grask's LOG THROW
opens the fight (2x2 on the cart). Switch to BATTLE music, reveal fog. 3 giants.
These giants are already hurt from the cart fight (lower HP). Fire burns wicker shields.
When the first giant falls the others hesitate; when the second falls the last one flees north-east (to the cave).
If the party arrives badly hurt from the traps, let them REST at the passage exit first.
After: tracks and blood lead to a cave in the hillside."""),

    dict(key="cave", title="6. The Last Stand Cave", fog=True, music="cave.mp3",
         map_prompt="inside a large dark natural cave, rocky floor, a tall shaft in the far wall rising into darkness, fallen weapons, a broken wicker shield, faint light from a crack above",
         heroes=[(0, -6), (1, -6), (0, -5), (1, -5)],
         props=rocks(-10, 6.8, -1.5, 6.8, 4) + rocks(2, 6.8, 10, 6.8, 5) + rocks(-10, -6.8, -2, -6.8, 6)
               + rocks(3, -6.8, 10, -6.8, 7) + rocks(-10.3, -5.8, -10.3, 5.8, 8) + rocks(10.3, -5.8, 10.3, 5.8, 9)
               + [("rock_tall", x, z, (x * 53 + z * 29) % 360, 2) for x, z in [
                   (-8, 4), (-7, 1.5), (-8, -2), (-7, -5), (-5.5, 5), (8, 4), (8.3, 1), (8.5, -1.5),
                   (-3, 5.2), (3.5, 5.2), (-5.5, -6), (5.2, -6.3)]]
               + [("rock_big", 2.8, -2.4, 30, 1.6), ("rock_big", 2.8, -0.4, 80, 1.3),
                  ("campfire_cold", -1.3, 0.8, 0, 2.5), ("debris_wood", -1, 1.5, 0, 2), ("debris", 4, 2.5, 0, 2)],
         npcs=[("dead_human", -3, 2), ("dead_human", -2, -2), ("dead_human", 0.5, -0.5), ("dying_giant", 6, -4.8),
               ("princess", 0, 6)],
         notes="""Read aloud: "The cave stinks of blood and smoke. The guild made their last stand here -
three bodies around a burnt-out fire. In the corner, slumped against the rock, a giant. Still breathing."
HROTHGUL (dying giant): speaks Giantish only. Tongues / Speak with the Dying lets them talk; Street Dravic
gets a few words. He is not hostile, just dying. What he knows:
  - "The little thieves took the Hearthstone from our mountain. Our shrine is cold. We came for it."
  - "We found the little witch in the thieves' cage. She is the Pact-maker. We wanted her to speak for us."
  - "The thieves fought. She... became a bird. White bird. Flew up." (points up the shaft to the north)
  - If healed/fed: "Tell your king: give back the Hearthstone and the mountains are quiet again."
  - He carries a GIANT'S TOOTH AMULET (magic: once, Might check auto-succeeds) and gives it if treated kindly.
THE SHAFT (north, where the light comes in): 10 squares straight up. Might DC 15 climb (fail: 1d6, try again), rope + one
climber, or LEVITATE. The LANTERN OF TRUE SIGHT shows her hiding place (otherwise Wits DC 14).
ISOLDE: in a ledge up the shaft, human again, wounded but alive. Heal her or give her food (she stands).
She keeps a shard of her MOONSTAFF (magic, gift to whoever reached her first: once, cast Fireball).
Read aloud: "A pale young woman in torn blue silk opens her eyes. 'Took you long enough.'"
THE END. (Optional epilogue: she promises to return the Hearthstone and renew the Pact.)"""),
]

BATTLE_MUSIC = "battle.mp3"
