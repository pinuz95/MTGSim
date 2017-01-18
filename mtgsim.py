#!/usr/bin/env python3
import copy
import functools
import random
import statistics
import sys
import traceback

from collections import defaultdict, Counter


@functools.lru_cache(maxsize=64)
def mana_ordering(m):
    mana_order = {1: 0, 'C': 1, 'W': 2, 'U': 3, 'B': 4, 'G': 5, 'R': 6}
    try:
        return mana_order[m]
    except:
        return len(m) + 5


def order_mana(m):
    mana_pool = Counter(m)
    result = []
    for key, val in sorted(mana_pool.items(),
                           key=lambda x: (mana_ordering(x[0]), -x[1])):
        result += [key] * val
    return result


def can_pay(mana, cost):
    if cost == 1:
        return True
    if mana == cost:
        return True
    if isinstance(mana, tuple):
        if cost in mana:
            return True
    if isinstance(cost, tuple):
        if mana in cost:
            return True
        if isinstance(mana, tuple):
            for nmana in mana:
                for ncost in cost:
                    if can_pay(nmana, ncost):
                        return True
    return False


class Card:
    def __init__(self, name="Blank Name", cost=[], managen=(), delay=0,
                 mana_effects=[], is_land=False, survival_chance=1.0,
                 turn_effects=[], play_effects=[]):
        self.name = name
        self.cost = cost
        self.managen = managen
        self.delay = delay
        self.mana_effects = mana_effects
        self.turn_effects = turn_effects
        self.play_effects = play_effects
        self.is_land = is_land
        self.survival_chance = survival_chance
        self.is_commander = False

    def can_play(self, env):
        if self.is_land:
            return env['land_plays'] > 0
        else:
            remaining_mana = order_mana(env['mana_pool'])
            payable = True
            for cost in self.cost:
                for mana in remaining_mana:
                    if can_pay(mana, cost):
                        to_remove = mana
                        break
                else:
                    payable = False
                    break
                remaining_mana.remove(to_remove)
            return payable

    def play(self, env, free=False):
        if not free:
            if self.is_land:
                env['land_plays'] -= 1
            else:
                env['mana_pool'].sort(key=mana_ordering)
                payed = 0
                for cost in self.cost:
                    for mana in env['mana_pool']:
                        if can_pay(mana, cost):
                            env['mana_pool'].remove(mana)
                            payed += 1
                            break
                    else:
                        if payed < len(self.cost):
                            print("Failed to pay {}, with {}".format(self.cost, env['mana_pool']))
                            raise ValueError("Couldn't play the card")
        if env['example']:
            print("Playing {}".format(self.name))
        for effect in self.play_effects:
            effect(env)
        env['cards_played'].append((self.name, env['turn']))

    def generate_mana(self, env):
        if self.delay > 0:
            self.delay -= 1
            if env['use_delay']:
                return ()
        mana_generated = copy.copy(self.managen)
        for card in env['played_cards']:
            for effect in card.mana_effects:
                effect(self, mana_generated)
        # print('{} generated {}'.format(self.name, mana_generated))
        env['mana_pool'] += mana_generated
        env['mana_generated'] += len(mana_generated)
        return mana_generated

    def survives_turn(self, env):
        return self.survival_chance != 0
        return random.random() < self.survival_chance

    def __str__(self):
        return self.name


class FillerCard(Card):
    def can_play(self, env):
        return False


def increase_land_plays(n):
    def fun(env):
        env['land_plays'] += n
    return fun


def increase_from_forests(card, mana):
    if card.name == 'Forest':
        mana += ('G',)


def draw_land_if_top(env):
    while len(env['library']) > 0 and env['library'][0].is_land:
        draw_cards(env, 1)


def draw_cards(env, n):
    to_draw = env['library'][:n]
    env['hand'] += to_draw
    env['library'] = env['library'][n:]
    env['cards_drawn'] += [(card.name, env['turn']) for card in to_draw]
    if env['example']:
        print('Drawing', ', '.join(['{}'] * len(to_draw)).format(*to_draw))


draw_multiplier = 1


def draw_cards_effect(n):
    def fun(env):
        draw_cards(env, n * draw_multiplier)
    return fun


