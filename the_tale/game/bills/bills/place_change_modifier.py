# coding: utf-8

from django.forms import ValidationError

from utg import words as utg_words

from dext.forms import fields

from the_tale.game.bills import relations
from the_tale.game.bills.forms import BaseUserForm, BaseModeratorForm
from the_tale.game.bills.bills.base_bill import BaseBill

from the_tale.game.map.places.storage import places_storage
from the_tale.game.map.places.modifiers import MODIFIERS
from the_tale.game.map.places.relations import CITY_MODIFIERS


class UserForm(BaseUserForm):

    place = fields.ChoiceField(label=u'Город')
    new_modifier = fields.ChoiceField(label=u'Новая специализация')

    def __init__(self, *args, **kwargs):
        super(UserForm, self).__init__(*args, **kwargs)
        self.fields['place'].choices = places_storage.get_choices()
        self.fields['new_modifier'].choices = sorted(CITY_MODIFIERS.choices(), key=lambda m: m[1])

    def clean_new_modifier(self):
        data = self.cleaned_data['new_modifier']
        return CITY_MODIFIERS.get_from_name(data)

    def clean(self):
        cleaned_data = super(UserForm, self).clean()

        place = places_storage.get(int(cleaned_data['place']))
        modifier = MODIFIERS[cleaned_data['new_modifier']](place)

        if not modifier.can_be_choosen:
            raise ValidationError(u'В данный момент город "%s" нельзя преобразовать в "%s".' % (place.name, modifier.NAME))

        return cleaned_data


class ModeratorForm(BaseModeratorForm):
    pass


class PlaceModifier(BaseBill):

    type = relations.BILL_TYPE.PLACE_MODIFIER

    UserForm = UserForm
    ModeratorForm = ModeratorForm

    USER_FORM_TEMPLATE = 'bills/bills/place_change_modifier_user_form.html'
    MODERATOR_FORM_TEMPLATE = 'bills/bills/place_change_modifier_moderator_form.html'
    SHOW_TEMPLATE = 'bills/bills/place_change_modifier_show.html'

    CAPTION = u'Изменение специализации города'
    DESCRIPTION = u'Изменяет специализацию города. Изменить специализацию можно только на одну из доступных для этого города. Посмотреть доступные варианты можно в диалоге информации о городе на странице игры.'

    def __init__(self, place_id=None, modifier_id=None, modifier_name=None, old_modifier_name=None, old_name_forms=None):
        super(PlaceModifier, self).__init__()
        self.place_id = place_id
        self.modifier_id = modifier_id
        self.modifier_name = modifier_name
        self.old_name_forms = old_name_forms
        self.old_modifier_name = old_modifier_name

        if self.old_name_forms is None and self.place_id is not None:
            self.old_name_forms = self.place.utg_name

    @property
    def place(self): return places_storage[self.place_id]

    @property
    def actors(self): return [self.place]

    @property
    def user_form_initials(self):
        return {'place': self.place_id,
                'new_modifier': self.modifier_id.value}

    @property
    def place_name_changed(self):
        return self.old_name != self.place.name

    @property
    def old_name(self): return self.old_name_forms.normal_form()

    def initialize_with_user_data(self, user_form):
        self.place_id = int(user_form.c.place)
        self.modifier_id = user_form.c.new_modifier
        self.modifier_name = self.modifier_id.text
        self.old_name_forms = self.place.utg_name
        self.old_modifier_name = self.place.modifier.NAME if self.place.modifier else None

    def apply(self, bill=None):
        self.place.modifier = self.modifier_id
        self.place.save()

    def serialize(self):
        return {'type': self.type.name.lower(),
                'modifier_id': self.modifier_id.value,
                'modifier_name': self.modifier_name,
                'place_id': self.place_id,
                'old_name_forms': self.old_name_forms.serialize(),
                'old_modifier_name': self.old_modifier_name if self.old_modifier_name else None}

    @classmethod
    def deserialize(cls, data):
        obj = cls()
        obj.modifier_id = CITY_MODIFIERS(data['modifier_id'])
        obj.modifier_name = data['modifier_name']
        obj.place_id = data['place_id']
        obj.old_name_forms = utg_words.Word.deserialize(data['old_name_forms'])
        obj.old_modifier_name = data.get('old_modifier_name')

        return obj
