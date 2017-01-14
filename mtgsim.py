#!/usr/bin/env python3

import copy
import itertools
import random
import sys


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
            random.shuffle(remaining_mana)
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

    def play(self, env):
        if not self.can_play(env):
            raise ValueError("You can't play this card")
        print("Playing {}".format(self.name))
        if self.is_land:
            env['land_plays'] -= 1
        else:
            random.shuffle(env['mana_pool'])
            for cost in self.cost:
                for mana in env['mana_pool']:
                    if can_pay(mana, cost):
                        env['mana_pool'].remove(mana)
                        break
        for effect in self.play_effects:
            effect(env)
        return env['mana_pool']

    def generate_mana(self, env):
        if self.delay > 0:
            self.delay -= 1
            return []
        mana_generated = self.managen
        for card in env['played_cards']:
            for effect in card.mana_effects:
                effect(self, mana_generated)
        env['mana_pool'] += mana_generated
        return mana_generated

    def survives_turn(self, env):
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
    if env['library'][0].is_land:
        draw_cards(env, 1)


def draw_cards(env, n):
    env['hand'] += env['library'][:n]
    env['library'] = env['library'][n:]
    env['cards_drawn'] += n


def draw_cards_effect(n):
    def fun(env):
        draw_cards(env, n)
    return fun


def double_land(card, mana):
    if card.is_land:
        mana.append(random.choice(mana))


def add_draw_spell(cost):
    def fun(env):
        draw_spell = Card(name='Draw Spell', cost=[1]*cost, survival_chance=0,
                          play_effects=[draw_cards_effect(1)])
        env['hand'].append(draw_spell)
    return fun


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
                'Birds of Paradise': Card(name='Birds of Paradise', cost=[G],
                                          managen=[Any], delay=1,
                                          survival_chance=0.85),
                'Azusa, Lost but Seeking': Card(name='Azusa, Lost but Seeking',
                                                cost=[1, 1, G],
                                                survival_chance=0.75,
                                                turn_effects=[increase_land_plays(2)]), # noqa
                'Exploration': Card(name='Exploration', cost=[G],
                                    survival_chance=0.95,
                                    turn_effects=[increase_land_plays(1)]),
                'Vernal Bloom': Card(name='Vernal Bloom', cost=[G, 1, 1, 1],
                                     survival_chance=0.90,
                                     mana_effects=[increase_from_forests]),
                'Oracle of Mul Daya': Card(name='Oracle of Mul Daya',
                                           cost=[G, 1, 1, 1],
                                           survival_chance=0.75,
                                           turn_effects=[draw_land_if_top,
                                                         increase_land_plays(1)]), # noqa
                'Joraga Treespeaker': Card(name='Joraga Treespeaker',
                                           cost=[G, G, 1], managen=[G, G],
                                           survival_chance=0.75,
                                           delay=1),
                'Vorinclex, Voice of Hunger': Card(name='Vorinclex, Voice of Hunger', # noqa
                                                   cost=[1, 1, 1, 1, 1, 1, G, G], # noqa
                                                   survival_chance=0.5,
                                                   mana_effects=[double_land]),
                'Llanowar Elves':  Card(name='Llanowar Elves', cost=[G],
                                        managen=[G], delay=1,
                                        survival_chance=0.8),
                'Fyndhorn Elves':  Card(name='Fyndhorn Elves', cost=[G],
                                        managen=[G], delay=1,
                                        survival_chance=0.8),
                'Nissa, Worldwaker': Card(name='Nissa, Worldwaker',
                                          cost=[1, 1, 1, G, G],
                                          managen=[G, G, G, G],
                                          survival_chance=0.67),
                "Diviner's Wand": Card(name="Diviner's Wand", cost=[1, 1, 1, 1], # noqa
                                       turn_effects=[add_draw_spell(4)]*3,
                                       survival_chance=0.85),
                "Gaea's Touch": Card(name="Gaea's Touch", cost=[G, G],
                                     turn_effects=[increase_land_plays(1)],
                                     survival_chance=0.95),
                'Temple Bell': Card(name='Temple Bell', cost=[1, 1, 1],
                                    turn_effects=[draw_cards_effect(1)],
                                    survival_chance=0.9),
                'Gauntlet of Power': Card(name='Gauntlet of Power',
                                          cost=[1, 1, 1, 1, 1],
                                          survival_chance=0.8,
                                          mana_effects=[double_land])
            }