def double_land(card, mana):
    if card.is_land and len(card.managen) > 0:
        mana += (random.choice(mana),)


def add_effect_spell(cost, effect, name=None, repeatable=False):
    if name is None:
        name = '{} Spell'.format(effect.__name__)
    if isinstance(cost, int):
        cost = [1] * cost

    def fun(env):
        effect_spell = Card(name=name, cost=cost, survival_chance=0,
                            play_effects=[effect])
        if repeatable:
            effect_spell.play_effects.append(fun)
        env['hand'].append(effect_spell)
    return fun


def double_gen(card, mana):
    mana += mana


def recycle_effect(env):
    for card in env['hand']:
        if card.name != "Recycling":
            card.play_effects.append(draw_cards_effect(1))
    for card in env['library']:
        card.play_effects.append(draw_cards_effect(1))


def add_mana(mana):
    def fun(env):
        env['mana_pool'].append(mana)
        env['mana_generated'] += len(mana)
    return fun


def add_play_effect(filter_func, effect):
    def fun(env):
        for card in env['hand']:
            if filter_func(card):
                card.play_effects.append(effect)
        for card in env['library']:
            if filter_func(card):
                card.play_effects.append(effect)
    return fun


def untap_forest(env):
    for card in env['played_cards']:
        if card.name == 'Forest':
            card.generate_mana(env)
            break


def untap_all_forests(env):
    for card in env['played_cards']:
        if card.name == 'Forest':
            card.generate_mana(env)


def bounce_forest(env):
    lands = 0
    for card in env['hand']:
        if card.is_land:
            lands += 1
    if lands < 3:
        for card in env['played_cards']:
            if card.name == 'Forest':
                env['played_cards'].remove(card)
                env['hand'].append(card)
                break


def kill_card(name):
    def fun(env):
        for card in env['played_cards']:
            if card.name == name:
                env['played_cards'].remove(card)
                break
    return fun


def alhammarret_effect(env):
    global draw_multiplier
    draw_multiplier = 2


def genesis_wave_effect(env):
    quantity = min(8 + len(env['mana_pool']), len(env['library']))
    env['mana_pool'] = env['mana_pool'][quantity - 8:]
    if env['example']:
        print("Genesis Wave for {} out of {}".format(quantity, len(env['library'])))
    for i in range(quantity):
        card = None
        try:
            card = env['library'].pop(0)
        except IndexError:
            break
        card.play(env, free=True)
        env['played_cards'].append(card)
        card.generate_mana(env)


def search_basic_land(env):
    # basic_lands = ["Plains", "Island", "Swamp", "Mountain", "Forest", "Wastes"]
    basic_lands = ["Plains"]
    for card in env['library']:
        if card.name in basic_lands:
            env['hand'].append(card)
            env['library'].remove(card)
            random.shuffle(env['library'])
            break


def basic_land_to_battlefield(env):
    # basic_lands = ["Plains", "Island", "Swamp", "Mountain", "Forest", "Wastes"]
    basic_lands = ["Plains"]
    for card in env['library']:
        if card.name in basic_lands:
            card.play(env, free=True)
            env['library'].remove(card)
            random.shuffle(env['library'])
            break


def remove_delay(env):
    env['use_delay'] = False


def delayed_effect(effect):
    def fun(env):
        if not env['use_delay']:
            effect(env)
    return fun


