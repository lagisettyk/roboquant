"""
Django settings for roboquant project.

Generated by 'django-admin startproject' using Django 1.8.1.

For more information on this file, see
https://docs.djangoproject.com/en/1.8/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.8/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TEMPLATE_PATH = os.path.join(BASE_DIR, 'templates')
#print TEMPLATE_PATH

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.8/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '&&-hxk0d+l3%iyfqggw59ve47i#wq(*4k5_35t&0ppo_f$57d3'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

#ALLOWED_HOSTS = []

# # Allow all host hosts/domain names for this site
ALLOWED_HOSTS = ['*']

#### Settings for 'allauth' package
AUTHENTICATION_BACKENDS = (
    # Need to login by username in Django admin, regardless of 'allauth'
    'django.contrib.auth.backends.ModelBackend',
    # 'allauth' specific authentication methods, such as login by email
    'allauth.account.auth_backends.AuthenticationBackend',
)

# settings for 'allauth' template context processors
TEMPLATE_CONTEXT_PROCESSORS = (
    'django.core.context_processors.request',
    'django.contrib.auth.context_processors.auth',
    'allauth.account.context_processors.account',
    'allauth.socialaccount.context_processors.socialaccount',
)

## settings related to django-registraion-redux package...
'''
REGISTRATION_OPEN = True  # If True users can register
ACCOUNT_ACTIVATION_DAYS = 7 # one-week activation window;
REGISTRATION_AUTO_LOGIN = True # If true, the user will be automatically logged on
LOGIN_REDIRECT_URL = '/strategies/' # The page you want to see after users login
LOGIN_URL = '/accounts/login/' # The page users are directed if they are not logged on
'''

# auth and all auth settings
SITE_ID = 1
LOGIN_REDIRECT_URL = "/strategies/"
LOGIN_URL = '/accounts/login/'
ACCOUNT_AUTHENTICATION_METHOD = 'username_email'
ACCOUNT_EMAIL_REQUIRED = True
SOCIALACCOUNT_QUERY_EMAIL = True
SOCIALACCOUNT_PROVIDERS = \
     {'facebook':
       {'SCOPE': ['email', 'public_profile', 'user_friends'],
        'AUTH_PARAMS': {'auth_type': 'reauthenticate'},
        'METHOD': 'js_sdk',
        'LOCALE_FUNC': lambda request: 'zh_CN',
        'VERIFIED_EMAIL': False,
        'VERSION': 'v2.3'}}
#### We still need to add email settings related to SendGrid on heroku...
#EMAIL_HOST_USER = 'app36635398@heroku.com'
#EMAIL_HOST= 'smtp.sendgrid.net'
#EMAIL_PORT = 587
#EMAIL_USE_TLS = True
#EMAIL_HOST_PASSWORD = '9bclxblu2966'

#########POSTMARK settings.......
EMAIL_BACKEND = 'postmark.backends.PostmarkBackend'
POSTMARK_API_KEY = '49faaa9f-4368-49ab-8b66-c30cb3a6ada'

# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'bootstrap_toolkit', # django's bootstrap toolkit package
    #'registration', # add in the django registation package
    'strategies', # xiQuant shell application

    ### 'allauth' related applications
    'django.contrib.sites',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.facebook',
    'allauth.socialaccount.providers.google',
    'postmark', #### for email backend services...
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.security.SecurityMiddleware',
)

ROOT_URLCONF = 'roboquant.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [TEMPLATE_PATH,],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',

                ### 'allauth' settings.... duplicate in addition to the TEMPLATE_CONTEXT
                'django.core.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'allauth.account.context_processors.account',
                'allauth.socialaccount.context_processors.socialaccount',
            ],
        },
    },
]

WSGI_APPLICATION = 'roboquant.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.8/ref/settings/#databases
'''
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}
'''

#Posgres local configuration...
'''
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'roboquant',
        'USER': 'lagisettyk',
        'PASSWORD': '$$$50shetty27',
        'HOST': 'localhost',
        'PORT': '',
      }
}
'''


import dj_database_url
DATABASES = {}
DATABASES['default'] =  dj_database_url.config()
DATABASES['default']['ENGINE'] = 'django.db.backends.postgresql_psycopg2'
#print DATABASES


# Honor the 'X-Forwarded-Proto' header for request.is_secure()
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

### Add redis cloud URL settings here...
REDIS_URL = 'redis://rediscloud:8onBIntrnVaqdl3u@pub-redis-18013.us-east-1-2.2.ec2.garantiadata.com:18013'

# try to load local_settings.py if it exists
try:
  from local_settings import *
  #print "Inside settings.py for local settings: ", DATABASES
except Exception as e:
  pass


# Internationalization
# https://docs.djangoproject.com/en/1.8/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.8/howto/static-files/
STATIC_ROOT = 'staticfiles'

STATIC_URL = '/static/'

STATICFILES_DIRS = (
    os.path.join(BASE_DIR, 'static'),
)

# Simplified static file serving.
# https://warehouse.python.org/project/whitenoise/

#STATICFILES_STORAGE = 'whitenoise.django.GzipManifestStaticFilesStorage'
