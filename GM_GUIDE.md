# The Giants of Holst - GM guide

## Setup

- Host the game and take the **Black (Game Master)** seat. The GM panel (top right) is only visible to Black/host.
- Players join and click their adventurer on the pick panel. Their seat changes, cards are dealt automatically.
- Right-click an NPC (GM-only entries): *Take damage* (`12` hurts, `-5` heals; or hover and type the number),
  and one entry per attack. Attacks whisper the roll to you (Black); crits add an extra set of damage dice.
- *Conditions...* on an NPC: Poisoned (3 turns), Frozen, Blinded, Shrunk, Prone (1 turn); pick again to remove.
  They show above its bar. On its turn (Next turn) poison deals 1d6 by itself; the others whisper you a reminder.
- Giants also have *Grab nearest hero* (within 6 squares, held up in the fist), then *Throw the hero* (4-6 squares,
  2d6, prone) or *Let go* (they broke free, Might DC 14). Revealing the chainmaster shakes the ground.
- Fireballs leave scorch marks until the scene changes. A hero's natural 20 / natural 1 on their d20 gets a flourish.
- Hiding things: select NPCs or props (drag a box) and press *Toggle visibility (selected)* in a GM menu, or
  bind the *Toggle visibility (GM)* hotkey (Options > Game Keys). Hidden things vanish for players and show
  see-through with an outline for you. Press again to show them.
- The same text as below sits in the Notebook (GM-only tabs).

## Rules

```
D20 LITE - HOW TO PLAY
Roll: roll a d20 and add your stat. Meet or beat the number. Attacks must beat the enemy's Defense.
  Natural 20: double damage dice. Natural 1: something goes wrong.
Difficulty: easy 10, hard 14, heroic 18.
Your turn: move 6 squares, then take 1 action: attack, play a card, use an item or try something.
HP: use - and + on your HP shield. At 0 you are down. An ally can spend an action to stabilise you.
Cards: most cost your action. Each works once, then comes back when the GM calls a REST.
Items: the bottom line says if it costs your action or is free, and if it is used up (give it to the GM).
Stats: Might: force, climb, lift.
  Agility: sneak, dodge, pick locks.
  Wits: notice, know, talk.
Initiative: roll your d20 when the GM asks. Your Agility is added for you. The strip on top shows whose turn it is.
Search: right-click a chest, barrel, crate or sack next to your hero, then Search. Once each.
```

## Heroes

**Wren the Thief** (Red) HP 18, Def 13, Might +0, Agility +3, Wits +2
- Card *Shadowstep*: Instead of your move: move up to 6 squares unseen. Your next attack this turn rolls 2d20, keep the best.
- Card *Backstab*: Free action, after you hit: add +2d6 damage.
- Card *Nimble Fingers*: Auto-succeed one lockpick, pickpocket or trap-disarm check.
- Card *Smoke Bomb*: Everyone in a 3x3 area is hidden until they act. Enemies can't target allies inside.
- Card *Luck*: Free action, any time: reroll any one die on the table, yours or anyone else's.
- Card *Poisoned Blade*: Free action: your next hit also deals 1d6 at the start of the target's next 3 turns.

**Brannoc the Fighter** (Blue) HP 30, Def 15, Might +3, Agility +1, Wits +0
- Card *Cleave*: Make one attack roll against every enemy adjacent to you.
- Card *Shield Wall*: Free action: until your next turn, you and adjacent allies get +3 Defense.
- Card *Taunt*: All enemies that can see you must attack you this round.
- Card *Second Wind*: Heal 1d10+5 HP. Free action.
- Card *Mighty Heave*: Throw an object or a human-sized foe up to 4 squares: 2d6 damage to what it hits.
- Card *Speak Giant*: Understand and speak Giant for one whole conversation. +5 to persuade or intimidate a giant.

**Sister Maelis the Healer** (Green) HP 22, Def 13, Might +1, Agility +0, Wits +3
- Card *Mending Touch*: Heal an adjacent ally 2d8+3.
- Card *Prayer of Light*: Every ally within 6 squares heals 1d8.
- Card *Blessing*: One ally adds +1d4 to all rolls until the end of the fight.
- Card *Sanctuary*: Target can't be attacked until it attacks or the fight ends.
- Card *Revive*: An ally at 0 HP stands up with half their HP.
- Card *Kind Heart*: One NPC nearby warms to you: until the talk ends it treats the party as trusted friends, and every ally gets +5 to persuade it.