def create_cards():
    W = 'W' # noqa
    U = 'U' # noqa
    B = 'B' # noqa
    R = 'R' # noqa
    G = 'G' # noqa
    C = 'C' # noqa
    Any = ('W', 'U', 'B', 'R', 'G') # noqa
    return {
                'Mana Crypt': Card(name="Mana Crypt", managen=(C, C,), # noqa
                                   survival_chance=0.85),
                'Plains': Card(name='Plains', managen=(W,), is_land=True),
                'Island': Card(name='Island', managen=(U,), is_land=True),
                'Swamp': Card(name='Swamp', managen=(B,), is_land=True),
                'Mountain': Card(name='Mountain', managen=(R,), is_land=True),
                'Forest': Card(name='Forest', managen=(G,), is_land=True),
                'Birds of Paradise': Card(cost=[G], managen=(Any,), delay=1,
                                          survival_chance=0.85),
                'Azusa, Lost but Seeking': Card(cost=[1, 1, G], survival_chance=0.75,
                                                turn_effects=[increase_land_plays(2)],
                                                play_effects=[increase_land_plays(2)]),
                'Exploration': Card(cost=[1, G], survival_chance=0.95,
                                    turn_effects=[increase_land_plays(1)],
                                    play_effects=[increase_land_plays(1)]),
                'Ghirapur Orrery': Card(cost=[1, 1, 1, 1], survival_chance=0.90,
                                        turn_effects=[increase_land_plays(1)],
                                        play_effects=[increase_land_plays(1)]),
                'Budoka Gardener': Card(cost=[1, G], survival_chance=0.85,
                                        turn_effects=[increase_land_plays(1)]),
                'Vernal Bloom': Card(cost=[G, 1, 1, 1], survival_chance=0.90,
                                     mana_effects=[increase_from_forests]),
                'Oracle of Mul Daya': Card(cost=[G, 1, 1, 1], survival_chance=0.75,
                                           turn_effects=[draw_land_if_top,
                                                         increase_land_plays(1)],
                                           play_effects=[draw_land_if_top,
                                                         increase_land_plays(1)]),
                'Rites of Flourishing': Card(cost=[G, 1, 1], survival_chance=0.95,
                                             turn_effects=[draw_cards_effect(1),
                                                           increase_land_plays(1)],
                                             play_effects=[increase_land_plays(1)]),
                'Joraga Treespeaker': Card(cost=[G], managen=(G, G,),
                                           survival_chance=0.75, delay=2),
                'Vorinclex, Voice of Hunger': Card(cost=[1, 1, 1, 1, 1, 1, G, G],
                                                   survival_chance=0.5,
                                                   mana_effects=[double_land]),
                'Llanowar Elves': Card(cost=[G], managen=(G,), delay=1, survival_chance=0.8),
                'Fyndhorn Elves': Card(cost=[G], managen=(G,), delay=1, survival_chance=0.8),
                'Elvish Mystic': Card(cost=[G], managen=(G,), delay=1, survival_chance=0.8),
                'Boreal Druid': Card(cost=[G], managen=(C,), delay=1, survival_chance=0.8),
                'Nissa, Worldwaker': Card(cost=[1, 1, 1, G, G],
                                          turn_effects=[untap_forest] * 4,
                                          play_effects=[untap_forest] * 4,
                                          survival_chance=0.67),
                "Diviner's Wand": Card(cost=[1, 1, 1, 1, 1, 1],
                                       turn_effects=[add_effect_spell(4, draw_cards_effect(1), "Draw Spell", True)],
                                       survival_chance=0.85),
                "Mind's Eye": Card(cost=[1, 1, 1, 1, 1],
                                   turn_effects=[add_effect_spell(1, draw_cards_effect(1),
                                                                  "Draw Spell")] * 3,
                                   survival_chance=0.85),
                "Mikokoro, Center of the Sea": Card(turn_effects=[add_effect_spell(3, draw_cards_effect(1),
                                                                                   "Draw Spell")],
                                                    play_effects=[add_effect_spell(3, draw_cards_effect(1),
                                                                                   "Draw Spell")],
                                                    managen=(C,), is_land=True),
                "Gaea's Touch": Card(cost=[G, G], turn_effects=[increase_land_plays(1)],
                                     survival_chance=0.95,
                                     play_effects=[increase_land_plays(1)]),
                'Temple Bell': Card(cost=[1, 1, 1], turn_effects=[draw_cards_effect(1)],
                                    survival_chance=0.9,
                                    play_effects=[draw_cards_effect(1)]),
                'Howling Mine': Card(cost=[1, 1], turn_effects=[draw_cards_effect(1)],
                                     survival_chance=0.9),
                'Font of Mythos': Card(cost=[1, 1, 1, 1], turn_effects=[draw_cards_effect(2)],
                                       survival_chance=0.9),
                'Gauntlet of Power': Card(cost=[1, 1, 1, 1, 1],
                                          survival_chance=0.8,
                                          mana_effects=[increase_from_forests]),
                'Mana Reflection': Card(cost=[1, 1, 1, 1, G, G], survival_chance=0.7,
                                        mana_effects=[double_gen]),
                'Caged Sun': Card(cost=[1, 1, 1, 1, 1, 1], survival_chance=0.8,
                                  mana_effects=[increase_from_forests]),
                'Explore': Card(cost=[1, G], survival_chance=0,
                                play_effects=[draw_cards_effect(1), increase_land_plays(1)]),
                'Elemental Bond': Card(cost=[1, 1, G], turn_effects=[draw_cards_effect(1)],
                                       survival_chance=0.9),
                'Recycling': Card(cost=[1, 1, 1, 1, G, G], survival_chance=0,
                                  play_effects=[recycle_effect]),
                'Nissa, Vital Force': Card(cost=[1, 1, 1, G, G],
                                           turn_effects=[add_play_effect(lambda x: x.is_land, draw_cards_effect(1)),
                                                         kill_card('Nissa, Vital Force')],
                                           survival_chance=0),
                'Horn of Greed': Card(cost=[1, 1, 1], play_effects=[add_play_effect(lambda x: x.is_land,
                                                                                    draw_cards_effect(1))],
                                      survival_chance=0),
                'Lotus Cobra': Card(cost=[1, G], play_effects=[add_play_effect(lambda x: x.is_land,
                                                                               add_mana((Any,)))],
                                    survival_chance=0),
                'Arbor Elf': Card(cost=[G], turn_effects=[untap_forest],
                                  survival_chance=0.8),
                'Patron of the Orochi': Card(cost=[1, 1, 1, 1, 1, 1, G, G],
                                             survival_chance=0.7,
                                             turn_effects=[untap_all_forests],
                                             play_effects=[delayed_effect(untap_all_forests)]),
                'Zendikar Resurgent': Card(cost=[1, 1, 1, 1, 1, G, G],
                                           survival_chance=0.9,
                                           turn_effects=[draw_cards_effect(2)],
                                           mana_effects=[double_land]),
                'Llanowar Druid': Card(cost=[1, G], survival_chance=0.9,
                                       turn_effects=[untap_all_forests,
                                                     kill_card('Llanowar Druid')]),
                "Alhammarret's Archive": Card(cost=[1, 1, 1, 1, 1],
                                              turn_effects=[alhammarret_effect],
                                              survival_chance=0.8),
                'Genesis Wave': Card(cost=[G, G, G, 1, 1, 1, 1, 1, 1, 1, 1],
                                     play_effects=[genesis_wave_effect],
                                     survival_chance=0),
                "Renegade Map": Card(cost=[1],
                                     turn_effects=[kill_card('Renegade Map'),
                                                   search_basic_land]),
                "Resourceful Return": Card(cost=[1, B], survival_chance=0,
                                           play_effects=[draw_cards_effect(1)]),
                "Tower of Fortunes": Card(cost=[1, 1, 1, 1], survival_chance=-.9,
                                          play_effects=[add_effect_spell(8, draw_cards_effect(4),
                                                                         "Draw Spell")],
                                          turn_effects=[add_effect_spell(8, draw_cards_effect(4),
                                                                         "Draw Spell")]),
                "Fancy Draw": Card(cost=[1, 1, U, U], survival_chance=0,
                                   play_effects=[draw_cards_effect(2)]),
                "Vision Skeins": Card(cost=[1, U], survival_chance=0,
                                   play_effects=[draw_cards_effect(2)]),
                "Simple Draw": Card(cost=[U], survival_chance=0,
                                   play_effects=[draw_cards_effect(1)]),
                "Battlefield Forge": Card(managen=((C, W, R,),), is_land=True),
                "Valakut, the Molten Pinnacle": Card(managen=(R,), delay=1, is_land=True),
                "Boros Cluestone": Card(cost=[1, 1, 1], managen=((W, R,),), survival_chance=0.85),
                "Boros Keyrune": Card(cost=[1, 1, 1], managen=((W, R,),), survival_chance=0.85),
                "Inspired Vantage": Card(managen=((W, R,),), is_land=True),  # TODO Implement fast effect
                "Sacred Foundry": Card(managen=((W, R,),), is_land=True),
                "Clifftop Retreat": Card(managen=((W, R,),), is_land=True),  # TODO Implement check effect
                "Land Tax": Card(cost=[W], turn_effects=[search_basic_land] * 2,
                                 survival_chance=0.95),
                "Command Tower": Card(managen=(Any,), is_land=True),
                "Thran Dynamo": Card(cost=[1, 1, 1, 1], managen=(C, C, C,), survival_chance=0.85),
                "Coldsteel Heart": Card(cost=[1, 1], managen=((W, R,),), delay=1),
                "Tithe": Card(cost=[W], survival_chance=0,
                              play_effects=[search_basic_land] * 2),  # TODO Make only search plains
                "Darksteel Ingot": Card(cost=[1, 1, 1], managen=(Any,)),
                "Sol Ring": Card(cost=[1], managen=(C, C,), survival_chance=0.8),
                "Oath of Lieges": Card(cost=[1, W], turn_effects=[basic_land_to_battlefield]),
                "Nykthos, Shrine to Nyx": Card(managen=(C,), is_land=True),
                "Worn Powerstone": Card(managen=(C, C,), cost=[1, 1, 1], delay=1, survival_chance=0.9),
                "Mind Stone": Card(cost=[1, 1], managen=(C,), survival_chance=0.9),
                "Hedron Archive": Card(cost=[1, 1, 1, 1], managen=(C, C,), survival_chance=0.85),
                "Chandra, Torch of Defiance": Card(cost=[1, 1, R, R], managen=(R, R,), survival_chance=0.67),
                "Drowned Catacomb": Card(managen=((U, B,),), is_land=True),
                "Sunken Ruins": Card(managen=((U, B),), is_land=True),  # TODO Needs to filter
                "Concordant Crossroads": Card(cost=[G], survival_chance=0,
                                              play_effects=[remove_delay],
                                              turn_effects=[remove_delay]),
                "Akroma's Memorial": Card(cost=[1] * 7, survival_chance=0,
                                          play_effects=[remove_delay],
                                          turn_effects=[remove_delay]),

                # Filler Cards
                'Quirion Ranger': Card(cost=[G],  # turn_effects=[bounce_forest],
                                       survival_chance=0.8),
                "Abundance": Card(cost=[1, 1, G, G], survival_chance=0),
                "Avenger of Zendikar": Card(cost=[1] * 5 + [G, G], survival_chance=0),
                "Hydra Broodmaster": Card(cost=[1] * 4 + [G, G], survival_chance=0),
                "Undergrowth Champion": Card(cost=[1, G, G], survival_chance=0),
                "Retreat to Kazandu": Card(cost=[1, 1, G], survival_chance=0),
                "Craterhoof Behemoth": Card(cost=[1] * 5 + [G] * 3, survival_chance=0),
                "Spidersilk Armor": Card(cost=[1, 1, G], survival_chance=0),
                "Beacon of Creation": Card(cost=[1, 1, 1, G], survival_chance=0),
                "Rampaging Baloths": Card(cost=[1, 1, 1, 1, G, G], survival_chance=0),
                "Jade Mage": Card(cost=[1, G], survival_chance=0),
                "Heroes Bane": Card(cost=[1, 1, 1, G, G], survival_chance=0),
                "Helix Pinnacle": Card(cost=[G], survival_chance=0),
                "Kamahl, Fist of Krosa": Card(cost=[1, 1, 1, 1, G, G], survival_chance=0),
                "Psychosis Crawler": Card(cost=[1, 1, 1, 1, 1], survival_chance=0),
                "Omnath, Locus of Mana": Card(cost=[1, 1, G], survival_chance=0),
                "Ant Queen": Card(cost=[1, 1, 1, G, G], survival_chance=0),
                "Mobile Garrison": Card(cost=[1, 1, 1], survival_chance=0),
                "Greenwheel Liberator": Card(cost=[1, G], survival_chance=0),
                "Renegade's Getaway": Card(cost=[1, 1, B], survival_chance=0),
                "Scrounging Bandar": Card(cost=[1, G], survival_chance=0),
                "Servo Schematic": Card(cost=[1, G], survival_chance=0),
                "Maulfist Squad": Card(cost=[1, 1, 1, B], survival_chance=0),
                "Lifecraft Cavalry": Card(cost=[1, 1, 1, 1, G], survival_chance=0),
                "Walking Ballista": Card(survival_chance=0),
                "Ghirapur Guide": Card(cost=[1, 1, G], survival_chance=0),
                "Aetherwind Basker": Card(cost=[1, 1, 1, 1, G, G, G], survival_chance=0),
                "Daring Demolition": Card(cost=[1, 1, B, B], survival_chance=0),
                "Implement of Ferocity": Card(cost=[1], survival_chance=0),
                "Longtusk Cub": Card(cost=[1, G], survival_chance=0),
                "Untethered Express": Card(cost=[1, 1, 1, 1], survival_chance=0),
                "Consulate Turret": Card(cost=[1, 1, 1], survival_chance=0),
                "Aether Herder": Card(cost=[1, 1, 1, G], survival_chance=0),
                "Die Young": Card(cost=[1, B], survival_chance=0),
                "Natural Obsolescence": Card(cost=[1, G], survival_chance=0),
                "Eager Construct": Card(cost=[1, 1], survival_chance=0),  # Add Scry Eventually
                "Fourth Bridge Prowler": Card(cost=[B], survival_chance=0),
                "Lifecrafter's Gift": Card(cost=[1, 1, 1, G], survival_chance=0),
                "Winding Constrictor": Card(cost=[B, G], survival_chance=0),
                "Prey Upon": Card(cost=[G], survival_chance=0),
                "Primordial Hydra": Card(cost=[1, 1, 1, 1, G, G], survival_chance=0),
                "Metallurgic Summonings": Card(cost=[1, 1, 1, U, U], survival_chance=0,
                                               turn_effects=[lambda x: None] * 10),
                "Gisela, Blade of Goldnight": Card(cost=[1, 1, 1, 1, W, W, R],
                                                   turn_effects=[lambda x: None] * 10,
                                                   survival_chance=0),
                "Keening Stone": Card(cost=[1, 1, 1, 1, 1, 1], survival_chance=0),
                "Traumatize": Card(cost=[1, 1, 1, U, U], survival_chance=0),
                "Jace, Memory Adept": Card(cost=[1, 1, 1, U, U], survival_chance=0),
                "Sphinx's Tutelage": Card(cost=[1, 1, U], survival_chance=0),
                "Mana Leak": Card(cost=[1, U], survival_chance=0),
                "Tome Scour": Card(cost=[U], survival_chance=0),
                "Mirko Vosk, Mind Drinker": Card(cost=[1, 1, 1, U, B], survival_chance=0),
                "Consuming Abberation": Card(cost=[1, 1, 1, U, B], survival_chance=0),
                "Jace's Phantasm": Card(cost=[U], survival_chance=0),
                "Hedron Crab": Card(cost=[U], survival_chance=0),
                "Mana Drain": Card(cost=[U, U], survival_chance=0),
                "Negate": Card(cost=[1, U], survival_chance=0),
                "Mind Funeral": Card(cost=[1, U, B], survival_chance=0),
                "Startled Awake": Card(cost=[1, 1, U, U], survival_chance=0)
            }


