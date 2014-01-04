# coding: utf-8

from rels import Column
from rels.django import DjangoEnum


class ACTOR_TYPE(DjangoEnum):
    records = (('PERSON', 0, u'житель'),
                ('PLACE', 1, u'место'),
                ('MONEY_SPENDING', 2, u'трата денег'))


class DONOTHING_TYPE(DjangoEnum):
    duration = Column(unique=False)
    messages_probability = Column(unique=False)

    records = (('DRUNK_SONG', 'drunk_song', u'пьяная песня', 6, 0.3),
                ('STAGGER_STREETS', 'stagger_streets', u'шляться по улицам', 10, 0.3),
                ('CHATTING', 'chatting', u'общение с друзьями',  5, 0.3),
                ('SEARCH_OLD_FRIENDS', 'search_old_friends', u'поиск старых друзей', 7, 0.3),
                ('REMEMBER_NAMES', 'remember_names', u'вспоминание имён', 3, 0.3),
                ('SPEAK_WITH_GURU', 'speak_with_guru', u'общение с гуру', 5, 0.1),
                ('STAGGER_HOLY_STREETS', 'stagger_holy_streets', u'бродить по святым улицам', 5, 0.1) )
