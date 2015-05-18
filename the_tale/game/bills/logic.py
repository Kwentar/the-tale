# coding: utf-8
import datetime

from the_tale.game.bills import models
from the_tale.game.bills import relations
from the_tale.game.bills import conf


def actual_bills_number(account_id):
    return models.Bill.objects.filter(state=relations.BILL_STATE.ACCEPTED,
                                      ownder=account_id,
                                      voting_end_at__gt=datetime.datetime.now() - datetime.timedelta(seconds=conf.bills_settings.BILL_ACTUAL_LIVE_TIME))