# coding: utf-8

from dext.common.utils.urls import url

from the_tale.common.utils import testcase
from the_tale.common.postponed_tasks import PostponedTaskPrototype

from the_tale.accounts.logic import register_user
from the_tale.accounts.prototypes import AccountPrototype

from the_tale.game.logic import create_test_map
from the_tale.game import names

from the_tale.game.logic_storage import LogicStorage

from the_tale.game.cards import relations
from the_tale.game.cards.prototypes import CARDS
from the_tale.game.cards import objects

from the_tale.game.map.places.prototypes import BuildingPrototype


class CardsRequestsTestsBase(testcase.TestCase):

    def setUp(self):
        super(CardsRequestsTestsBase, self).setUp()
        self.place_1, self.place_2, self.place_3 = create_test_map()

        result, account_id, bundle_id = register_user('test_user_1', 'test_user_1@test.com', '111111')

        self.account = AccountPrototype.get_by_id(account_id)
        self.storage = LogicStorage()
        self.storage.load_account_data(self.account)
        self.hero = self.storage.accounts_to_heroes[self.account.id]

        self.card = objects.Card(relations.CARD_TYPE.KEEPERS_GOODS_COMMON)

        self.building_1 = BuildingPrototype.create(person=self.place_1.persons[0], utg_name=names.generator.get_test_name('building-1-name'))


class UseDialogRequestTests(CardsRequestsTestsBase):

    def test_unlogined(self):
        self.check_html_ok(self.request_ajax_html(url('game:cards:use-dialog', card=666)), texts=['common.login_required'])

    def test_no_cards(self):
        self.request_login(self.account.email)
        self.check_html_ok(self.request_ajax_html(url('game:cards:use-dialog', card=666)), texts=['cards.no_card'])

    def test_has_cards(self):
        self.hero.cards.add_card(self.card)
        self.hero.save()

        self.request_login(self.account.email)
        self.check_html_ok(self.request_ajax_html(url('game:cards:use-dialog', card=self.card.uid)))



class UseRequestTests(CardsRequestsTestsBase):

    def post_data(self, card_uid, place_id=None, person_id=None, building_id=None):
        return {'place': self.place_1.id if place_id is None else place_id,
                'person': self.place_1.persons[0].id if person_id is None else person_id,
                'building': self.building_1.id if building_id is None else building_id,}

    def test_unlogined(self):
        self.check_ajax_error(self.post_ajax_json(url('game:cards:use', card=666), self.post_data(666)), 'common.login_required')

    def test_no_cards(self):
        self.request_login(self.account.email)
        self.check_ajax_error(self.post_ajax_json(url('game:cards:use', card=666)), 'cards.no_card')


    def test_form_invalid(self):
        self.request_login(self.account.email)

        self.hero.cards.add_card(self.card)
        self.hero.save()

        # if card_type.form is forms.EmptyForm:
        #     continue

        self.check_ajax_error(self.post_ajax_json(url('game:cards:use', card=self.card.uid),
                                                  self.post_data(self.card.uid, place_id=666, building_id=666, person_id=666)), 'cards.use.form_errors')


    def test_success(self):
        self.request_login(self.account.email)

        self.hero.cards.add_card(self.card)
        self.hero.save()

        response = self.post_ajax_json(url('game:cards:use', card=self.card.uid), self.post_data(self.card.uid))
        task = PostponedTaskPrototype._db_get_object(0)

        self.check_ajax_processing(response, task.status_url)

        task.remove()


class TestIndexRequests(CardsRequestsTestsBase):

    def setUp(self):
        super(TestIndexRequests, self).setUp()

    def test_simple(self):
        texts = [card.TYPE.text for card in CARDS.values()]
        self.check_html_ok(self.request_html(url('guide:cards:')), texts=texts)

    def test_rarity_filter(self):
        for rarity in relations.RARITY.records:
            texts = [card.TYPE.text for card in CARDS.values() if card.TYPE.rarity == rarity]
            self.check_html_ok(self.request_html(url('guide:cards:')), texts=texts)

    def test_availability_filter(self):
        for availability in relations.AVAILABILITY.records:
            texts = [card.TYPE.text for card in CARDS.values() if card.TYPE.availability == availability]
            self.check_html_ok(self.request_html(url('guide:cards:')), texts=texts)
