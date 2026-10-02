"""All game content for "The Giants of Holst". build.py turns this into the TTS save + GM guide,
gen_art.py renders the art prompts. Positions are grid squares from the map centre (x right, z up/north).
Map is 22 x 14 squares."""
import math

STYLE = ("painterly dark fantasy illustration, muted earthy colours, dramatic light, "
         "hand-painted texture, highly detailed, no text, no letters")
# scene backdrops are plain ground: the 3D props supply buildings, walls and objects
GROUND_STYLE = ("seen from directly above, flat top-down game ground texture, hand-painted stylized, soft even lighting, "
                "no buildings, no walls, no objects, no people, no text")
GROUNDS = {
    "outskirts": "seamless tileable texture of worn grey medieval cobblestones filling the whole image, mud patches, "
                 "puddles, scattered straw and splinters",
    "sewer": "wet dark grey flagstone floor of a huge underground sewer, a single straight channel of dark murky brown-green "
             "water running from the top edge to the bottom edge through the middle, worn stone kerbs along the channel, "
             "puddles and moss in the cracks",
    "den": "seamless tileable texture of large worn dark grey flagstones evenly filling the whole image, dust and cracks",
    "passage": "dark dungeon floor of cracked flagstones, puddles, patches of moss",
    "cart": "a straight horizontal muddy dirt road crossing the middle of the image from left edge to right edge, "
            "forest floor of dark grass, moss and pine needles above and below the road, deep cart wheel ruts",
    "cave": "rough dark cave floor, cracked rock, gravel and small puddles",
}
MAP_STYLE = ("top-down orthographic battle map for a tabletop rpg, seen from directly above, "
             "painted fantasy map, detailed, even lighting, no text, no grid, no people")

