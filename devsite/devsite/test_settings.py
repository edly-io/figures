"""
Settings file to run automated tests

"""

from __future__ import absolute_import, unicode_literals

from os.path import abspath, dirname, join
import environ
import sys

from figures.settings.lms_production import (
    update_celerybeat_schedule,
    # TODO: https://appsembler.atlassian.net/browse/RED-673
    # update_webpack_loader,
)


COURSE_ID_PATTERN = r'(?P<course_id>[^/+]+(/|\+)[^/+]+(/|\+)[^/?]+)'


def root(*args):
    """
    Get the absolute path of the given path relative to the project root.
    """
    return join(abspath(dirname(__file__)), *args)


env = environ.Env(
    OPENEDX_RELEASE=(str, 'JUNIPER'),
)

environ.Env.read_env()

OPENEDX_RELEASE = env('OPENEDX_RELEASE').upper()

MOCKS_DIR = 'mocks/{}'.format(OPENEDX_RELEASE.lower())

sys.path.append(root('mocks', MOCKS_DIR))


# Set the default Site (django.contrib.sites.models.Site)
SITE_ID = 1

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'default.db',
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
    }
}


INSTALLED_APPS = [
    'django.contrib.admin',  # Why did it work without this before?
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sites',
    'rest_framework',
    'django_countries',
    'django_filters',
    'devsite',
    'webpack_loader',
    'figures',

    # edx-platform apps. Mocks are used by default
    # See: edx-figures/tests/mocks/
    # Also note the paths set in edx-figures/pytest.ini
    'edx_when',
    'config_models',
    'organizations',
    'lms.djangoapps.branding',
    'lms.djangoapps.grades',
    'openedx.core.djangoapps.catalog',
    'openedx.core.djangoapps.content.course_overviews',
    'openedx.core.djangoapps.django_comment_common',
    'openedx.features.content_type_gating',
    'openedx.core.djangoapps.course_groups',
    'openedx.core.djangoapps.site_configuration',
    'openedx.core.djangoapps.video_pipeline',
    'openedx.features.edly',
    'student',
    'track',
    'eventtracking.django.apps.EventTrackingConfig',
    'util',
    'course_modes',
    'coursewarehistoryextended',
    'experiments',
]

if OPENEDX_RELEASE == 'GINKGO':
    INSTALLED_APPS.append('certificates')
    INSTALLED_APPS.append('courseware')
elif OPENEDX_RELEASE == 'HAWTHORN':
    INSTALLED_APPS.append('lms.djangoapps.certificates')
    INSTALLED_APPS.append('courseware')
else:
    INSTALLED_APPS.append('lms.djangoapps.certificates')
    INSTALLED_APPS.append('lms.djangoapps.courseware')
    INSTALLED_APPS.append('openedx.core.djangoapps.content.block_structure')
    INSTALLED_APPS.append('completion')
    INSTALLED_APPS.append('edx_django_utils')

BLOCK_STRUCTURES_SETTINGS = dict(
    # Delay, in seconds, after a new edit of a course is published
    # before updating the block structures cache.  This is needed
    # for a better chance at getting the latest changes when there
    # are secondary reads in sharded mongoDB clusters. See TNL-5041
    # for more info.
    COURSE_PUBLISH_TASK_DELAY=30,

    # Delay, in seconds, between retry attempts if a task fails.
    TASK_DEFAULT_RETRY_DELAY=30,

    # Maximum number of retries per task.
    TASK_MAX_RETRIES=5,
)

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            join('devsite', 'devsite', 'templates'),
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]


LOCALE_PATHS = [
    root('figures', 'conf', 'locale'),
]

ROOT_URLCONF = 'figures.urls'

SECRET_KEY = 'insecure-secret-key'

USE_TZ = True
TIME_ZONE = 'UTC'

# https://wsvincent.com/django-rest-framework-serializers-viewsets-routers/

# For initial testing, later we want to enforce authorization
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ]
}

# Webpack loader is required to load Figure's front-end
WEBPACK_LOADER = {
    'FIGURES_APP': {
        'BUNDLE_DIR_NAME': 'figures/',
        'STATS_FILE': 'tests/test-webpack-stats.json',
    }
}
CELERYBEAT_SCHEDULE = {}
FEATURES = {
    'FIGURES_IS_MULTISITE': True
}

# The LMS defines ``ENV_TOKENS`` to load settings declared in `lms.env.json`
# We have an empty dict here to replicate behavior in the LMS
ENV_TOKENS = {}

