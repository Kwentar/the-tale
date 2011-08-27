# -*- coding: utf-8 -*-
from django_next.utils.decorators import nested_commit_on_success

from game.journal_messages.prototypes import MessagesLogPrototype, get_messages_log_by_model

from game.map.places.prototypes import HeroPositionPrototype, PlacePrototype

from ..artifacts.effects import RAW_EFFECT_TYPE

from .models import Hero, HeroQuest
from . import game_info

attrs = game_info.attributes

def get_hero_by_id(model_id):
    hero = Hero.objects.get(id=model_id)
    return HeroPrototype(model=hero)

def get_hero_by_model(model):
    return HeroPrototype(model=model)

def get_heroes_by_query(query):
    return [ get_hero_by_model(hero) for hero in list(query)]


class HeroPrototype(object):

    def __init__(self, model=None):
        self.model = model

    @property
    def is_npc(self): return self.model.npc

    def get_is_alive(self): return self.model.alive
    def set_is_alive(self, value): self.model.alive = value
    is_alive = property(get_is_alive, set_is_alive)

    @property
    def id(self): return self.model.id

    @property
    def angel_id(self): return self.model.angel_id

    ###########################################
    # Base attributes
    ###########################################

    @property
    def first(self): return self.model.first

    @property
    def name(self): return self.model.name

    @property
    def wisdom(self): return self.model.wisdom

    def get_health(self): return self.model.health
    def set_health(self, value): self.model.health = value
    health = property(get_health, set_health)

    def get_money(self): return self.model.money
    def set_money(self, value): self.model.money = value
    money = property(get_money, set_money)

    @property
    def bag(self):
        if not hasattr(self, '_bag'):
            from .bag import Bag
            self._bag = Bag()
            self._bag.load_from_json(self.model.bag)
        return self._bag

    def put_loot(self, artifact):
        max_bag_size = self.max_bag_size
        quest_items_count, loot_items_count = self.bag.occupation
        if artifact.quest or loot_items_count < max_bag_size:
            self.bag.put_artifact(artifact)
            self.create_tmp_log_message('hero received "%s"' % artifact.name)
        else:
            self.create_tmp_log_message('hero can not put "%s" - the bag is full' % artifact.name)

    @property
    def equipment(self):
        if not hasattr(self, '_equipment'):
            from .bag import Equipment
            self._equipment = Equipment()
            self._equipment.load_from_json(self.model.equipment)
        return self._equipment


    ###########################################
    # Primary attributes
    ###########################################

    @property
    def intellect(self): return self.model.intellect
    @property
    def constitution(self): return self.model.constitution
    @property
    def reflexes(self): return self.model.reflexes
    @property
    def charisma(self): return self.model.charisma
    @property
    def chaoticity(self): return self.model.chaoticity

    ###########################################
    # accumulated attributes
    ###########################################

    ###########################################
    # Secondary attributes
    ###########################################

    @property
    def move_speed(self): return game_info.attributes.secondary.move_speed.get(self)

    @property
    def battle_speed(self): 
        speed = game_info.attributes.secondary.battle_speed.get(self)
        speed += self.equipment.get_raw_effect(RAW_EFFECT_TYPE.BATTLE_SPEED)        
        return speed

    @property
    def max_health(self): return game_info.attributes.secondary.max_health.get(self)

    @property
    def min_damage(self): 
        damage = game_info.attributes.secondary.min_damage.get(self)
        damage += self.equipment.get_raw_effect(RAW_EFFECT_TYPE.MIN_DAMAGE)
        return damage

    @property
    def max_damage(self): 
        damage = game_info.attributes.secondary.max_damage.get(self)
        damage += self.equipment.get_raw_effect(RAW_EFFECT_TYPE.MAX_DAMAGE)
        return damage

    @property
    def max_bag_size(self): return game_info.attributes.secondary.max_bag_size.get(self)

    ###########################################
    # Needs attributes
    ###########################################

    @property
    def need_rest_in_town(self): return game_info.needs.InTown.rest.check(self)

    @property
    def need_trade_in_town(self): return game_info.needs.InTown.trade.check(self)

    @property
    def need_equipping_in_town(self): return game_info.needs.InTown.equipping.check(self)

    ###########################################
    # quests
    ###########################################

    @property
    def quests(self):
        from game.quests.prototypes import QUESTS_TYPES
        if not hasattr(self, '_quests'):
            self._quests = []
            hero_quests = HeroQuest.objects.select_related('quest').filter(hero=self.model).order_by('created_at')
            quests = [hero_quest.quest for hero_quest in hero_quests]
            for quest in quests:
                quest_objects = QUESTS_TYPES[quest.type](base_model=quest)
                self._quests.append(quest_objects)
        return self._quests
    

    ###########################################
    # actions
    ###########################################p

    def get_actions(self):
        from game.actions.models import Action
        from game.actions.prototypes import ACTION_TYPES

        if not hasattr(self, '_actions'):
            self._actions = []
            actions = list(Action.objects.filter(hero=self.model).order_by('order'))
            for action in actions:
                action_object = ACTION_TYPES[action.type](model=action)
                self._actions.append(action_object)

        return self._actions

    @property
    def position(self):
        if not hasattr(self, '_position'):
            self._position = HeroPositionPrototype(model=self.model.position)
        return self._position


    def create_tmp_log_message(self, text):
        messages_log = self.get_messages_log()
        messages_log.push_message('TMP', 'TMP: %s' % text)
        messages_log.save()


    ###########################################
    # Object operations
    ###########################################

    def remove(self): return self.model.delete()
    def save(self): 
        self.model.bag = self.bag.save_to_json()
        self.model.equipment = self.equipment.save_to_json()
        self.model.save()

    def get_messages_log(self):
        return get_messages_log_by_model(model=self.model.messages_log)

    def ui_info(self, ignore_actions=False, ignore_quests=False):

        quest_items_count, loot_items_count = self.bag.occupation

        return {'id': self.id,
                'npc': self.is_npc,
                'angel': self.angel_id,
                'actions': [ action.ui_info() for action in self.get_actions() ] if not ignore_actions else [],
                'quests': [quest.ui_info() for quest in self.quests] if not ignore_quests else [], 
                'messages': self.get_messages_log().messages if not self.is_npc else None,
                'position': self.position.ui_info() if not self.is_npc else None,
                'alive': self.is_alive,
                'bag': self.bag.ui_info(),
                'equipment': self.equipment.ui_info(),
                'money': self.money, 
                'base': { 'name': self.name,
                          'first': self.first,
                          'wisdom': self.wisdom,
                          'health': self.health,
                          'max_health': self.max_health},
                'primary': { 'intellect': self.intellect,
                             'constitution': self.constitution,
                             'reflexes': self.reflexes,
                             'charisma': self.charisma,
                             'chaoticity': self.chaoticity },
                'secondary': { 'min_damage': self.min_damage,
                               'max_damage': self.max_damage,
                               'move_speed': round(self.move_speed, 2),
                               'battle_speed': round(self.battle_speed, 2),
                               'max_bag_size': self.max_bag_size,
                               'loot_items_count': loot_items_count},
                'accumulated': { }
                }


    @classmethod
    @nested_commit_on_success
    def create(cls, angel, name, first, intellect, constitution, reflexes, chaoticity, charisma, npc=False):
        from game.actions.prototypes import ActionIdlenessPrototype

        hero = Hero.objects.create(angel=angel.model if not npc else None,
                                   npc=npc,

                                   name=name,
                                   first=first,

                                   health=attrs.secondary.max_health.from_attrs(constitution, 
                                                                                attrs.base.wisdom.initial),
                                   
                                   wisdom=attrs.base.wisdom.initial,

                                   intellect=intellect,
                                   constitution=constitution,
                                   reflexes=reflexes,
                                   chaoticity=chaoticity)

        hero = cls(model=hero)

        if npc:
            return hero

        ActionIdlenessPrototype.create(hero=hero)

        MessagesLogPrototype.create(hero)

        start_place = PlacePrototype.random_place()

        HeroPositionPrototype.create(hero=hero, place=start_place)

        return hero

    ###########################################
    # Game operations
    ###########################################

    def kill(self, current_action=None):
        self.is_alive = False

        if self.is_npc:
            self.health = 0
            return
        
        self.health = 1
        self.position.set_place(PlacePrototype.random_place())
        self.position.save()
        
        for action in reversed(self.get_actions()):
            if action.id == current_action.id:
                if current_action.on_die():
                    break
            elif action.on_die():
                action.save()
                break

    def resurrent(self):
        self.health = self.max_health
        self.is_alive = True

    ###########################################
    # Next turn operations
    ###########################################

    def next_turn_pre_update(self, turn):
        if not self.is_npc:
            messages_log = self.get_messages_log()        
            messages_log.clear_messages()
            messages_log.save()

    def next_turn_post_update(self, turn):
        pass
