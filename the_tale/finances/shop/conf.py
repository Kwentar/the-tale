# coding: utf-8

from django.conf import settings as project_settings

from dext.common.utils.app_settings import app_settings

payments_settings = app_settings('PAYMENTS',
                                 PREMIUM_CURRENCY_FOR_DOLLAR=100,
                                 ENABLE_REAL_PAYMENTS=False if not project_settings.TESTS_RUNNING else True,
                                 SETTINGS_ALLOWED_KEY='payments allowed',

                                 GLOBAL_COST_MULTIPLIER = 1.0,

                                 ALWAYS_ALLOWED_ACCOUNTS=[],

                                 RANDOM_PREMIUM_DAYS=30,

                                 XSOLLA_ENABLED=False if not project_settings.TESTS_RUNNING else True,

                                 XSOLLA_RUB_FOR_PREMIUM_CURRENCY=0.013,

                                 # default values was gotten from documentation
                                 XSOLLA_BASE_LINK= u'https://secure.xsolla.com/paystation2/',
                                 XSOLLA_PID=6,
                                 XSOLLA_MARKETPLACE=u'paydesk',
                                 XSOLLA_THEME=115,
                                 XSOLLA_PROJECT=4521,
                                 XSOLLA_LOCAL=u'ru',
                                 XSOLLA_DESCRIPTION=u'покупка печенек',
                                 XSOLLA_ID_THEME='id_theme',

                                 XSOLLA_DIALOG_WIDTH=900,
                                 XSOLLA_DIALOG_HEIGHT=800,

                                 REFERRAL_BONUS=0.1)
