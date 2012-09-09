# coding: utf-8

from game.quests.quests_builders.help import Help
from game.quests.quests_builders.help_friend import HelpFriend
from game.quests.quests_builders.delivery import Delivery
from game.quests.quests_builders.caravan import Caravan
from game.quests.quests_builders.spying import Spying
from game.quests.quests_builders.not_my_work import NotMyWork
from game.quests.quests_builders.hunt import Hunt
from game.quests.quests_builders.hometown import Hometown

QUESTS = [Help, HelpFriend, Delivery, Caravan, Spying, NotMyWork, Hunt, Hometown]
QUESTS_TYPES = [quest.type() for quest in QUESTS]

# TODO: WHY no all quest added here?
__all__ = ['QUESTS']
