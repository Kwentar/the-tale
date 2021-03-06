# coding: utf-8
import time
import datetime

import mock

from django.contrib.auth import authenticate as django_authenticate
from django.contrib.auth.hashers import make_password

from the_tale.common.utils import testcase

from the_tale.post_service.models import Message

from the_tale.game.logic import create_test_map

from the_tale.accounts.personal_messages.prototypes import MessagePrototype as PersonalMessagePrototype

from the_tale.accounts.logic import register_user
from the_tale.accounts.prototypes import AccountPrototype
from the_tale.accounts.conf import accounts_settings
from the_tale.accounts.achievements.relations import ACHIEVEMENT_TYPE


class AccountPrototypeTests(testcase.TestCase):

    def setUp(self):
        super(AccountPrototypeTests, self).setUp()
        self.place_1, self.place_2, self.place_3 = create_test_map()

        result, account_id, bundle_id = register_user('test_user', 'test_user@test.com', '111111')
        self.account = AccountPrototype.get_by_id(account_id)

        result, account_id, bundle_id = register_user('fast_user')
        self.fast_account = AccountPrototype.get_by_id(account_id)

    def test_create(self):
        self.assertTrue(self.account.active_end_at > datetime.datetime.now() + datetime.timedelta(seconds=accounts_settings.ACTIVE_STATE_TIMEOUT - 60))

    def test_get_achievement_type_value(self):
        for achievement_type in ACHIEVEMENT_TYPE.records:
            if achievement_type.source.is_GAME_OBJECT:
                continue
            if achievement_type.source.is_NONE:
                continue
            self.account.get_achievement_type_value(achievement_type)


    @mock.patch('the_tale.accounts.conf.accounts_settings.ACTIVE_STATE_REFRESH_PERIOD', 0)
    def test_update_active_state__expired(self):
        self.assertTrue(self.account.is_update_active_state_needed)
        with mock.patch('the_tale.game.workers.supervisor.Worker.cmd_update_hero_with_account_data') as cmd_mark_hero_as_active:
            self.account.update_active_state()
        self.assertEqual(cmd_mark_hero_as_active.call_count, 1)

    def test_update_active_state__not_expired(self):
        self.assertFalse(self.account.is_update_active_state_needed)

    def test_change_credentials(self):
        self.assertTrue(AccountPrototype.get_by_id(self.fast_account.id).is_fast)

        with mock.patch('the_tale.game.workers.supervisor.Worker.cmd_update_hero_with_account_data') as fake_cmd:
            with mock.patch('the_tale.accounts.workers.accounts_manager.Worker.cmd_run_account_method') as cmd_run_account_method:
                self.fast_account.change_credentials(new_email='fast_user@test.ru', new_password=make_password('222222'), new_nick='test_nick')

        self.assertEqual(cmd_run_account_method.call_count, 0)

        self.assertEqual(django_authenticate(nick='test_nick', password='222222').id, self.fast_account.id)
        self.assertFalse(AccountPrototype.get_by_id(self.fast_account.id).is_fast)
        self.assertEqual(fake_cmd.call_count, 1)
        self.assertFalse(fake_cmd.call_args[1]['is_fast'])

    def test_change_credentials__with_referral(self):
        self.fast_account._model.referral_of = self.account._model
        self.fast_account.save()

        self.assertTrue(AccountPrototype.get_by_id(self.fast_account.id).is_fast)

        with mock.patch('the_tale.game.workers.supervisor.Worker.cmd_update_hero_with_account_data') as fake_cmd:
            with mock.patch('the_tale.accounts.workers.accounts_manager.Worker.cmd_run_account_method') as cmd_run_account_method:
                self.fast_account.change_credentials(new_email='fast_user@test.ru', new_password=make_password('222222'), new_nick='test_nick')

        self.assertEqual(cmd_run_account_method.call_count, 1)
        self.assertEqual(cmd_run_account_method.call_args, mock.call(account_id=self.account.id,
                                                                     method_name=AccountPrototype.update_referrals_number.__name__,
                                                                     data={}))

        self.assertEqual(django_authenticate(nick='test_nick', password='222222').id, self.fast_account.id)
        self.assertFalse(AccountPrototype.get_by_id(self.fast_account.id).is_fast)
        self.assertEqual(fake_cmd.call_count, 1)
        self.assertFalse(fake_cmd.call_args[1]['is_fast'])

    def test_change_credentials_password(self):
        self.account.change_credentials(new_password=make_password('222222'))

        self.assertEqual(Message.objects.all().count(), 0)

        self.assertEqual(self.account.email, 'test_user@test.com')
        user = django_authenticate(nick='test_user', password='222222')
        self.assertEqual(user.id, self.account.id)

    def test_change_credentials_nick(self):

        with mock.patch('the_tale.game.workers.supervisor.Worker.cmd_update_hero_with_account_data') as fake_cmd:
            self.account.change_credentials(new_nick='test_nick')

        self.assertEqual(Message.objects.all().count(), 0)
        self.assertEqual(fake_cmd.call_count, 0)
        self.assertEqual(django_authenticate(nick='test_nick', password='111111').id, self.account.id)

    def test_change_credentials_email(self):
        self.account.change_credentials(new_email='test_user@test.ru')

        self.assertEqual(Message.objects.all().count(), 0)

        self.assertEqual(self.account.email, 'test_user@test.ru')
        self.assertEqual(django_authenticate(nick='test_user', password='111111').id, self.account.id)
        self.assertEqual(django_authenticate(nick='test_user', password='111111').nick, 'test_user')

    def test_prolong_premium__for_new_premium(self):
        self.account._model.premium_end_at = datetime.datetime.now() - datetime.timedelta(days=100)

        self.account.prolong_premium(days=30)

        self.assertTrue(datetime.datetime.now() + datetime.timedelta(days=29) < self.account.premium_end_at)
        self.assertTrue(datetime.datetime.now() + datetime.timedelta(days=31) > self.account.premium_end_at)

    def test_prolong_premium__for_existed_premium(self):
        self.account._model.premium_end_at = datetime.datetime.now() + datetime.timedelta(days=100)

        self.account.prolong_premium(days=30)

        self.assertTrue(datetime.datetime.now() + datetime.timedelta(days=129) < self.account.premium_end_at)
        self.assertTrue(datetime.datetime.now() + datetime.timedelta(days=131) > self.account.premium_end_at)

    def test_is_premium(self):
        self.assertFalse(self.account.is_premium)
        self.account.prolong_premium(days=1)
        self.assertTrue(self.account.is_premium)

    def test_notify_about_premium_expiration(self):
        self.assertEqual(PersonalMessagePrototype._db_count(), 0)
        self.account.notify_about_premium_expiration()
        self.assertEqual(PersonalMessagePrototype._db_count(), 1)

    def test_send_premium_expired_notifications(self):
        self.assertEqual(PersonalMessagePrototype._db_count(), 0)

        register_user('test_user_2', 'test_user_2@test.com', '111111')
        register_user('test_user_3', 'test_user_3@test.com', '111111')
        register_user('test_user_4', 'test_user_4@test.com', '111111')

        account_1 = self.account
        account_2 = AccountPrototype.get_by_nick('test_user_2')
        account_3 = AccountPrototype.get_by_nick('test_user_3')
        account_4 = AccountPrototype.get_by_nick('test_user_4')

        account_1.prolong_premium(accounts_settings.PREMIUM_EXPIRED_NOTIFICATION_IN.days-1)
        account_1.save()

        account_3.prolong_premium(accounts_settings.PREMIUM_EXPIRED_NOTIFICATION_IN.days-1)
        account_3.save()

        account_4.prolong_premium(accounts_settings.PREMIUM_EXPIRED_NOTIFICATION_IN.days+1)
        account_4.save()

        zero_time = datetime.datetime.fromtimestamp(0)

        self.assertEqual(account_1._model.premium_expired_notification_send_at, zero_time)
        self.assertEqual(account_2._model.premium_expired_notification_send_at, zero_time)
        self.assertEqual(account_3._model.premium_expired_notification_send_at, zero_time)
        self.assertEqual(account_4._model.premium_expired_notification_send_at, zero_time)

        AccountPrototype.send_premium_expired_notifications()

        account_1.reload()
        account_2.reload()
        account_3.reload()
        account_4.reload()

        self.assertNotEqual(account_1._model.premium_expired_notification_send_at, zero_time)
        self.assertEqual(account_2._model.premium_expired_notification_send_at, zero_time)
        self.assertNotEqual(account_3._model.premium_expired_notification_send_at, zero_time)
        self.assertEqual(account_4._model.premium_expired_notification_send_at, zero_time)

        current_time = datetime.datetime.now()

        self.assertTrue(current_time-datetime.timedelta(seconds=60) < account_1._model.premium_expired_notification_send_at < current_time)
        self.assertTrue(current_time-datetime.timedelta(seconds=60) < account_3._model.premium_expired_notification_send_at < current_time)

        self.assertEqual(PersonalMessagePrototype._db_count(), 2)

    def test_ban_game(self):
        self.assertFalse(self.account.is_ban_game)
        with mock.patch('the_tale.game.workers.supervisor.Worker.cmd_update_hero_with_account_data') as cmd_update_hero_with_account_data:
            self.account.ban_game(days=1)
        self.assertEqual(cmd_update_hero_with_account_data.call_count, 1)
        self.assertEqual(cmd_update_hero_with_account_data.call_args[1]['ban_end_at'], self.account.ban_game_end_at)
        self.assertTrue(self.account.is_ban_game)
        self.account._model.ban_game_end_at = datetime.datetime.now()
        self.assertFalse(self.account.is_ban_game)

    def test_ban_forum(self):
        self.assertFalse(self.account.is_ban_forum)
        self.account.ban_forum(days=1)
        self.assertTrue(self.account.is_ban_forum)
        self.account._model.ban_forum_end_at = datetime.datetime.now()
        self.assertFalse(self.account.is_ban_forum)

    def test_bank_account__not_created(self):
        bank_account = self.account.bank_account

        self.assertTrue(bank_account.is_fake)
        self.assertEqual(bank_account.amount, 0)

    def test_update_referrals(self):
        register_user('user_2', 'user_2@test.com', '111111', referral_of_id=self.account.id)
        register_user('fast_user_3', referral_of_id=self.account.id)

        self.account.update_referrals_number()
        self.fast_account.update_referrals_number()

        self.assertEqual(self.account.referrals_number, 1)
        self.assertEqual(self.fast_account.referrals_number, 0)

    def test_referral_removing(self):
        result, account_id, bundle_id = register_user('fast_user_2', referral_of_id=self.account.id)

        self.account.remove()

        # child account must not be removed
        self.assertEqual(AccountPrototype.get_by_id(account_id).referral_of_id, None)


    def test_set_might(self):
        with mock.patch('the_tale.accounts.achievements.storage.AchievementsStorage.verify_achievements') as verify_achievements:
            self.account.set_might(666)

        self.assertEqual(verify_achievements.call_args_list, [mock.call(account_id=self.account.id,
                                                                        type=ACHIEVEMENT_TYPE.KEEPER_MIGHT,
                                                                        old_value=0,
                                                                        new_value=666)])

    @mock.patch('the_tale.game.bills.conf.bills_settings.MIN_VOTES_PERCENT', 0.6)
    @mock.patch('the_tale.game.bills.prototypes.BillPrototype.time_before_voting_end', datetime.timedelta(seconds=0))
    # fixt segmentation fault when testing with sqlite
    def test_1_update_actual_bills(self):
        from the_tale.game.bills import prototypes as bills_prototypes
        from the_tale.game.bills import bills
        from the_tale.game.bills import conf as bills_conf
        from the_tale.game.map.places import modifiers as places_modifiers
        from the_tale.forum import models as forum_models

        forum_category = forum_models.Category.objects.create(caption='category-1', slug='category-1')
        forum_models.SubCategory.objects.create(caption=bills_conf.bills_settings.FORUM_CATEGORY_UID + '-caption',
                                                uid=bills_conf.bills_settings.FORUM_CATEGORY_UID,
                                                category=forum_category)

        self.account.update_actual_bills()
        self.assertEqual(self.account.actual_bills, [])

        bill_data = bills.PlaceModifier(place_id=self.place_1.id,
                                        modifier_id=places_modifiers.TradeCenter.get_id(),
                                        modifier_name=places_modifiers.TradeCenter.TYPE.text,
                                       old_modifier_name=None)
        bill = bills_prototypes.BillPrototype.create(self.account, 'bill-1-caption', 'bill-1-rationale', bill_data, chronicle_on_accepted='chronicle-on-accepted')

        self.account.update_actual_bills()
        self.assertEqual(self.account.actual_bills, [])

        form = bills.PlaceModifier.ModeratorForm({'approved': True})
        self.assertTrue(form.is_valid())
        bill.update_by_moderator(form)

        bill.apply()

        self.account.update_actual_bills()
        self.assertEqual(self.account.actual_bills, [time.mktime(bill.voting_end_at.timetuple())])
