#!/usr/bin/env python3

import copy
import itertools
import random
import statistics
import sys

from collections import defaultdict


def mana_ordering(m):
    mana_order = {1: '0', 'C': 1, 'W': 2, 'U': 2, 'B': 2, 'G': 2, 'R': 2}
    if isinstance(m, list):
        return 3
    else:
        return mana_order[m]


def can_pay(mana, cost):
    if cost == 1:
        return True
    if mana == cost:
        return True
    if isinstance(mana, list):
        if cost in mana:
            return True
    if isinstance(cost, list):
        if mana in cost:
            return True
        if isinstance(mana, list):
            for nmana in mana:
                for ncost in cost:
                    if can_pay(nmana, ncost):
                        return True
    return False


class Card:
    def __init__(self, name="Blank Name", cost=[], managen=[], delay=0,
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
            remaining_mana = copy.deepcopy(env['mana_pool'])
            remaining_mana.sort(key=mana_ordering)
            payable = True
            for cost in self.cost:
                to_remove = None
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
        if not self.can_play(env):
            raise ValueError("You can't play this card")
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
        # print("Playing {}, free: {}".format(self.name, free))
        for effect in self.play_effects:
            effect(env)
        env['cards_played'].append((self.name, env['turn']))

    def generate_mana(self, env):
        if self.delay > 0:
            self.delay -= 1
            return []
        mana_generated = copy.copy(self.managen)
        for card in env['played_cards']:
            for effect in card.mana_effects:
                effect(self, mana_generated)
        # print('{} generated {}'.format(self.name, mana_generated))
        env['mana_pool'] += mana_generated
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
        mana += 'G'


def draw_land_if_top(env):
    if len(env['library']) > 0:
        if env['library'][0].is_land:
            draw_cards(env, 1)


def draw_cards(env, n):
    to_draw = env['library'][:n]
    env['hand'] += to_draw
    env['library'] = env['library'][n:]
    env['cards_drawn'] += [(card.name, env['turn']) for card in to_draw]


draw_multiplier = 1


def draw_cards_effect(n):
    def fun(env):
        draw_cards(env, n*draw_multiplier)
    return fun


def double_land(card, mana):
    if card.is_land and len(card.managen) > 0:
        mana.append(random.choice(mana))


def add_draw_spell(cost, repeatable=False):
    def fun(env):
        for card in env['hand']:
            if card.name == 'Draw Spell' and len(card.cost) == cost \
               and len(card.play_effects) == 2:
                    return

        draw_spell = Card(name='Draw Spell', cost=[1]*cost, survival_chance=0,
                          play_effects=[draw_cards_effect(1)])
        if repeatable:
            draw_spell.play_effects.append(fun)
        env['hand'].append(draw_spell)
    return fun


def double_gen(card, mana):
    mana += mana


def recycle_effect(env):
    for card in env['hand']:
        card.play_effects.append(draw_cards_effect(1))
    for card in env['library']:
        card.play_effects.append(draw_cards_effect(1))


def landfall_draw(env):
    for card in env['hand']:
        if card.is_land:
            card.play_effects.append(draw_cards_effect(1))
    for card in env['library']:
        if card.is_land:
            card.play_effects.append(draw_cards_effect(1))


def add_mana(mana):
    def fun(env):
        env['mana_pool'].append(mana)
    return fun


def landfall_mana(env):
    for card in env['hand']:
        if card.is_land:
            card.play_effects.append(add_mana(['W', 'U', 'B', 'R', 'G']))
    for card in env['library']:
        if card.is_land:
            card.play_effects.append(add_mana(['W', 'U', 'B', 'R', 'G']))


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
    draw_multiplier = 2


def genesis_wave_effect(env):
    quantity = 5 + len(env['mana_pool'])
    for i in range(quantity):
        card = None
        try:
            card = env['library'].pop(0)
        except IndexError:
            break
        card.play(env, free=True)
        env['played_cards'].append(card)
        card.generate_mana(env)


def create_cards():
    W = 'W'
    U = 'U'
    B = 'B'
    R = 'R'
    G = 'G'
    C = 'C'
    Any = ['W', 'U', 'B', 'R', 'G']
    return {
                'Mana Crypt': Card(name="Mana Crypt", managen=[C, C],
                                   survival_chance=0.85),
                'Plains': Card(name='Plains', managen=[W], is_land=True),
                'Island': Card(name='Island', managen=[U], is_land=True),
                'Swamp': Card(name='Swamp', managen=[B], is_land=True),
                'Mountain': Card(name='Mountain', managen=[R], is_land=True),
                'Forest': Card(name='Forest', managen=[G], is_land=True),
                'Birds of Paradise': Card(cost=[G], managen=[Any], delay=1,
                                          survival_chance=0.85),
                'Azusa, Lost but Seeking': Card(cost=[1, 1, G], survival_chance=0.75,
                                                turn_effects=[increase_land_plays(2)]),
                'Exploration': Card(cost=[1, G], survival_chance=0.95,
                                    turn_effects=[increase_land_plays(1)]),
                'Ghirapur Orrery': Card(cost=[1, 1, 1, 1], survival_chance=0.90,
                                        turn_effects=[increase_land_plays(1)]),
                'Budoka Gardener': Card(cost=[G], survival_chance=0.85,
                                        turn_effects=[increase_land_plays(1)]),
                'Vernal Bloom': Card(cost=[G, 1, 1, 1], survival_chance=0.90,
                                     mana_effects=[increase_from_forests]),
                'Oracle of Mul Daya': Card(cost=[G, 1, 1, 1], survival_chance=0.75,
                                           turn_effects=[draw_land_if_top,
                                                         increase_land_plays(1)]),
                'Rites of Flourishing': Card(cost=[G, 1, 1], survival_chance=0.95,
                                             turn_effects=[draw_cards_effect(1),
                                                           increase_land_plays(1)]),
                'Joraga Treespeaker': Card(cost=[G, G, 1], managen=[G, G],
                                           survival_chance=0.75, delay=1),
                'Vorinclex, Voice of Hunger': Card(cost=[1, 1, 1, 1, 1, 1, G, G],
                                                   survival_chance=0.5,
                                                   mana_effects=[double_land]),
                'Llanowar Elves':  Card(cost=[G], managen=[G], delay=1, survival_chance=0.8),
                'Fyndhorn Elves':  Card(cost=[G], managen=[G], delay=1, survival_chance=0.8),
                'Elvish Mystic':  Card(cost=[G], managen=[G], delay=1, survival_chance=0.8),
                'Boreal Druid':  Card(cost=[G], managen=[C], delay=1, survival_chance=0.8),
                'Nissa, Worldwaker': Card(cost=[1, 1, 1, G, G],
                                          turn_effects=[untap_forest]*4,
                                          survival_chance=0.67),
                "Diviner's Wand": Card(cost=[1, 1, 1, 1, 1, 1],
                                       turn_effects=[add_draw_spell(4, repeatable=True)],
                                       survival_chance=0.85),
                "Mind's Eye": Card(cost=[1, 1, 1, 1, 1], turn_effects=[add_draw_spell(1)]*3,
                                   survival_chance=0.85),
                "Mikokoro, Center of the Sea": Card(turn_effects=[add_draw_spell(3)],
                                                    managen=[C], is_land=True),
                "Gaea's Touch": Card(cost=[G, G], turn_effects=[increase_land_plays(1)],
                                     survival_chance=0.95),
                'Temple Bell': Card(cost=[1, 1, 1], turn_effects=[draw_cards_effect(1)],
                                    survival_chance=0.9),
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
                'Exploration': Card(cost=[1, G], survival_chance=0,
                                    play_effects=[draw_cards_effect(1),
                                                  increase_land_plays(1)]),
                'Elemental Bond': Card(cost=[1, 1, G], turn_effects=[draw_cards_effect(1)],
                                       survival_chance=0.9),
                'Recycling': Card(cost=[1, 1, 1, 1, G, G], survival_chance=0,
                                  play_effects=[recycle_effect]),
                'Nissa, Vital Force': Card(cost=[1, 1, 1, G, G],
                                           play_effects=[landfall_draw],
                                           survival_chance=0),
                'Horn of Greed': Card(cost=[1, 1, 1], play_effects=[landfall_draw],
                                      survival_chance=0),
                'Lotus Cobra': Card(cost=[1, G], play_effects=[landfall_mana],
                                    survival_chance=0),
                'Arbor Elf': Card(cost=[G], turn_effects=[untap_forest],
                                  survival_chance=0.8),
                'Patron of the Orochi': Card(cost=[1, 1, 1, 1, 1, 1, G, G],
                                             survival_chance=0.7,
                                             turn_effects=[untap_all_forests]),
                'Quirion Ranger': Card(cost=[G], turn_effects=[bounce_forest],
                                       survival_chance=0.8),
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
                'Genesis Wave': Card(cost=[G, G, G, 1, 1, 1, 1, 1],
                                     play_effects=[genesis_wave_effect],
                                     survival_chance=0),
                # Filler Cards
                "Concordant Crossroads": Card(cost=[G], survival_chance=0),
                "Akroma's Memorial": Card(cost=[1]*7, survival_chance=0),
                "Abundance": Card(cost=[1, 1, G, G], survival_chance=0),
                "Avenger of Zendikar": Card(cost=[1]*5 + [G, G], survival_chance=0),
                "Hydra Broodmaster": Card(cost=[1]*4 + [G, G], survival_chance=0),
                "Undergrowth Champion": Card(cost=[1, G, G], survival_chance=0),
                "Retreat to Kazandu": Card(cost=[1, 1, G], survival_chance=0),
                "Craterhoof Behemoth": Card(cost=[1]*5 + [G]*3, survival_chance=0),
                "Spidersilk Armor": Card(cost=[1, 1, G], survival_chance=0),
                "Beacon of Creation": Card(cost=[1, 1, 1, G], survival_chance=0),
                "Rampaging Baloths": Card(cost=[1, 1, 1, 1, G, G], survival_chance=0),
                "Jade Mage": Card(cost=[1, G], survival_chance=0),
                "Heroes Bane": Card(cost=[1, 1, 1, G, G], survival_chance=0),
                "Helix Pinnacle": Card(cost=[G], survival_chance=0),
                "Kamahl, Fist of Krosa": Card(cost=[1, 1, 1, 1, G, G], survival_chance=0),
                "Psychosis Crawler": Card(cost=[1, 1, 1, 1, 1], survival_chance=0),
                "Omnath, Locus of Mana": Card(cost=[1, 1, G], survival_chance=0),
                "Ant Queen": Card(cost=[1, 1, 1, G, G], survival_chance=0)
            }


def should_mulligan(hand):
    lands = 0
    lands_needed = [0, 0, 1, 1, 2, 3, 3, 4, 4]
    for card in hand:
        if len(card.managen) > 0:
            lands += 1
        if card.name == "Recycling":
            return False
    return lands < lands_needed[len(hand)]


def play_order(playable):
    playable = copy.copy(playable)
    for card in playable:
        if card.name == "Recycling":
            yield card
            playable.remove(card)
    random.shuffle(playable)
    for card in playable:
        yield card
    # for card in sorted(playable, key=lambda x: len(x.cost)):
    #     yield card


def main(argv=None):
    if not argv:
        argv = sys.argv
    num_iterations = 500
    num_turns = 10

    if len(argv) < 2:
        print("Need to supply a deck file")
        return
    elif len(argv) > 2:
        num_iterations = int(argv[2])
        if len(argv) > 3:
            num_turns = int(argv[3])

    library = []
    commander = FillerCard(name='Filler')

    with open(argv[1]) as deck_file:
        cards = create_cards()
        for line in deck_file:
            if line.startswith('SB:'):
                trash, quantity, *parts = line.split() # noqa
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

    generated_mana = []
    for i in range(num_turns):
        generated_mana.append([0]*num_iterations)
    excess_mana = [0.0]*num_turns
    cards_drawn = []
    cards_played = []
    average_mulligans = 0
    max_mana = 0
    for iteration in range(num_iterations):
        random.shuffle(library)
        env = {
                'library': copy.deepcopy(library),
                'hand': [],
                'mana_pool': [],
                'land_plays': 1,
                'played_cards': [],
                'cards_drawn': [],
                'cards_played': [],
                'turn': 1
              }

        draw_cards(env, 7)
        saved_cards = []
        cards_to_draw = 7
        while should_mulligan(env['hand']) and cards_to_draw > 0:
            average_mulligans += 1/num_iterations
            saved_cards += env['hand']
            env['hand'] = []
            env['cards_drawn'] = []
            draw_cards(env, cards_to_draw)
            cards_to_draw -= 1
        env['library'] += saved_cards
        random.shuffle(env['library'])
        env['hand'].append(copy.deepcopy(commander))
        # print(', '.join(['{}']*len(env['hand'])).format(*env['hand']))

        for turn in range(num_turns):
            if len(env['library']) == 0:
                break
            env['turn'] = turn + 1
            draw_multiplier = 1
            mana_generated = 0
            # print('\n{}'.format(turn))
            draw_cards(env, 1)
            env['mana_pool'] = []
            env['land_plays'] = 1

            to_remove = [card for card in env['hand'] if card.name == 'Draw Spell']
            for card in to_remove:
                env['hand'].remove(card)

            for card in env['played_cards']:
                # print('{} is in Play'.format(card))
                for effect in card.turn_effects:
                    effect(env)
            # print(', '.join(['{}']*len(env['hand'])).format(*env['hand']))
            for card in env['played_cards']:
                card.generate_mana(env)
            mana_generated += len(env['mana_pool'])

            # print()
            # for card in env['hand']:
            #     if card.name != 'Filler':
            #         print('{} is in hand'.format(card))
            playable = ['t']
            while len(playable) > 0:
                playable = []
                for card in env['hand']:
                    if card.can_play(env):
                        playable.append(card)
                random.shuffle(playable)
                for card in play_order(playable):
                    if card.can_play(env) and card in env['hand']:
                        try:
                            card.play(env)
                        except ValueError:
                            pass
                        cache_mana = len(env['mana_pool'])
                        card.generate_mana(env)
                        mana_generated += len(env['mana_pool']) - cache_mana
                        env['played_cards'].append(card)
                        env['hand'].remove(card)

            excess_mana[turn] += len(env['mana_pool'])/num_iterations
            generated_mana[turn][iteration] = mana_generated
            max_mana = max(max_mana, mana_generated)

            env['hand'] = env['hand'][:7]

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
    for i in range(len(generated_mana)):
        try:
            while True:
                generated_mana[i].remove(0)
        except:
            pass

    for i, mana in enumerate(generated_mana):
        print('Turn {}: {:.2f} median, {:.2f} mean, and {:.2f} stddev with {:.2f} mean excess'.format(i+1,
              statistics.median(mana), statistics.mean(mana), statistics.pstdev(mana), excess_mana[i]))
    print('Max: {:.2f}'.format(max_mana))
    print('\n{:.2f} mean cards drawn'.format(len(cards_drawn)/num_iterations))
    print('{:.2f} mulligans per game\n'.format(average_mulligans))
    card_stats = defaultdict(lambda : [0, 0, 0, 0])
    print(len(cards_drawn))
    for card, turn in cards_drawn:
        card_stats[card][0] += turn
        card_stats[card][2] += 1
    for card, turn in cards_played:
        card_stats[card][1] += turn
        card_stats[card][3] += 1
    for card, val in sorted(card_stats.items(), key=lambda x: x[1][2]):
        if len(val) != 4:
            print(val)
        turn_drawn = float("inf") if val[2] == 0 else val[0]/val[2]
        turn_played = float("inf") if val[3] == 0 else val[1]/val[3]
        print('{} {} was drawn {:2.2f} and played {:2.2f} times per game. On average drawn turn {:3.0f} and played {:3.0f}, difference {:3.0f}'.format(card,
               ' '*(30 - len(card)), val[2]/num_iterations, val[3]/num_iterations, turn_drawn, turn_played, turn_played - turn_drawn))


if __name__ == "__main__":
    main(sys.argv)