cards = create_cards()


# Lands based
def should_mulligan(hand):
    lands = 0
    #                   0  1  2  3  4  5  6  7
    lands_needed =     [0, 0, 1, 1, 2, 2, 3, 4] # noqa
    overloaded_lands = [1, 2, 3, 4, 5, 5, 5, 5] # noqa
    # overloaded_lands = [8] * 8
    for card in hand:
        if len(card.managen) > 0:
            lands += 1
        if card.name == "Recycling":
            return False
    return lands < lands_needed[len(hand)]
    # return lands < lands_needed[len(hand)] or lands >= overloaded_lands[len(hand)]


# def should_mulligan(hand):
#     mana = 0
#     lands = 0
#     mana_needed = [i - 2 for i in range(8)]
#     for card in hand:
#         if len(card.managen) > 0 and not card.is_land:
#             mana += len(card.managen)
#         if card.is_land:
#             lands += 1
#     if lands >= 3:
#         mana += lands
#     return mana < mana_needed[len(hand)]


def should_play(env):
    important_cards = ["Genesis Wave", "Recycling", "Alhammarret's Archive",
                       "Azusa, Lost but Seeking", "Patron of the Orochi"]
    filters = [
                    ( # noqa
                        lambda c: len(c.mana_effects) > 0,
                        lambda c: -len(c.mana_effects)
                    ),
                    (
                        lambda c: c.name in important_cards,
                        lambda c: important_cards.index(c.name)
                    ),
                    (
                        lambda c: len(c.managen) > 0,
                        lambda c: c.delay
                    ),
                    (
                        lambda c: len(c.play_effects) > 0 and c.name != "Draw Spell",
                        lambda c: random.random()
                    ),
                    (
                        lambda c: len(c.turn_effects) > 0,
                        lambda c: random.random()
                    ),
                    (
                        lambda c: c.name == "Draw Spell",
                        lambda c: 1
                    )
                   ] # noqa
    while True:
        playable = [card for card in env['hand'] if card.can_play(env)]
        if len(playable) == 0:
            break
        if env['example']:
            print('Playable: ', ', '.join(['{}'] * len(playable)).format(*sorted(playable,
                                                                                 key=lambda x: x.name)))
        for func, key in filters:
            choices = [card for card in playable if func(card)]
            if len(choices) > 0:
                # if env['example']:
                #     print("Using a choice function")
                yield sorted(choices, key=key)[0]
                break
        else:
            # if env['example']:
            #     print("Couldn't find anything good to play so random")
            yield random.choice(playable)