**Aldric the Wizard** (Purple) HP 16, Def 11, Might +0, Agility +1, Wits +3
- Card *Fireball*: 3x3 area: 3d6 fire, Agility DC 14 for half. Burns wicker shields to ash.
- Card *Shrink*: One creature nearby shrinks to a third of its size until the end of its next turn: it deals half damage, and it can be grappled and shoved with advantage.
- Card *Levitate*: Lift yourself or one ally up to 10 squares straight up, and set them down gently.
- Card *Mirror Image*: Until the fight ends, every attack against you: roll a d6, on 1-3 it hits an illusion instead.
- Card *Frost Nova*: Enemies adjacent to you take 1d6 and can't move on their next turn.
- Card *Detect Magic*: The GM points out every magic item and magical trap nearby.

## NPCs

- **Giant** HP 60, Def 12. Club Smash (+6, 2d8+2, melee, reach 2); Stomp (no roll, 1d8, all adjacent: Agility DC 13 or take it and fall prone). WICKER SHIELD: ranged attacks against it get -5 unless the shield is burned. Moves 8.
- **Giant Thrower** HP 50, Def 12. Hurl Rubble (+5, 2d6+2, range 10); Hurl Cart Wheel (no roll, 2d8, a line 6 long, Agility DC 13 for half); Club Smash (+6, 2d8+2, melee, reach 2). Hangs back and throws whatever the street offers. Moves 8.
- **Giant** HP 55, Def 12. Club Smash (+6, 2d8+2, melee, reach 2); Kick (+6, 1d10+2, melee, target flies 3 squares and falls prone). WICKER SHIELD: ranged -5. One eye: a blinding trick (sand, light) makes it miss next turn.
- **Giant Chainmaster** HP 65, Def 11. Fist (+6, 2d6+4, melee, reach 2); Crack the Chains (no roll, -, every thrall moves 3 and makes a free Rusty Knife attack); Reel in (+6, -, range 6: target is dragged next to him and held, Might DC 14 to break free). Holds all the thralls' chains. THRALL SHIELD: when he is hit, an adjacent thrall can take the blow instead. Kill or drop him and the chains go slack: every thrall flees. Slow, moves 6.
- **Leashed Thrall** HP 8, Def 11. Rusty Knife (+3, 1d6, melee). Captured looter on the Chainmaster's chain. Cutting the leash (Agility DC 12) and the thrall runs off.
- **Street Kid** HP 5, Def 12. Pickpocket (+6, -, steals 1 gold if it beats the target's Defense). Works for the Bandit Baron.
- **Refugee** HP 6, Def 10. . Hungry and scared.
- **Old Pell (Merchant)** HP 8, Def 10. . Sells from his pack and the barrels behind him: rope, torches, lamp oil, chalk, 1 gold each. Out of food. Knows the Bandit Baron's men buy his best wine every night.
- **Lady Oriska (Noble)** HP 10, Def 12. . Pays 5 gold per carcass. Has a fat purse and a Healing Draught she'll trade for food.
- **Hunter** HP 14, Def 13. Short Bow (+4, 1d8, range 10). Rough, proud. They hunt the woods outside the walls and bring the game down here to sell. Trade food for their Wolf-tooth Charm.
- **Giant Rat Carcass** HP 1, Def 1. . Food.
- **Vasko, the Bandit Baron** HP 35, Def 13. Rapier (+5, 1d8+2, melee); Baron's Bones: Roll 3d6 (no roll, 3d6, dice game roll); Baron's Bones: Reroll 1 Die (no roll, 1d6, his free reroll each round (ring or rules)); Lucky Ring Reroll (no roll, 1d6, extra reroll from the ring, once per round). Wears THE BARON'S LUCKY RING (see notes). Laughs a lot, never blinks. Fights to the end, no surrender.
- **Baron's Bruiser** HP 30, Def 14. Axe (+5, 1d10+3, melee). Two of them. Loyal while Vasko is winning.
- **Giant** HP 70, Def 12. Log Throw (no roll, 3d6, 2x2 area, Agility DC 14 for half; opening move); Club Smash (+6, 2d8+2, melee, reach 2); Roar (no roll, -, all heroes within 6: Wits DC 12 or lose next move). Leader of the ambush. Wicker shield: ranged -5.
- **Trampled Guildsman** HP 1, Def 1. . Thieves' guild. Search: 3 gold, a guild token, cart keys.
- **Hrothga, Dying Giantess** HP 6, Def 8. Feeble Swipe (+3, 1d6, only if attacked). Speaks only Giant (Speak Giant, or Brannoc's few words). See scene notes.
- **Fallen Guildsman** HP 1, Def 1. . Died fighting.
- **Princess Isolde** HP 20, Def 12. Moonfire (+6, 2d6, range 10 (once she's healed)). Wounded (lying down, 4 HP). Heal her with the damage box (e.g. -8) and she stands up.
- **Giant Rat** HP 6, Def 12. Bite (+4, 1d6, melee). Only attacks if the bell trap rings or it's cornered.

## The Giants of Holst

```
PARTY SELECT. Players click their adventurer on the pick panel (top of screen). One each.
Read aloud:
  "By order of King Aldwin of Aldmere: Princess Isolde has not returned from Holst, in the
  land of Dravmark. She went as royal envoy to renew the Mountain Pact with the giants.
  Word is the giants have come down from the mountains and are raiding the towns. Find her.
  Bring her home."
Give them 10 gold and 3 rations each.
Background (GM only): the giants' sacred Hearthstone was stolen from their mountain shrine and
fenced in Holst by the thieves' guild. The giants came to take it back - and everything else.
```

## 1. Holst City

```
Read aloud: "Holst's gate hangs open. Doors are smashed in, from above. Footprints the size
of a cart sink into the mud. Nothing moves - except three thin children watching you."
Clues: roofs torn off; a door ripped out whole; granaries empty; a broken wicker shield bigger than a door.
STREET KIDS: hands out, "Coin? Spare a coin? We're hungry."
  - Give them ANY gold or food -> note it. Later the Bandit Baron's crew vouches for the party (scene 3:
    Vasko starts friendly, first Baron's Bones round is won automatically) and the kids give the party the
    WARREN WHISTLE (magic: blow it, 1d4 street kids appear to help or distract, once).
  - Ignore/threaten them -> they vanish; one tries to pickpocket (Pickpocket button).
GIANTS and thralls start hidden (see-through for you). After a few minutes the ground shakes: select them and
TOGGLE VISIBILITY. Four giants round the
corner with thralls on chains, wicker shields raised. THIS FIGHT IS MEANT TO BE FLED.
  Press INITIATIVE (battle music, grid, health bars). Giants move 8 (the Chainmaster 6), thralls 6.
  The Chainmaster (big, green base) holds every thrall's chain: drop him and the thralls scatter. Let them feel the danger: first giant hit is big.
  Escape: the sewer grate (centre-south). Might DC 12 to lift, or the kids point at it and scatter.
  Anyone who jumps in: next scene.
```

## 2. The Sewer Warren

```
Read aloud: "You drop into stink and darkness. Then - firelight. Hundreds of people live down here
in rags and smoke. Holst didn't empty. It went underground."
FOOD SCENE: two rough hunters come in from outside the walls, dragging carcasses from the woods. A noblewoman (Lady Oriska) pays 5 gold EACH, loudly.
Refugees stare. Food is worth more than gold here: 1 ration = 5 gold, or a favour.
  - Hunters sell their WOLF-TOOTH CHARM for 2 rations (magic: once, reroll a failed Agility or Might check).
  - Lady Oriska trades a HEALING DRAUGHT (heal 2d8+2) for 1 ration. Or steal it (Agility DC 14).
  - OLD PELL the merchant (top right, by his barrels): rope, torches, lamp oil, chalk for 1 gold each. No food.
  - LOADED GOLD DIE: hidden in the barrel nearest Pell (Wits DC 12 to search). Always lands on 6.
    Reveal it with the visibility hotkey when found; it's worth a lot at Vasko's dice table.
    Buy something and he gossips: the Bandit Baron's men collect his best wine every night, east tunnel.
  - Sharing food with a refugee family: an old man tells them "the Bandit Baron knows everything in the drains".
ASKING ABOUT THE PRINCESS:
  "A lady in blue with glowing hands? The Bandit Baron's boys brought her through a week ago."
Anyone who asks around gets pointed to the Bandit Baron's den (east). If they paid the kids, a kid appears and leads them.
REST here is allowed (press REST): full HP, all cards back to hand.
```

## 3. The Bandit Baron's Den

```
Read aloud: "Stolen chandeliers, three rugs on top of each other, a velvet throne with the stuffing
out. On it: a thin man in a noble's coat three sizes too big, rolling bones in one hand. Vasko,
the Bandit Baron. The street kids sit around him like cats."
He speaks broken Common: "Information is food. You want food, you play."
RAT'S BONES (dice game) - best of 3 rounds:
  1. Each side rolls 3d6 (players use table dice; Vasko: his button).
  2. Each side may reroll ANY of their dice once (Vasko: reroll button per die).
  3. Rank: TRIPLE > STRAIGHT (e.g. 3-4-5) > PAIR (higher pair wins) > highest total.
  One hero plays, others may "help" (cards: Luck rerolls one die; Blessing adds +1d4 to the total).
  THE LOADED GOLD DIE (if they found it in the sewer): always a 6. Swapping it in unseen: Agility DC 13;
    Vasko notices a gold die on Wits DC 12 (he'd know - it's how he'd cheat too).
  Stakes: party loses -> hand over all food and gold. Party wins -> he talks.
  THE RING: Vasko secretly rerolls once more per round with THE BARON'S LUCKY RING (use its button).
    Wits DC 14 to notice his ring glowing when he rerolls. Calling it out: he laughs, sets it aside
    for "fairness" (no more ring rerolls) - and now it's on the table.
  STEALING THE RING (optional heist): Agility DC 16 while he's rolling (Nimble Fingers auto-succeeds,
    Smoke Bomb or a distraction gives +5). Caught -> the bruisers attack, kids scatter.
  THE BARON'S LUCKY RING (magic): once per fight, reroll any die you can see.
TREASURE CHEST (gold chest behind the throne, north side): Locked (Agility DC 15 to pick, Might DC 16 to smash - loud, the bruisers come). Inside: 20 gold and a LIGHTNING ROD.
  Opening it under his nose needs a distraction (the dice game is one); the key is on the ring cord around his neck.
  LIGHTNING ROD (magic): chain lightning 2d6 + 1d6 to 2 more enemies, once per fight.
IF THEY WIN: "The girl? Yes, I kept her. A princess eats a lot. Sold her to the guild boys, the
  Shadow Hands. They meant to ransom her to your king. Took her out by cart, north road, three days ago."
  He whistles; a kid leads them to the hidden door (east wall): the old smugglers' passage.
IF THEY LOSE: take their food and gold. He still sells the info for "a favour": they must carry a
  message out of the city. Then the same kid leads them to the door.
If paid the kids earlier: Vasko starts friendly and the first round is given to the party.
```

## 4. The Smugglers' Passage

```
Read aloud: "The door grinds shut behind you. The kid is gone. The tunnel runs west to east,
narrow and old. Your torch shows scratches on the floor - and a skeleton still holding a torch."
FOUR TRAPS, west to east (GM-only markers on the map; hover one for its DCs).
Wits DC 13 to spot each (Detect Magic reveals the gas vent's rune).
Disarm: Agility DC 13 (Nimble Fingers auto). Triggered effects:
  1. DART PLATE (column -6): darts from the walls, 2d4 to whoever steps on it.
  2. COLLAPSING FLOOR (column -1): 2x2 drops into a 3m pit. Agility DC 13 or fall, 1d6 +
     Might DC 12 to climb out (allies can help).
  3. POISON GAS VENT (column +4): green gas floods the tunnel. Everyone within 2 squares: Might DC 12.
     Fail: 2d6 poison damage and POISONED (-2 to all rolls until a rest). Success: half damage. Rune-marked.
     Right-click the vent marker > "Release the gas" for the green cloud.
  4. BELL TRIPWIRE (column +8): harmless... unless it rings: the 2 giant rats in their nest (C) attack.
SIDE PASSAGES (optional, each off the main tunnel; hover a chest/barrel/sack for its loot):
  A. OLD GUARD POST (north, column -3.5): a skeleton slumped by a chest. LOOT: in a little cage by the skeleton, a
     SNIFFER FERRET, still alive (the smugglers' pet: it finds one hidden person, loot, door or trap) - hint: the
     princess will be hard to find in the cave. The chest is locked (Agility DC 12): 15 gold, a rope.
  B. COLLAPSED STASH (south, column +1.5): smugglers' goods half buried under a roof fall. Wits DC 12 notices the
     ceiling is loose; digging out the barrel without care brings more down (1d6, Agility DC 12 halves).
     Inside: 3 rations and a SMOKE EGG (throw it: a 3x3 area is hidden in smoke for one round).
  C. RATS' NEST (north, column +6): the 2 giant rats sleep on stolen bedding. Sneaking past: Agility DC 11.
     The bell tripwire (trap 4) wakes them. In the nest: a gnawed purse, 8 gold.
Exit (far east): a hatch into a ditch well outside the city walls. Cart tracks in the mud.
```

## 5. The Broken Cart

```
Read aloud: "The tracks lead north into the pines. An hour later you find the cart - or what's
left of it. It's been stamped flat. So have the men who drove it."
INVESTIGATE (Wits DC 12): guild tokens (a black hand), a broken iron cage in the cart - empty, bent
OUTWARD, scorched. Something burned its way out. Giant footprints lead north-east.
GUILD LOCKBOX (under the cart, Agility DC 13 or cart keys): HEALING DRAUGHT (2d8+2), a SMOKE EGG (3x3 smoke for one round)
and a POTION OF GIANTISM (twice your size until the fight ends, +1d4 melee damage, advantage on Might checks).
AMBUSH: when they're busy at the cart, a whole tree trunk flies out of the woods. the biggest giant's LOG THROW
opens the fight (2x2 on the cart). Select the giants and TOGGLE VISIBILITY (all start hidden), then press INITIATIVE. 3 giants.
CHAINMASTER (north-west, with 3 thralls): only if he survived Holst City. Otherwise leave him and his thralls hidden.
These giants are already hurt from the cart fight (lower HP). Fire burns wicker shields.
When the first giant falls the others hesitate; when the second falls the last one flees north-east (to the cave).
If the party arrives badly hurt from the traps, let them REST at the passage exit first.
After: tracks and blood lead to a cave in the hillside.
```

## 6. The Last Stand Cave

```
Read aloud: "The cave stinks of blood and smoke. The guild made their last stand here -
three bodies around a burnt-out fire. In the corner, leaning against the rock, a giantess. Still breathing."
HROTHGA (dying giantess): speaks Giant only. Brannoc's Speak Giant card lets them talk; without it
he gets a few simple words. Kind Heart makes her trust them. She is not hostile, just dying. What she knows:
  - "The little thieves took the Hearthstone from our mountain. Our shrine is cold. We came for it."
  - "We found the little witch in the thieves' cage. She is the Pact-maker. We wanted her to speak for us."
  - "The thieves fought. She... became a bird. White bird. Flew up." (points up the shaft to the north)
  - If healed/fed: "Tell your king: give back the Hearthstone and the mountains are quiet again."
THE SHAFT (north, where the light comes in): 10 squares straight up. Might DC 15 climb (fail: 1d6, try again), rope + one
climber, or LEVITATE. The SNIFFER FERRET finds her hiding place (otherwise Wits DC 14).
ISOLDE: in a ledge up the shaft, human again, wounded but alive. Heal her or give her food (she stands).
Read aloud: "A pale young woman in torn blue silk opens her eyes. 'Took you long enough.'"
THE END. (Optional epilogue: she promises to return the Hearthstone and renew the Pact.)
```

## First-run checklist

1. Load save as host in Black. GM panel top right, title map with 4 heroes.
2. Second client picks Thief: moves to Red, gets 6 cards; button shows as taken.
3. Click each scene: table image, props, NPCs and music change; enemies are invisible to players until near.
4. On a giant: type 20 in the damage box -> bar drops. Attack button -> roll whispered to you.
5. Play a card onto the table, press REST -> card returns to hand, counters reset.
6. If things sit off the art or the kits overlap it: LAYOUT in build.py; health bars: UI_POS in npc.lua.

Updates: Holst.json is only a loader. It downloads game.json + controller.lua from GitHub on every load, so pushed fixes
arrive without replacing the save. Offline, a save you made yourself keeps the last version it loaded.