def should_mulligan(hand):
    lands = 0
    for card in hand:
        if card.is_land:
            lands += 1
    return lands >= len(hand)/2


def main(argv=None):
    if not argv:
        argv = sys.argv
    if len(argv) < 2:
        print("Need to supply a deck file")
        return

    library = []
    commander = FillerCard(name='Filler')

    with open(argv[1]) as deck_file:
        cards = create_cards()
        for line in deck_file:
            if line.startswith('SB:'):
                trash, quantity, *parts = line.split() # noqa
                commander = cards.get(' '.join(parts),
                                      FillerCard(name='Filler'))
                commander.is_commander = True
                continue
            quantity, *parts = line.split() # noqa
            library += list(itertools.repeat(cards.get(' '.join(parts),
                                                       FillerCard(name='Filler')), # noqa
                                             int(quantity)))

    num_iterations = 1
    num_turns = 10
    generated_mana = list(itertools.repeat(0.0, num_turns))
    cards_drawn = 0
    card_played = {}
    for card in library:
        card_played[card.name] = 0
    card_played[commander.name] = 0
    card_played['Draw Spell'] = 0
    average_mulligans = 0
    for iteration in range(num_iterations):
        random.shuffle(library)
        env = {
                'library': copy.deepcopy(library),
                'hand': [],
                'mana_pool': [],
                'land_plays': 1,
                'played_cards': [],
                'cards_drawn': 0
              }
        draw_cards(env, 7)
        saved_cards = []
        cards_to_draw = 7
        while should_mulligan(env['hand']) and cards_to_draw > 0:
            average_mulligans += 1/num_iterations
            saved_cards += env['hand']
            env['hand'] = []
            draw_cards(env, cards_to_draw)
            cards_to_draw -= 1
        env['library'] += saved_cards
        random.shuffle(env['library'])

        env['hand'].append(commander)
        for turn in range(num_turns):
            print('\n{}'.format(turn))
            draw_cards(env, 1)
            env['mana_pool'] = []
            env['land_plays'] = 1
            for card in env['played_cards']:
                # print('{} is in Play'.format(card))
                for effect in card.turn_effects:
                    effect(env)
            # print(', '.join(['{}']*len(env['hand'])).format(*env['hand']))
            for card in env['played_cards']:
                card.generate_mana(env)
            generated_mana[turn] += len(env['mana_pool'])/num_iterations

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
                for card in playable:
                    if card.can_play(env):
                        for i in range(3):
                            try:
                                card.play(env)
                                card_played[card.name] += 1/num_iterations
                                break
                            except ValueError:
                                pass
                        cache_mana = len(env['mana_pool'])
                        card.generate_mana(env)
                        generated_mana[turn] += (len(env['mana_pool'])
                                                 - cache_mana)/num_iterations
                        env['played_cards'].append(card)
                        env['hand'].remove(card)

            dead_cards = []
            for card in env['played_cards']:
                if not card.survives_turn(env):
                    dead_cards.append(card)
            for card in dead_cards:
                env['played_cards'].remove(card)
                if card.is_commander:
                    card.cost += [1, 1]
                    env['hand'].append(card)

        cards_drawn += env['cards_drawn']/num_iterations

    for i, mana in enumerate(generated_mana):
        print('Turn {}: {:.2f}'.format(i+1, mana))
    print('\n{:.2f} cards drawn'.format(cards_drawn))
    print('{:.2f} mulligans per game\n'.format(average_mulligans))
    for card, val in sorted(card_played.items(), key=lambda x: x[1]):
        print('{} was played {} {:.2f} times per game'.format(card, ' '*(40-len(card)), val))


if __name__ == "__main__":
    main(sys.argv)