# ---------------------------------------------------------------- heroes
# seat colour = class. fig = TTS built-in figurine.
HEROES = [
    dict(key="thief", name="Wren the Thief", color="Red", fig="rpg_THIEF", hp=18, defense=13,
         stats=dict(Might=0, Agility=3, Wits=2),
         attacks=[("Dagger", 5, "1d6+3", "melee"), ("Throwing knife", 5, "1d4+3", "range 6")],
         blurb="Has never paid for anything twice. Rarely once.",
         traits=["Sneaky: advantage on sneaking and lockpicking (roll 2 d20, keep the best).",
                 "Street smart: knows how thieves' guilds think, talk and hide things."],
         background="Grew up in the alleys of Aldmere's capital and talked his way into the King's service "
                    "instead of the King's dungeon.",
         gear="Twin daggers, throwing knives, lockpicks, rope, a hooded cloak.",
         portrait="a hooded young rogue man with twin daggers, sly smile, short stubble, leather armour, city rooftops at dusk",
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
         blurb="Has been hit by more things than most people have seen.",
         traits=["Speaks a little Dravic: understands simple words and can say a few. Anything harder: Wits DC 12.",
                 "Hard to shift: advantage on checks to hold a door, a line or a giant's leash."],
         background="Veteran of the goblin wars. Picked up his Dravic in border taverns, mostly the rude words.",
         gear="Longsword, dented shield, chainmail, a flask of something strong.",
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
         blurb="Will heal you. Will also tell you it was your own fault.",
         traits=["Healer: stabilising a downed ally is automatic for her (no roll), and still just one action.",
                 "Dawn lore: knows the dying, the undead and what holy symbols mean."],
         background="Battle priest of the Dawn. Keeps everyone breathing, whether they like it or not.",
         gear="Flanged mace, sun pendant, bandages, a small pot of honey for bribing children.",
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
         blurb="Knows four hundred spells. Six of them are useful.",
         traits=["Arcane lore: recognises magic items, runes and spells on sight.",
                 "Old friends: he taught Princess Isolde her first sorcery. She trusts his voice."],
         background="Royal court wizard. Fragile, clever and loud. Tutor to the princess, and not about to lose her.",
         gear="Crooked staff, spellbook, star-embroidered robe, a pipe he is not allowed to light indoors.",
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

RULES = """D20 LITE - HOW TO PLAY
Check or attack: roll d20 + stat. Meet or beat the target.
  Attacks vs the enemy's Defense.  Checks: easy 10, hard 14, heroic 18.
  Natural 20: double damage dice. Natural 1: something goes wrong.
Your turn: move 6 squares + 1 action (attack, play a card, use an item, do a thing).
HP: track it with the - and + on your HP shield. At 0 you are down; an ally can spend an action to stabilise you.
Cards: play any time it makes sense (most are an action). Each card works once,
  then comes back to your hand when the GM calls a REST.
Stats: Might (force, climbing, lifting), Agility (sneak, dodge, lockpick), Wits (notice, know, talk)."""

# ---------------------------------------------------------------- npcs
# attacks: (name, to-hit bonus or None, damage dice or None, note). Attack buttons roll these.
NPCS = {
    "giant_club": dict(name="Giant", fig="rpg_CYCLOP", hp=60, defense=12, attacks=[
        ("Club smash", 7, "2d8+4", "melee, reach 2"),
        ("Hurl rubble", 5, "2d6+2", "range 10"),
        ("Stomp", None, "1d8", "all adjacent: Agility DC 13 or take it and fall prone"),
    ], notes="WICKER SHIELD: ranged attacks against it get -5 unless the shield is burned. Moves 8."),
    "giant_eye": dict(name="Giant", fig="rpg_CYCLOP", hp=55, defense=12, attacks=[
        ("Club smash", 7, "2d8+4", "melee, reach 2"),
        ("Leash yank", None, None, "pulls its thrall back next to it"),
    ], notes="WICKER SHIELD: ranged -5. One eye: a blinding trick (sand, light) makes it miss next turn."),
    "giant_troll": dict(name="Hill Giant", fig="rpg_CYCLOP", scale=1.2, tint=(0.62, 0.8, 0.5), hp=65, defense=11, attacks=[
        ("Fist", 6, "2d6+4", "melee, reach 2"),
        ("Grab", 6, None, "target is held: Might DC 14 to break free, 1d6 each turn"),
    ], notes="WICKER SHIELD: ranged -5. Slow, moves 6."),
    "thrall": dict(name="Leashed thrall", fig="rpg_GHOUL", tint=(0.8, 0.7, 0.6), hp=8, defense=11, attacks=[
        ("Rusty knife", 3, "1d6", "melee"),
    ], notes="Captured looter on a chain. Cutting the leash (Agility DC 12) and the thrall runs off."),
    "street_kid": dict(name="Street kid", fig="rpg_KOBOLD", hp=5, defense=12, attacks=[
        ("Pickpocket", 6, None, "steals 1 gold if it beats the target's Defense"),
    ], notes="Speaks only Dravic. Works for the Bandit Baron."),
    "refugee": dict(name="Refugee", fig="rpg_MAGE", tint=(0.55, 0.5, 0.45), hp=6, defense=10, attacks=[], notes="Hungry and scared."),
    "noble": dict(notable=True, name="Lady Oriska (noble)", fig="rpg_MAGE", tint=(0.75, 0.45, 0.9), hp=10, defense=12, attacks=[],
                  notes="Pays 5 gold per carcass. Has a fat purse and a Healing Draught she'll trade for food."),
    "hunter": dict(name="Hunter", fig="rpg_RANGER", hp=14, defense=13, attacks=[
        ("Short bow", 4, "1d8", "range 10"),
    ], notes="Rough, proud. They hunt the woods outside the walls and bring the game down here to sell. "
             "Trade food for their Wolf-tooth Charm."),
    "carcass": dict(name="Fresh carcass", fig="rpg_WOLF", hp=1, defense=1, attacks=[], notes="Food.", dead=True),
    "rat_count": dict(notable=True, name="Vasko, the Bandit Baron", fig="rpg_THIEF", tint=(0.85, 0.3, 0.25), hp=25, defense=13, attacks=[
        ("Rapier", 5, "1d8+2", "melee"),
        ("Baron's Bones: roll 3d6", None, "3d6", "dice game roll"),
        ("Baron's Bones: reroll 1 die", None, "1d6", "his free reroll each round (ring or rules)"),
        ("Lucky Ring reroll", None, "1d6", "extra reroll from the ring, once per round"),
    ], notes="Wears VASKO'S LUCKY RING (see notes). Laughs a lot, never blinks."),
    "guard": dict(name="Baron's bruiser", fig="rpg_ORC", hp=20, defense=14, attacks=[
        ("Axe", 4, "1d10+2", "melee"),
    ], notes="Two of them. Loyal while Vasko is winning."),
    "log_giant": dict(name="Giant", fig="rpg_CYCLOP", hp=70, defense=12, attacks=[
        ("Log throw", None, "3d6", "2x2 area, Agility DC 14 for half; opening move"),
        ("Club smash", 7, "2d8+4", "melee, reach 2"),
        ("Roar", None, None, "all heroes within 6: Wits DC 12 or lose next move"),
    ], notes="Leader of the ambush. Wicker shield: ranged -5."),
    "dead_thug": dict(name="Trampled guildsman", fig="rpg_THIEF", hp=1, defense=1, attacks=[],
                      notes="Thieves' guild. Search: 3 gold, a guild token, cart keys.", dead=True),
    "dying_giant": dict(name="Hrothga, dying giantess", fig="rpg_RANGER", scale=1.9, tint=(0.85, 0.72, 0.6), notable=True,
                        hp=6, defense=8, attacks=[
        ("Feeble swipe", 3, "1d6", "only if attacked"),
    ], notes="Speaks only Giantish (Tongues / Speak with the Dying / Street Dravic badly). See scene notes."),
    "dead_human": dict(name="Fallen guildsman", fig="rpg_THIEF", hp=1, defense=1, attacks=[], notes="Died fighting.",
                       dead=True),
    "princess": dict(notable=True, name="Princess Isolde", fig="rpg_MAGE", hp=20, defense=12, attacks=[
        ("Moonfire", 6, "2d6", "range 10 (once she's healed)"),
    ], notes="Wounded (lying down, 4 HP). Heal her with the damage box (e.g. -8) and she stands up.",
        dead=True, start_hp=4, tint=(1.0, 0.75, 0.85)),
    "giant_rat": dict(name="Giant rat", fig="rpg_RAT", hp=6, defense=12, attacks=[
        ("Bite", 4, "1d6", "melee"),
    ], notes="Only attacks if the bell trap rings or it's cornered."),
}

# ---------------------------------------------------------------- scenes
# npcs: (npc key, x, z) ; heroes: 4 entry squares ; music: file in music/
def wall_line(prop, x1, z1, x2, z2, scale=1, spacing=1):
    """Props every `spacing` squares from (x1, z1) to (x2, z2), turned to run along the line."""
    n = max(1, round(math.hypot(x2 - x1, z2 - z1) / spacing))
    rot = math.degrees(math.atan2(-(z2 - z1), x2 - x1))       # TTS: rotY turns local +x clockwise seen from above
    return [(prop, round(x1 + (x2 - x1) * i / n, 2), round(z1 + (z2 - z1) * i / n, 2), rot, scale) for i in range(n + 1)]


def rocks(x1, z1, x2, z2, seed, spacing=1.1, big=1.6):
    """Irregular low rock wall from (x1, z1) to (x2, z2): mixed rocks, jittered, random turn and size."""
    import random
    rnd = random.Random(seed)
    n = max(1, int(math.hypot(x2 - x1, z2 - z1) / spacing))
    out = []
    for i in range(n + 1):
        x = x1 + (x2 - x1) * i / n + rnd.uniform(-0.25, 0.25)
        z = z1 + (z2 - z1) * i / n + rnd.uniform(-0.25, 0.25)
        piece = rnd.choice(["rock_a", "rock_b", "rock_c", "rock_d", "rock_e"])
        size = big * rnd.uniform(0.7, 1.1)
        out.append((piece, round(x, 2), round(z, 2), rnd.randrange(360), round(size, 2)))
    return out


def wall_run(prop, x1, z1, x2, z2, height=1.0):
    """Wall segments (1.8 long) stretched to cover exactly from (x1, z1) to (x2, z2)."""
    L = math.hypot(x2 - x1, z2 - z1)
    n = max(1, math.ceil(L / 1.8 - 0.05))
    rot = math.degrees(math.atan2(-(z2 - z1), x2 - x1))
    return [(prop, round(x1 + (x2 - x1) * (i + 0.5) / n, 2), round(z1 + (z2 - z1) * (i + 0.5) / n, 2), rot,
             (round(L / n / 1.8, 3), height, 1)) for i in range(n)]


def passage_walls():
    """The smugglers' tunnel: main corridor west-east (z -2.4..2.4) with three dead-end side passages, 2.2 wide:
    A north at x -3.5, B south at x 1.5, C north at x 6. The south walls are low so players see in."""
    north = [(-10.8, -4.6), (-2.4, 4.9), (7.1, 10.8)]
    south = [(-10.8, 0.4), (2.6, 10.8)]
    out = []
    for x1, x2 in north:
        out += wall_run("wall", x1, 2.4, x2, 2.4)
    for x1, x2 in south:
        out += wall_run("wall", x1, -2.4, x2, -2.4, 0.4)
    for bx, z_end in ((-3.5, 6.6), (6.0, 5.4)):        # north branches A, C
        out += wall_run("wall", bx - 1.1, 2.6, bx - 1.1, z_end) + wall_run("wall", bx + 1.1, 2.6, bx + 1.1, z_end)
        out += wall_run("wall", bx - 1.1, z_end, bx + 1.1, z_end)
    bx, z_end = 1.5, -6.4                                # south branch B (low walls, broken end)
    out += wall_run("wall", bx - 1.1, -2.6, bx - 1.1, z_end, 0.4) + wall_run("wall", bx + 1.1, -2.6, bx + 1.1, z_end, 0.4)
    out += wall_run("wall_broken", bx - 1.1, z_end, bx + 1.1, z_end)
    return [("wall_broken" if p == "wall" and i % 6 == 3 else p, *rest) for i, (p, *rest) in enumerate(out)]


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

    dict(key="outskirts", title="1. Holst City", fog=True, music="outskirts.mp3", battle=True,
         map_prompt="ruined medieval town street with broken houses, smashed carts, huge footprints in mud, scattered debris, a round sewer grate in the cobbles",
         heroes=[(-7, -1), (-7, 0), (-6, -1), (-6, 0)],
         props=[("house_a", -8.2, 5.6, 180), ("ruin_b", -2.8, 5.6, 180), ("tavern", 2.9, 5.4, 180), ("house_b", 7.9, 5.7, 180),
                ("house_d", -9.8, 2.1, 90), ("house_c", -8.4, -5.8, 0), ("stall", -3.4, -5.6, 0, 1.2), ("stall", -1.2, -5.8, 10, 1.2),
                ("ruin_a", 7.9, -5.6, 0), ("house_a", 9.8, 1.6, 270), ("ruin_c", 3.8, -6, 0),
                ("grate", 0, -2.2), ("well", -1, 2), ("broken_cart", -4, -1.6, 40, 1.1),
                ("cart", -5.6, -3.4, 70, 0.9), ("crate", -6.4, -2.4, 20), ("barrel", -6.8, -1.9), ("barrel", -6.3, -1.6),
                ("sack", 1.6, 3.2, 20), ("sack", 2.1, 2.8, 70), ("lumber", 5.6, 2.9, 20),
                ("rubble", -3, 3.3, 10), ("rubble", 6.2, -3, 60), ("rubble", 3.3, -3.3, 20, 0.8), ("crates", 5.4, -4, 30),
                ("door_smashed", -2.0, 3.3, 35), ("giant_club", 5.2, -1.9, 115, 0.6), ("wicker_shield", 2.6, -3.6, 20),
                ("goods", -2.6, -4.3, 10), ("goods", -4.9, -4.2, 200)],
         npcs=[("street_kid", -4, 3), ("street_kid", -3, 4), ("street_kid", -5, 4),
               ("giant_club", 4.5, 2.5), ("giant_eye", 6, 0), ("giant_troll", 6, -3), ("giant_club", 3, 1),
               ("thrall", 3, 4), ("thrall", 4, -1), ("thrall", 4, -3), ("thrall", 2.0, 2.2), ("thrall", 7.2, 1.2),
               ("thrall", 7.4, -2.0), ("thrall", 5.3, 3.6)],
         notes="""Read aloud: "Holst's gate hangs open. Doors are smashed in, from above. Footprints the size
of a cart sink into the mud. Nothing moves - except three thin children watching you."
Clues: roofs torn off; a door ripped out whole; granaries empty; a broken wicker shield bigger than a door.
STREET KIDS (Dravic only): hands out, "Pénz? Pénz?" (money). Fighter can make out "coin" and "hungry".
  - Give them ANY gold or food -> note it. Later the Bandit Baron's crew vouches for the party (scene 3:
    Vasko starts friendly, first Baron's Bones round is won automatically) and the kids give the party the
    WARREN WHISTLE (magic: blow it, 1d4 street kids appear to help or distract, once).
  - Ignore/threaten them -> they vanish; one tries to pickpocket (Pickpocket button).
GIANTS: after a few minutes, ground shakes. Press REVEAL ALL ENEMIES. Four giants round the
corner with thralls on chains, wicker shields raised. THIS FIGHT IS MEANT TO BE FLED.
  Switch to BATTLE music. Giants move 8 (the Hill Giant 6), thralls 6. Let them feel the danger: first giant hit is big.
  Escape: the sewer grate (centre-south). Might DC 12 to lift, or the kids point at it and scatter.
  Anyone who jumps in: next scene."""),

    dict(key="sewer", title="2. The Sewer Warren", fog=True, music="sewer.mp3", rest=True,
         map_prompt="underground stone sewer cavern with a refugee camp, tents made of rags, small fires, a central channel of dark water, crates",
         heroes=[(-5, 1), (-5, 2), (-4, 1), (-4, 2)],
         props=wall_line("wall", -9.9, 6.3, 9.9, 6.3, spacing=1.8) + wall_line("wall", -10.4, -6, -10.4, 4.8, spacing=1.8)
               + wall_line("wall", 10.4, -6, 10.4, 4.8, spacing=1.8)
               + [("tent", -8, 3.6, 30), ("tent", -8.3, -3.4, 150), ("tent", -5.8, 4.8, 10),
                  ("bed", -6.2, 2.4, 90), ("bed", -7, -1.2, 0), ("bed", -5.4, -4.6, 60), ("bed", -9, 1.3, 20),
                  ("torch", -6, 0.6), ("torch", -3.8, -5.2), ("torch", 8.6, -3.4), ("torch", 4.4, 4.6),
                  ("bridge", 0, 0.6), ("bridge", 0.1, -4.4, 5),
                  ("crates", 8.6, 3.8), ("barrel", 7.6, 4.6), ("barrel", 7.9, 4.1), ("sack", 3.4, 0.2, 30), ("sack", 3.8, -0.4),
                  ("crate", 5.6, 1.2, 15), ("keg", -9.2, -0.4, 90), ("rubble", 3.2, 5.2, 0, 0.7)],
         npcs=[("refugee", -6.3, 3.2), ("refugee", -6.6, -1.6), ("refugee", -3.6, -3), ("refugee", 4.3, -4.5),
               ("noble", 4, -1.5), ("hunter", 8, -0.5), ("hunter", 7.4, -2.6), ("carcass", 5.6, -2.9), ("carcass", 6.5, -1.2)],
         notes="""Read aloud: "You drop into stink and darkness. Then - firelight. Hundreds of people live down here
in rags and smoke. Holst didn't empty. It went underground."
FOOD SCENE: two rough hunters come in from outside the walls, dragging carcasses from the woods. A noblewoman (Lady Oriska) pays 5 gold EACH, loudly.
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
         props=[("wall_sconce" if i % 3 == 0 else "wall", *rest) for i, (_, *rest) in enumerate(ring("wall", 9.4, 6.8, 30, gap=(-8, 8)))]
               + [("wall_door", 9.4, 0, 90)]
               + [("pillar", round(6.6 * math.cos(math.radians(t)), 2), round(4.8 * math.sin(math.radians(t)), 2))
                  for t in (40, 90, 140, 220, 270, 320)]                       # cistern columns
               + [("rug", 0, 0, 15), ("table_feast", 0, 0, 0, 1.5), ("chair", -1.1, 0, 90, 1.2), ("chair", 0, 1.1, 180, 1.2),
                  ("chair", 0, -1.1, 0, 1.2), ("throne_dais", 5.0, 0, 270), ("banner", 6.1, 1.4, 90), ("banner", 6.1, -1.4, 90),
                  ("candelabra", -1.7, 1.7), ("candelabra", -1.7, -1.7), ("candelabra", 3.6, 1.3), ("candelabra", 3.6, -1.3),
                  ("torch", -3, 3), ("torch", 3, 3.4), ("torch", -3, -3), ("torch", 3, -3.4),
                  ("hoard", 7.2, 3.4, 200), ("hoard_b", 7.2, -3.4, 330), ("chest_gold", -6, -4.2, 20), ("coins", 5.9, 4.6),
                  ("keg", -7.3, 2, 90), ("keg", -7.6, 0.8, 90), ("crates", -6.9, -2.6),
                  ("barrel", -4.5, 5.2), ("barrel", -4, 5.5), ("chest", -3, -5.3, 10)],
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
         props=passage_walls()
               + [("wall_door", -10.8, 0, 90), ("pillar", -10.8, 1.6), ("pillar", -10.8, -1.6),
                  ("rubble", -4, 1.4, 20, 0.7), ("rubble", 5, -1.4, 200, 0.7), ("torch", -6, 1.7),
                  ("torch", -0.5, -1.7), ("torch", 8.5, 1.7), ("chest", -2.6, -1.5, 80),
                  # A: old guard post (north, x -3.5)
                  ("chest", -3.5, 6.0, 0), ("torch", -4.3, 5.4), ("rubble", -2.9, 4.4, 60, 0.6),
                  # B: collapsed stash (south, x 1.5)
                  ("rubble", 1.5, -5.6, 0, 1.1), ("barrel", 0.9, -4.6), ("sack", 2.0, -4.2, 40), ("crate", 1.9, -3.4, 15),
                  # C: rats' nest (north, x 6)
                  ("bed", 5.6, 4.6, 20), ("bed", 6.4, 4.0, 110), ("sack", 6.6, 4.9, 70), ("rubble", 5.4, 3.4, 140, 0.5)],
         npcs=[("giant_rat", 5.6, 3.6), ("giant_rat", 6.4, 3.2)],
         notes="""Read aloud: "The door grinds shut behind you. The kid is gone. The tunnel runs west to east,
narrow and old. Your torch shows scratches on the floor - and a skeleton still holding a torch."
FOUR TRAPS, west to east. Wits DC 13 to spot each (Detect Magic reveals the gas vent's rune).
Disarm: Agility DC 13 (Nimble Fingers auto). Triggered effects:
  1. DART PLATE (column -6): darts from the walls, 2d4 to whoever steps on it.
  2. COLLAPSING FLOOR (column -1): 2x2 drops into a 3m pit. Agility DC 13 or fall, 1d6 +
     Might DC 12 to climb out (allies can help).
  3. SLEEP GAS VENT (column +4): Might DC 12 or sleep 1d4 minutes (real time is funny). Rune-marked.
  4. BELL TRIPWIRE (column +8): harmless... unless it rings: the 2 giant rats in their nest (C) attack.
SIDE PASSAGES (optional, each off the main tunnel):
  A. OLD GUARD POST (north, column -3.5): a skeleton slumped by a chest. LOOT: the skeleton has a LANTERN OF
     TRUE SIGHT (magic: once, see through illusions/invisibility for a scene) - hint: the princess will be hard
     to see in the cave. The chest is locked (Agility DC 12): 15 gold, a rope.
  B. COLLAPSED STASH (south, column +1.5): smugglers' goods half buried under a roof fall. Wits DC 12 notices the
     ceiling is loose; digging out the barrel without care brings more down (1d6, Agility DC 12 halves).
     Inside: 3 rations and a SMOKE EGG (magic: works like Smoke Bomb, once).
  C. RATS' NEST (north, column +6): the 2 giant rats sleep on stolen bedding. Sneaking past: Agility DC 11.
     The bell tripwire (trap 4) wakes them. In the nest: a gnawed purse, 8 gold.
Exit (far east): a hatch into a ditch well outside the city walls. Cart tracks in the mud."""),

    dict(key="cart", title="5. The Broken Cart", fog=True, music="cart.mp3", battle=True,
         map_prompt="a muddy country road through a pine forest, a smashed wooden cart on its side, broken wheel, scattered crates and cloth, huge footprints, a tree trunk lying across the road",
         heroes=[(-1, -6), (0, -6), (1, -6), (0, -5)],
         props=[("broken_cart", 0.2, 0.6, 60, 1.2), ("log_large", 2.8, 2, 25),
                ("crate", -1.8, 2.4, 10), ("crate", 1.9, -1.2, 40), ("sack", -1, -1.4, 30), ("sack", 1.2, 2.9, 80),
                ("pines", -9, 5), ("pines", -9.5, -5.6, 90), ("pines", 9.6, 1, 180), ("pines", 9.8, -6.6, 270),
                ("oaks", -9.6, 0.4, 40), ("pine", -7, 6.6), ("pine_b", 7, 6.6), ("pine", 10.4, 3.8), ("oak", 6.8, -6.2),
                ("pine_b", -6.8, -6.6), ("oak", 6.7, 2.9, 40),
                ("stump", -6.4, 2.8, 0, 1.4), ("stump", 6.5, -1.8, 0, 1.4), ("rock_c", -6.5, -2.5, 30, 1.2), ("rock_a", 6.3, 5)],
         npcs=[("dead_thug", -1.6, 1.4), ("dead_thug", 1.6, -0.3), ("dead_thug", -0.6, -1.9),
               ("log_giant", 8.3, 4.4, 45), ("giant_club", -8.3, -2.4, 35), ("giant_eye", 8, -3.8, 35)],
         notes="""Read aloud: "The tracks lead north into the pines. An hour later you find the cart - or what's
left of it. It's been stamped flat. So have the men who drove it."
INVESTIGATE (Wits DC 12): guild tokens (a black hand), a broken iron cage in the cart - empty, bent
OUTWARD, scorched. Something burned its way out. Giant footprints lead north-east.
GUILD LOCKBOX (under the cart, Agility DC 13 or cart keys): HEALING DRAUGHT (2d8+2) and a SMOKE EGG
(magic: works like Smoke Bomb, once).
AMBUSH: when they're busy at the cart, a whole tree trunk flies out of the woods. the biggest giant's LOG THROW
opens the fight (2x2 on the cart). Switch to BATTLE music, press REVEAL ALL ENEMIES. 3 giants.
These giants are already hurt from the cart fight (lower HP). Fire burns wicker shields.
When the first giant falls the others hesitate; when the second falls the last one flees north-east (to the cave).
If the party arrives badly hurt from the traps, let them REST at the passage exit first.
After: tracks and blood lead to a cave in the hillside."""),

    dict(key="cave", title="6. The Last Stand Cave", fog=True, music="cave.mp3",
         map_prompt="inside a large dark natural cave, rocky floor, a tall shaft in the far wall rising into darkness, fallen weapons, a broken wicker shield, faint light from a crack above",
         heroes=[(0, -6), (1, -6), (0, -5), (1, -5)],
         props=rocks(-10, 6.8, -1.6, 6.8, 4) + rocks(1.6, 6.8, 10, 6.8, 5) + rocks(-10, -6.8, -2, -6.8, 6)
               + rocks(3, -6.8, 10, -6.8, 7) + rocks(-10.4, -5.8, -10.4, 5.8, 8) + rocks(10.4, -5.8, 10.4, 5.8, 9)
               + [(r, x, z, (x * 53 + z * 29) % 360, 2) for r, x, z in [("rock_b", -8, 4.5), ("rock_d", -8, -4.4),
                                                                         ("rock_e", 8, 4.5), ("rock_b", 8.2, -1.2)]]
               + [("stalagmite", x, z, (x * 31) % 360) for x, z in [(-5.5, 3.8), (4.8, 4.2), (-6, -2.8), (5.6, 1.5), (-3, 5)]]
               + [("rubble", -1.6, 5.6, 0, 0.8), ("rubble", 1.8, 5.6, 180, 0.8), ("rock_b", 2.8, -2.4, 30, 1.4),
                  ("rock_d", 2.8, -0.4, 80, 1.1), ("campfire_cold", -1.3, 0.8), ("rubble", 4, 2.5, 0, 0.6), ("torch", -3.5, -1),
                  ("wicker_shield", 4.4, -3.2, 130, 0.9), ("giant_club", 7.6, -3.0, 75, 0.55)],
         npcs=[("dead_human", -3, 2), ("dead_human", -2, -2), ("dead_human", 0.5, -0.5), ("dying_giant", 6, -4.8),
               ("princess", 0, 6)],
         notes="""Read aloud: "The cave stinks of blood and smoke. The guild made their last stand here -
three bodies around a burnt-out fire. In the corner, leaning against the rock, a giantess. Still breathing."
HROTHGA (dying giantess): speaks Giantish only. Tongues / Speak with the Dying lets them talk; Street Dravic
gets a few words. She is not hostile, just dying. What she knows:
  - "The little thieves took the Hearthstone from our mountain. Our shrine is cold. We came for it."
  - "We found the little witch in the thieves' cage. She is the Pact-maker. We wanted her to speak for us."
  - "The thieves fought. She... became a bird. White bird. Flew up." (points up the shaft to the north)
  - If healed/fed: "Tell your king: give back the Hearthstone and the mountains are quiet again."
  - She carries a GIANT'S TOOTH AMULET (magic: once, Might check auto-succeeds) and gives it if treated kindly.
THE SHAFT (north, where the light comes in): 10 squares straight up. Might DC 15 climb (fail: 1d6, try again), rope + one
climber, or LEVITATE. The LANTERN OF TRUE SIGHT shows her hiding place (otherwise Wits DC 14).
ISOLDE: in a ledge up the shaft, human again, wounded but alive. Heal her or give her food (she stands).
She keeps a shard of her MOONSTAFF (magic, gift to whoever reached her first: once, cast Fireball).
Read aloud: "A pale young woman in torn blue silk opens her eyes. 'Took you long enough.'"
THE END. (Optional epilogue: she promises to return the Hearthstone and renew the Pact.)"""),
]

BATTLE_MUSIC = "battle.mp3"

# ---------------------------------------------------------------- GM desk (GM-only, beside the table)
# magic items as cards the GM hands out: (name, rules text, card art prompt, copies)
ITEMS = [
    ("Warren Whistle", "Blow it once: 1d4 street kids turn up to help or cause a distraction.",
     "a small carved bone whistle on a leather cord lying on worn cobblestones, warm candlelight", 1),
    ("Wolf-tooth Charm", "Once: reroll a failed Agility or Might check.",
     "a necklace of wolf teeth and leather strips with a carved bone bead on rough dark wood", 1),
    ("Healing Draught", "Drink (an action): heal 2d8+2 HP. One use.",
     "a small round glass flask of glowing red potion with a cork stopper on a wooden table", 2),
    ("Smoke Egg", "Throw it: works like Smoke Bomb, a 3x3 area is hidden until they act. One use.",
     "a grey clay egg-shaped bomb with a short smouldering fuse, wisps of smoke curling from it", 2),
    ("Vasko's Lucky Ring", "Once per scene: reroll any die you can see.",
     "a heavy gold signet ring with a rat crest and a faintly glowing green gem on red velvet", 1),
    ("Lantern of True Sight", "Once: for one scene, see through illusions and invisibility.",
     "an old engraved brass lantern glowing with pale blue magical light in a dark stone tunnel", 1),
    ("Giant's Tooth Amulet", "Once: one Might check automatically succeeds.",
     "a huge yellowed giant's tooth carved with swirling spiral patterns hanging from a thick braided rope on dark stone", 1),
    ("Moonstaff Shard", "Once: cast Fireball (3x3 area, 3d6 fire, Agility DC 14 for half).",
     "a broken shard of a silver staff with a glowing crescent moon crystal, sparks of light", 1),
]
# per scene: 360 backdrop around the table (prompt) and the mood light (colour, brightness x the default)
SKY_STYLE = ("An equirectangular 360 degree panorama, seen from eye level. A painterly dark fantasy illustration "
             "in muted earthy colours with soft atmospheric light.")
SKIES = {
    "title": ("A cosy medieval tavern hall at night with a roaring stone hearth, heavy wooden beams, candles and "
              "shelves of bottles.", (1.0, 0.85, 0.65), 1.0),
    "outskirts": ("A walled medieval city burning at dusk, columns of smoke rising over timber-framed rooftops, a red "
                  "sky and the hazy silhouettes of giants between the towers.", (1.0, 0.78, 0.6), 0.9),
    "sewer": ("A vast underground brick sewer with tall vaulted arches, dark water channels and the warm glow of "
              "refugee campfires in the gloom.", (0.75, 0.9, 0.8), 0.65),
    "den": ("A candlelit underground stone cistern hall with thick columns, stolen chandeliers, red drapes and heaps "
            "of glittering loot.", (1.0, 0.75, 0.5), 0.75),
    "passage": ("A long dark stone tunnel lit by a few flickering wall torches, damp walls, cobwebs and deep "
                "shadows.", (0.8, 0.8, 0.95), 0.55),
    "cart": ("A misty pine forest at dusk along a muddy country road, tall dark trees and fog drifting between the "
             "trunks.", (0.85, 0.9, 1.0), 0.85),
    "cave": ("Inside a huge dark natural cave, jagged rock walls and a shaft of pale light falling from a crack high in "
             "the ceiling.", (0.7, 0.75, 0.9), 0.55),
}
SCREEN_ART = ("Three huge cyclops giants, muscular grey-skinned brutes each with a single large eye in the middle of "
              "the forehead, carrying round wicker shields and tree-trunk clubs, smashing a burning medieval town at dusk "
              "while tiny townsfolk flee below them")
