
from django.db import models

class Action(models.Model):

    class STATE:
        UNINITIALIZED = 'uninitialized'
        PROCESSED = 'processed'

    created_at = models.DateTimeField(auto_now_add=True)

    type = models.CharField(max_length=150, null=False)

    hero = models.ForeignKey('heroes.Hero', related_name='+')

    order = models.IntegerField()

    percents = models.FloatField(null=False)

    state = models.CharField(max_length=50, null=False, default=STATE.UNINITIALIZED)

    entropy = models.IntegerField(null=False, default=0)


class ActionIdleness(models.Model):

    class STATE(Action.STATE):
        pass
    
    base_action = models.OneToOneField(Action, related_name='action_idleness')

    entropy_action = models.ForeignKey(Action, related_name='+', default=None, null=True, on_delete=models.SET_NULL)


class ActionQuest(models.Model):

    class STATE(Action.STATE):
        PROCESSING = 'processing'
    
    base_action = models.OneToOneField(Action, related_name='action_quest')

    quest = models.ForeignKey('quests.Quest', related_name='+', default=None, null=True)

    quest_action = models.OneToOneField(Action, related_name='+', null=True, default=None, on_delete=models.SET_NULL)


class ActionMoveTo(models.Model):

    class STATE(Action.STATE):
        CHOOSE_ROAD = 'choose_road'
        MOVING = 'moving'
        WALKING_IN_CITY = 'walking_in_city'
    
    base_action = models.OneToOneField(Action, related_name='action_move_to')

    destination = models.ForeignKey('places.Place', related_name='+')

    road = models.ForeignKey('roads.Road', related_name='+', null=True, default=None, on_delete=models.SET_NULL)

    entropy_action = models.ForeignKey(Action, related_name='+', default=None, null=True, on_delete=models.SET_NULL)


class ActionBattlePvE_1x1(models.Model):

    class STATE(Action.STATE):
        BATTLE_RUNNING = 'battle_running'

    base_action = models.OneToOneField(Action, related_name='action_battle_pve_1x1')

    npc = models.ForeignKey('heroes.Hero', related_name='+')

    hero_initiative = models.FloatField(null=False, default=0.0)
    npc_initiative = models.FloatField(null=False, default=0.0)


class ActionResurrect(models.Model):

    class STATE(Action.STATE):
        RESURRECT = 'resurrect'

    base_action = models.OneToOneField(Action, related_name='action_resurrect')


class ActionInCity(models.Model):

    class STATE(Action.STATE):
        WALKING = 'walking'
        TRADING = 'trading'
        RESTING = 'resting'
        EQUIPPING = 'equipping'

    traded = models.BooleanField(null=False, default=False)
    rested = models.BooleanField(null=False, default=False)
    equipped = models.BooleanField(null=False, default=False)

    base_action = models.OneToOneField(Action, related_name='action_in_city')

    city = models.ForeignKey('places.Place', related_name='+')
    

