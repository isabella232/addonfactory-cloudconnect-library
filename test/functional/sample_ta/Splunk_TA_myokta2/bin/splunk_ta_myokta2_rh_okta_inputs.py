
import splunk_ta_myokta2_import_declare

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    DataInputModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler

util.remove_http_proxy_env_vars()


fields = [
    field.RestField(
        'account',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'api_key',
        required=False,
        encrypted=True,
        default=None,
        validator=None
    ), 
    field.RestField(
        'interval',
        required=False,
        encrypted=False,
        default='60',
        validator=None
    ), 
    field.RestField(
        'event_metrics',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'limit_count',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'event_id',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'index',
        required=True,
        encrypted=False,
        default='default',
        validator=None
    ), 

    field.RestField(
        'disabled',
        required=False,
        validator=None
    )

]
model = RestModel(fields, name=None)



endpoint = DataInputModel(
    'okta_inputs',
    model,
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=AdminExternalHandler,
    )
