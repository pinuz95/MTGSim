A program to simulate a deck's mana curve and help optimize. Just needs the cards relevant to the mana curve to be implemented with effects, everything else can be written just as a card with a cost. Cards relevant to mana curve are usually lands, mana rocks, land search, and draw.

The only thing you should need to do is implement the cards with effects mostly already written. Then you can change should\_mulligan, should\_play, and should\_discard to match your strategy.

Can be run with `./mtgsim.py <deck file> <iterations> <num_turns>`