def should_discard(env, num):
    cards = sorted(env['hand'], key=lambda x: len(x.managen) +
                                              len(x.turn_effects + x.play_effects + # noqa
                                                  x.mana_effects))
    return cards[:num]


def main(argv=None):
    global draw_multiplier, cards
    if not argv:
        argv = sys.argv
    num_iterations = 500
    num_turns = 10
    example = False

    if len(argv) < 2:
        print("Need to supply a deck file")
        return
    elif len(argv) > 2:
        if argv[2] == 'example':
            num_iterations = 1
            example = True
        else:
            num_iterations = int(argv[2])
        if len(argv) > 3:
            num_turns = int(argv[3])

    library = []
    commander = None

    with open(argv[1]) as deck_file:
        for line in deck_file:
            if line.startswith('SB:'):
                trash, quantity, *parts = line.split()
                card_name = ' '.join(parts)
                commander = cards.get(card_name, FillerCard(name='Filler'))
                commander.is_commander = True
                commander.name = card_name
                continue
            quantity, *parts = line.split()
            card_name = ' '.join(parts)
            card = cards.get(card_name, FillerCard(name='Filler'))
            if isinstance(card, FillerCard):
                print(line)
            card.name = card_name
            for i in range(int(quantity)):
                library.append(copy.deepcopy(card))
    print(len(library))
    generated_mana = []
    for i in range(num_turns):
        generated_mana.append([0] * num_iterations)
    excess_mana = [0.0] * num_turns
    cards_drawn = []
    cards_played = []
    average_mulligans = 0
    max_mana = 0
    for iteration in range(num_iterations):
        env = {
                'library': copy.deepcopy(library), # noqa
                'hand': [],
                'mana_pool': [],
                'land_plays': 1,
                'played_cards': [],
                'cards_drawn': [],
                'cards_played': [],
                'turn': 1,
                'example': example,
                'mana_generated': 0,
                'use_delay': True
              }

        random.shuffle(env['library'])
        draw_cards(env, 7)
        saved_cards = []
        cards_to_draw = 6
        while should_mulligan(env['hand']) and cards_to_draw > 0:
            average_mulligans += 1 / num_iterations
            saved_cards += env['hand']
            env['hand'] = []
            env['cards_drawn'] = []
            draw_cards(env, cards_to_draw)
            cards_to_draw -= 1
        env['library'] += saved_cards
        random.shuffle(env['library'])

        if commander:
            env['hand'].append(copy.deepcopy(commander))

        for turn in range(num_turns):
            if len(env['library']) == 0:
                break
            env['turn'] = turn + 1
            draw_multiplier = 1
            env['mana_generated'] = 0
            if example:
                print('\n{}'.format(env['turn']))
            env['mana_pool'] = []
            env['land_plays'] = 1
            env['use_delay'] = True

            for card in env['played_cards']:
                for effect in card.turn_effects:
                    effect(env)

            draw_cards(env, 1)

            if example:
                print('In Play: ', ', '.join(['{}'] * len(env['played_cards'])).format(*sorted(env['played_cards'],
                                                                                               key=lambda x: x.name)))
                print('Hand: ', ', '.join(['{}'] * len(env['hand'])).format(*sorted(env['hand'],
                                                                                    key=lambda x: x.name)))

            for card in env['played_cards']:
                card.generate_mana(env)

            for card in should_play(env):
                if card not in env['hand'] or not card.can_play(env):
                    continue
                try:
                    card.play(env)
                except ValueError:
                    traceback.print_exc()
                    continue
                card.generate_mana(env)
                env['played_cards'].append(card)
                env['hand'].remove(card)

            excess_mana[turn] += len(env['mana_pool']) / num_iterations
            generated_mana[turn][iteration] = env['mana_generated']
            max_mana = max(max_mana, env['mana_generated'])

            to_remove = [card for card in env['hand'] if card.name == 'Draw Spell']
            for card in to_remove:
                env['hand'].remove(card)
            hand_len = len(env['hand'])
            if hand_len > 7:
                for card in should_discard(env, hand_len - 7):
                    try:
                        env['hand'].remove(card)
                    except ValueError:
                        print("Couldn't find card to discard")
            if env['example'] and len(to_remove) > 0:
                print('Discarding: ', ', '.join(['{}'] * len(to_remove)).format(*sorted(to_remove,
                                                                                        key=lambda x: x.name)))

            dead_cards = []
            for card in env['played_cards']:
                if not card.survives_turn(env):
                    dead_cards.append(card)
            for card in dead_cards:
                env['played_cards'].remove(card)
                if card.is_commander:
                    card.cost += [1, 1]
                    env['hand'].append(card)

        cards_drawn += env['cards_drawn']
        cards_played += env['cards_played']

    card_stats = defaultdict(lambda: [0, 0, 0, 0])
    spells_cast = [0] * num_turns
    total_spells_cast = 0
    for card, turn in cards_drawn:
        card_stats[card][0] += turn
        card_stats[card][2] += 1
    for card, turn in cards_played:
        card_stats[card][1] += turn
        card_stats[card][3] += 1
        card_obj = cards.get(card, FillerCard(name='Filler'))
        if not card_obj.is_land and card != "Draw Spell":
            spells_cast[turn - 1] += 1
            total_spells_cast += 1

    for i, mana in enumerate(generated_mana):
        print('Turn {:2.0f}: {:3.0f} median, {:3.2f} mean, and {:3.2f} stddev with {:3.2f} mean excess, and {:2.2f} spells cast'.format(i + 1, # noqa
              statistics.median(mana), statistics.mean(mana), statistics.pstdev(mana), excess_mana[i],
              spells_cast[i] / num_iterations))
    print('Max: {:.2f}'.format(max_mana))
    print('Average spells cast: {:2.2f}'.format(total_spells_cast / num_iterations))
    print('\n{:.2f} mean cards drawn'.format(len(cards_drawn) / num_iterations))
    print('{:.2f} mulligans per game\n'.format(average_mulligans))
    if not example:
        for card, val in sorted(card_stats.items(), key=lambda x: x[1][3] / max(x[1][2], 1)):
            if len(val) != 4:
                print(val)
            turn_drawn = float("inf") if val[2] == 0 else val[0] / val[2]
            turn_played = float("inf") if val[3] == 0 else val[1] / val[3]
            play_to_draw = float("inf") if val[2] == 0 else val[3] / val[2] * 100
            percent_played = min(100, 100 * val[3] / num_iterations)
            percent_drawn = min(100, 100 * val[2] / num_iterations)
            print('{} {} was drawn {:3.0f}% and played {:3.0f}% of games with play/draw ratio {:3.0f}%. On average {:1.0f} turns between drawing and playing'.format(card, # noqa
                   ' ' * (30 - len(card)), percent_drawn, percent_played, play_to_draw,
                   turn_played - turn_drawn))


if __name__ == "__main__":
    main()