# TODO: https://appsembler.atlassian.net/browse/RED-673
# update_webpack_loader(WEBPACK_LOADER, ENV_TOKENS)
update_celerybeat_schedule(CELERYBEAT_SCHEDULE, ENV_TOKENS)

COURSE_MODE_DEFAULTS = {
    'bulk_sku': None,
    'currency': 'usd',
    'description': None,
    'expiration_datetime': None,
    'min_price': 0,
    'name': 'Audit',
    'sku': None,
    'slug': 'audit',
    'suggested_prices': '',
}

SOFTWARE_SECURE_REQUEST_RETRY_DELAY = 60 * 60

SOFTWARE_SECURE_RETRY_MAX_ATTEMPTS = 6

ALL_LANGUAGES = [
    [u"aa", u"Afar"],
    [u"ab", u"Abkhazian"],
    [u"af", u"Afrikaans"],
    [u"ak", u"Akan"],
    [u"sq", u"Albanian"],
    [u"am", u"Amharic"],
    [u"ar", u"Arabic"],
    [u"an", u"Aragonese"],
    [u"hy", u"Armenian"],
    [u"as", u"Assamese"],
    [u"av", u"Avaric"],
    [u"ae", u"Avestan"],
    [u"ay", u"Aymara"],
    [u"az", u"Azerbaijani"],
    [u"ba", u"Bashkir"],
    [u"bm", u"Bambara"],
    [u"eu", u"Basque"],
    [u"be", u"Belarusian"],
    [u"bn", u"Bengali"],
    [u"bh", u"Bihari languages"],
    [u"bi", u"Bislama"],
    [u"bs", u"Bosnian"],
    [u"br", u"Breton"],
    [u"bg", u"Bulgarian"],
    [u"my", u"Burmese"],
    [u"ca", u"Catalan"],
    [u"ch", u"Chamorro"],
    [u"ce", u"Chechen"],
    [u"zh", u"Chinese"],
    [u"zh_HANS", u"Simplified Chinese"],
    [u"zh_HANT", u"Traditional Chinese"],
    [u"cu", u"Church Slavic"],
    [u"cv", u"Chuvash"],
    [u"kw", u"Cornish"],
    [u"co", u"Corsican"],
    [u"cr", u"Cree"],
    [u"cs", u"Czech"],
    [u"da", u"Danish"],
    [u"dv", u"Divehi"],
    [u"nl", u"Dutch"],
    [u"dz", u"Dzongkha"],
    [u"en", u"English"],
    [u"eo", u"Esperanto"],
    [u"et", u"Estonian"],
    [u"ee", u"Ewe"],
    [u"fo", u"Faroese"],
    [u"fj", u"Fijian"],
    [u"fi", u"Finnish"],
    [u"fr", u"French"],
    [u"fy", u"Western Frisian"],
    [u"ff", u"Fulah"],
    [u"ka", u"Georgian"],
    [u"de", u"German"],
    [u"gd", u"Gaelic"],
    [u"ga", u"Irish"],
    [u"gl", u"Galician"],
    [u"gv", u"Manx"],
    [u"el", u"Greek"],
    [u"gn", u"Guarani"],
    [u"gu", u"Gujarati"],
    [u"ht", u"Haitian"],
    [u"ha", u"Hausa"],
    [u"he", u"Hebrew"],
    [u"hz", u"Herero"],
    [u"hi", u"Hindi"],
    [u"ho", u"Hiri Motu"],
    [u"hr", u"Croatian"],
    [u"hu", u"Hungarian"],
    [u"ig", u"Igbo"],
    [u"is", u"Icelandic"],
    [u"io", u"Ido"],
    [u"ii", u"Sichuan Yi"],
    [u"iu", u"Inuktitut"],
    [u"ie", u"Interlingue"],
    [u"ia", u"Interlingua"],
    [u"id", u"Indonesian"],
    [u"ik", u"Inupiaq"],
    [u"it", u"Italian"],
    [u"jv", u"Javanese"],
    [u"ja", u"Japanese"],
    [u"kl", u"Kalaallisut"],
    [u"kn", u"Kannada"],
    [u"ks", u"Kashmiri"],
    [u"kr", u"Kanuri"],
    [u"kk", u"Kazakh"],
    [u"km", u"Central Khmer"],
    [u"ki", u"Kikuyu"],
    [u"rw", u"Kinyarwanda"],
    [u"ky", u"Kirghiz"],
    [u"kv", u"Komi"],
    [u"kg", u"Kongo"],
    [u"ko", u"Korean"],
    [u"kj", u"Kuanyama"],
    [u"ku", u"Kurdish"],
    [u"lo", u"Lao"],
    [u"la", u"Latin"],
    [u"lv", u"Latvian"],
    [u"li", u"Limburgan"],
    [u"ln", u"Lingala"],
    [u"lt", u"Lithuanian"],
    [u"lb", u"Luxembourgish"],
    [u"lu", u"Luba-Katanga"],
    [u"lg", u"Ganda"],
    [u"mk", u"Macedonian"],
    [u"mh", u"Marshallese"],
    [u"ml", u"Malayalam"],
    [u"mi", u"Maori"],
    [u"mr", u"Marathi"],
    [u"ms", u"Malay"],
    [u"mg", u"Malagasy"],
    [u"mt", u"Maltese"],
    [u"mn", u"Mongolian"],
    [u"na", u"Nauru"],
    [u"nv", u"Navajo"],
    [u"nr", u"Ndebele, South"],
    [u"nd", u"Ndebele, North"],
    [u"ng", u"Ndonga"],
    [u"ne", u"Nepali"],
    [u"nn", u"Norwegian Nynorsk"],
    [u"nb", u"Bokmål, Norwegian"],
    [u"no", u"Norwegian"],
    [u"ny", u"Chichewa"],
    [u"oc", u"Occitan"],
    [u"oj", u"Ojibwa"],
    [u"or", u"Oriya"],
    [u"om", u"Oromo"],
    [u"os", u"Ossetian"],
    [u"pa", u"Panjabi"],
    [u"fa", u"Persian"],
    [u"pi", u"Pali"],
    [u"pl", u"Polish"],
    [u"pt", u"Portuguese"],
    [u"ps", u"Pushto"],
    [u"qu", u"Quechua"],
    [u"rm", u"Romansh"],
    [u"ro", u"Romanian"],
    [u"rn", u"Rundi"],
    [u"ru", u"Russian"],
    [u"sg", u"Sango"],
    [u"sa", u"Sanskrit"],
    [u"si", u"Sinhala"],
    [u"sk", u"Slovak"],
    [u"sl", u"Slovenian"],
    [u"se", u"Northern Sami"],
    [u"sm", u"Samoan"],
    [u"sn", u"Shona"],
    [u"sd", u"Sindhi"],
    [u"so", u"Somali"],
    [u"st", u"Sotho, Southern"],
    [u"es", u"Spanish"],
    [u"sc", u"Sardinian"],
    [u"sr", u"Serbian"],
    [u"ss", u"Swati"],
    [u"su", u"Sundanese"],
    [u"sw", u"Swahili"],
    [u"sv", u"Swedish"],
    [u"ty", u"Tahitian"],
    [u"ta", u"Tamil"],
    [u"tt", u"Tatar"],
    [u"te", u"Telugu"],
    [u"tg", u"Tajik"],
    [u"tl", u"Tagalog"],
    [u"th", u"Thai"],
    [u"bo", u"Tibetan"],
    [u"ti", u"Tigrinya"],
    [u"to", u"Tonga (Tonga Islands)"],
    [u"tn", u"Tswana"],
    [u"ts", u"Tsonga"],
    [u"tk", u"Turkmen"],
    [u"tr", u"Turkish"],
    [u"tw", u"Twi"],
    [u"ug", u"Uighur"],
    [u"uk", u"Ukrainian"],
    [u"ur", u"Urdu"],
    [u"uz", u"Uzbek"],
    [u"ve", u"Venda"],
    [u"vi", u"Vietnamese"],
    [u"vo", u"Volapük"],
    [u"cy", u"Welsh"],
    [u"wa", u"Walloon"],
    [u"wo", u"Wolof"],
    [u"xh", u"Xhosa"],
    [u"yi", u"Yiddish"],
    [u"yo", u"Yoruba"],
    [u"za", u"Zhuang"],
    [u"zu", u"Zulu"]
]

TRACK_MAX_EVENT = 50000

EVENT_TRACKING_ENABLED = True

ADMIN_CONFIGURATION_USERS_GROUP = 'Admin Configuration Users'
EDLY_PANEL_USERS_GROUP = 'Edly Panel Users'
EDLY_INSIGHTS_GROUP = 'Edly Insights Admin'
EDLY_PANEL_ADMIN_USERS_GROUP = 'Edly Panel Admin Users'
EDLY_PANEL_RESTRICTED_USERS_GROUP = 'Edly Panel Restricted Users'
EDLY_WP_ADMIN_USERS_GROUP = 'WordPress Edly Admin Users'
EDLY_WP_SUBSCRIBER_USERS_GROUP = 'WordPress Subscriber Users'
