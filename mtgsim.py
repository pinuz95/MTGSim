#!/usr/bin/env python3

import copy
import itertools
import random
import statistics
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
        # print("Playing {}".format(self.name))
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
    env['hand'] += env['library'][:n]
    env['library'] = env['library'][n:]
    env['cards_drawn'] += n*draw_multiplier


draw_multiplier = 1
def draw_cards_effect(n):
    def fun(env):
        draw_cards(env, n*draw_multiplier)
    return fun


def double_land(card, mana):
    if card.is_land and len(card.managen) > 0:
        mana.append(random.choice(mana))


def add_draw_spell(cost):
    def fun(env):
        draw_spell = Card(name='Draw Spell', cost=[1]*cost, survival_chance=0,
                          play_effects=[draw_cards_effect(1)])
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
                'Exploration': Card(name='Exploration', cost=[1, G],
                                    survival_chance=0.95,
                                    turn_effects=[increase_land_plays(1)]),
                'Ghirapur Orrery': Card(name='Ghirapur Orrery', cost=[1, 1, 1, 1],
                                        survival_chance=0.90,
                                        turn_effects=[increase_land_plays(1)]),
                'Budoka Gardener': Card(name='Budoka Gardener', cost=[G],
                                        survival_chance=0.85,
                                        turn_effects=[increase_land_plays(1)]),
                'Vernal Bloom': Card(name='Vernal Bloom', cost=[G, 1, 1, 1],
                                     survival_chance=0.90,
                                     mana_effects=[increase_from_forests]),
                'Oracle of Mul Daya': Card(name='Oracle of Mul Daya',
                                           cost=[G, 1, 1, 1],
                                           survival_chance=0.75,
                                           turn_effects=[draw_land_if_top,
                                                         increase_land_plays(1)]), # noqa
                'Rites of Flourishing': Card(name='Rites of Flourishing',
                                           cost=[G, 1, 1],
                                           survival_chance=0.95,
                                           turn_effects=[draw_cards_effect(1),
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
                'Elvish Mystic':  Card(name='Elvish Mystic', cost=[G],
                                       managen=[G], delay=1,
                                       survival_chance=0.8),
                'Boreal Druid':  Card(name='Boreal Druid', cost=[G],
                                        managen=[C], delay=1,
                                        survival_chance=0.8),
                'Nissa, Worldwaker': Card(name='Nissa, Worldwaker',
                                          cost=[1, 1, 1, G, G],
                                          managen=[G, G, G, G],
                                          survival_chance=0.67),
                "Diviner's Wand": Card(name="Diviner's Wand", cost=[1, 1, 1, 1, 1, 1], # noqa
                                       turn_effects=[add_draw_spell(4)]*10,
                                       survival_chance=0.85),
                "Mind's Eye": Card(name="Mind's Eye", cost=[1, 1, 1, 1, 1], # noqa
                                       turn_effects=[add_draw_spell(1)]*3,
                                       survival_chance=0.85),
                "Mikokoro, Center of the Sea": Card(name="Mikokoro, Center of the Sea", # noqa
                                                    turn_effects=[add_draw_spell(2)], # no qa
                                                    is_land=True),
                "Gaea's Touch": Card(name="Gaea's Touch", cost=[G, G],
                                     turn_effects=[increase_land_plays(1)],
                                     survival_chance=0.95),
                'Temple Bell': Card(name='Temple Bell', cost=[1, 1, 1],
                                    turn_effects=[draw_cards_effect(1)],
                                    survival_chance=0.9),
                'Howling Mine': Card(name='Howling Mine', cost=[1, 1],
                                     turn_effects=[draw_cards_effect(1)],
                                     survival_chance=0.9),
                'Font of Mythos': Card(name='Font of Mythos', cost=[1, 1, 1, 1],
                                     turn_effects=[draw_cards_effect(2)],
                                     survival_chance=0.9),
                'Gauntlet of Power': Card(name='Gauntlet of Power',
                                          cost=[1, 1, 1, 1, 1],
                                          survival_chance=0.8,
                                          mana_effects=[double_land]),
                'Mana Reflection': Card(name='Mana Reflection',
                                        cost=[1, 1, 1, 1, G, G],
                                        survival_chance=0.7,
                                        mana_effects=[double_gen]),
                'Caged Sun': Card(name='Caged Sun',
                                  cost=[1, 1, 1, 1, 1, 1],
                                  survival_chance=0.8,
                                          mana_effects=[double_land]),
                'Exploration': Card(name='Explore', cost=[1, G],
                                    survival_chance=0,
                                    play_effects=[draw_cards_effect(1),
                                                  increase_land_plays(1)]),
                'Elemental Bond': Card(name='Elemental Bond', cost=[1, 1, G],
                                    turn_effects=[draw_cards_effect(1)],
                                    survival_chance=0.9),
                'Recycling': Card(name='Recycling', cost=[1, 1, 1, 1, G, G],
                                  survival_chance=0,
                                  play_effects=[recycle_effect]),
                'Nissa, Vital Force': Card(name='Nissa, Vital Force',
                                           cost=[1, 1, 1, G, G],
                                           play_effects=[landfall_draw],
                                           survival_chance=0),
                'Horn of Greed': Card(name='Horn of Greed',
                                      cost=[1, 1, 1, G, G],
                                      play_effects=[landfall_draw],
                                      survival_chance=0),
                'Lotus Cobra': Card(name='Lotus Cobra', cost=[1, G],
                                    play_effects=[landfall_mana],
                                    survival_chance=0),
                'Arbor Elf': Card(name='Arbor Elf', cost=[G],
                                  turn_effects=[untap_forest],
                                  survival_chance=0.8),
                'Patron of the Orochi': Card(name='Patron of the Orochi',
                                             cost=[1, 1, 1, 1, 1, 1, G, G],
                                             survival_chance=0.7,
                                             turn_effects=[untap_all_forests]),
                'Quirion Ranger': Card(name='Quirion Ranger', cost=[G],
                                        turn_effects=[bounce_forest],
                                        survival_chance=0.8),
                'Zendikar Resurgent': Card(name='Zendikar Resurgent',
                                           cost=[1, 1, 1, 1, 1, G, G],
                                           survival_chance=0.9,
                                           turn_effects=[draw_cards_effect(2)],
                                           mana_effects=[double_land]),
                'Llanowar Druid': Card(name='Llanowar Druid', cost=[1, G],
                                       survival_chance=0.9,
                                       turn_effects=[untap_all_forests,
                                                     kill_card('Llanowar Druid')]),
                "Alhammarret's Archive": Card(name="Alhammarret's Archive",
                                              cost=[1, 1, 1, 1, 1],
                                              turn_effects=[alhammarret_effect],
                                              survival_chance=0.8),
                # Filler Cards
                "Concordant Crossroads": Card(name="Concordant Crossroads",
                                              cost=[G],
                                              survival_chance=0),
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
    value = 0
    for x in hand:
        value += 4*len(x.managen) \
        + 3*len(x.turn_effects) \
        + 4*len(x.mana_effects) \
        + 2*len(x.play_effects) \
        - len(x.cost)
    return value < 64*hand/7
    lands = 0
    lands_needed = [0, 0, 1, 1, 2, 2, 3, 3, 3]
    for card in hand:
        if len(card.managen) > 0:
            lands += 1
        if card.name == "Recycling":
            return False
    return lands <= lands_needed[len(hand)]


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
            card_name = ' '.join(parts)
            card = cards.get(card_name, FillerCard(name='Filler'))
            if card.name == 'Filler' and quantity == '1':
                print(line)
            card.name = card_name
            for i in range(int(quantity)):
                library.append(copy.deepcopy(card))

    num_iterations = 5000
    num_turns = 10
    generated_mana = []
    for i in range(num_turns):
        generated_mana.append(list(itertools.repeat(0, num_iterations)))
    excess_mana = list(itertools.repeat(0.0, num_turns))
    cards_drawn = list(itertools.repeat(0, num_iterations))
    card_played = {}
    for card in library:
        card_played[card.name] = 0
    card_played[commander.name] = 0
    card_played['Draw Spell'] = 0
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
                'cards_drawn': 0
              }
        
        draw_cards(env, 7)
        saved_cards = []
        cards_to_draw = 7
        while should_mulligan(env['hand']) and cards_to_draw > 0:
            average_mulligans += 1/num_iterations
            saved_cards += env['hand']
            env['hand'] = []
            env['cards_drawn'] = 0
            draw_cards(env, cards_to_draw)
            cards_to_draw -= 1
        env['library'] += saved_cards
        random.shuffle(env['library'])
        env['hand'].append(copy.deepcopy(commander))
        # print(', '.join(['{}']*len(env['hand'])).format(*env['hand']))
        

        for turn in range(num_turns):
            if len(env['library']) == 0:
                break
            draw_multiplier = 1
            mana_generated = 0
            # print('\n{}'.format(turn))
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
                for card in sorted(playable, key=lambda x: (2*len(x.managen) \
                                                            + 3*len(x.turn_effects) \
                                                            + 4*len(x.mana_effects) \
                                                            + 2*len(x.play_effects))):
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
                        mana_generated += len(env['mana_pool']) - cache_mana
                        env['played_cards'].append(card)
                        env['hand'].remove(card)

            excess_mana[turn] += len(env['mana_pool'])/num_iterations
            generated_mana[turn][iteration] = mana_generated
            max_mana = max(max_mana, mana_generated)

            dead_cards = []
            for card in env['played_cards']:
                if not card.survives_turn(env):
                    dead_cards.append(card)
            for card in dead_cards:
                env['played_cards'].remove(card)
                if card.is_commander:
                    card.cost += [1, 1]
                    env['hand'].append(card)

        cards_drawn[iteration] = env['cards_drawn']
    
    for i in range(len(generated_mana)):
        try:
            while True:
                generated_mana[i].remove(0)
        except:
            pass

    for i, mana in enumerate(generated_mana):
        print('Turn {}: {:.2f} median, {:.2f} mean, and {:.2f} stddev with {:.2f} mean excess'.format(i+1, statistics.median(mana), statistics.mean(mana), statistics.pstdev(mana), excess_mana[i]))
    print('Max: {:.2f}'.format(max_mana))
    print('\n{:.2f} median cards drawn, {:.2f} mean, and {:.2f} stddev'.format(statistics.median(cards_drawn), statistics.mean(cards_drawn), statistics.pstdev(cards_drawn)))
    print('{:.2f} mulligans per game\n'.format(average_mulligans))
    for card, val in sorted(card_played.items(), key=lambda x: x[1]):
        print('{} was played {} {:.2f} times per game'.format(card, ' '*(40-len(card)), val))


if __name__ == "__main__":
    main(sys.argv)
