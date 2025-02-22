import os
import re
ta_name = os.path.basename(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ta_lib_name = re.sub("[^\w]+", "_", ta_name.lower())
__import__(ta_lib_name + "_import_declare")
from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    MultipleModel,
)
from splunktaucclib.rest_handler import admin_external
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler


fields_logging = [

    field.RestField(
        'loglevel',
        required=False,
        encrypted=False,
        default='INFO',
        validator=None
    )
]
model_logging = RestModel(fields_logging, name='logging')


fields_proxy = [

    field.RestField(
        'proxy_enabled',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 

    field.RestField(
        'proxy_type',
        required=False,
        encrypted=False,
        default='http',
        validator=None
    ), 

    field.RestField(
        'proxy_url',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 

    field.RestField(
        'proxy_port',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 

    field.RestField(
        'proxy_username',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 

    field.RestField(
        'proxy_password',
        required=False,
        encrypted=True,
        default=None,
        validator=None
    )
]
model_proxy = RestModel(fields_proxy, name='proxy')


endpoint = MultipleModel(
    'splunk_ta_snow_settings',
    models=[
        model_logging, 
        model_proxy
    ],
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=AdminExternalHandler,
    )
