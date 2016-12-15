
from __future__ import absolute_import

from functools import wraps
from splunk import admin
from solnlib.splunkenv import get_splunkd_uri
from solnlib.utils import is_true

from .eai import EAI_FIELDS
from .handler import RestHandler


__all__ = [
    'make_conf_item',
    'build_conf_info',
    'AdminExternalHandler',
]


def make_conf_item(conf_item, content, eai):
    for key, val in content.iteritems():
        conf_item[key] = val

    for eai_field in EAI_FIELDS:
        conf_item.setMetadata(eai_field, eai.content[eai_field])

    return conf_item


def build_conf_info(meth):
    """
    Build conf info for admin external REST endpoint.

    :param meth:
    :return:
    """
    @wraps(meth)
    def wrapper(self, confInfo):
        result = meth(self, confInfo)
        for entity in result:
            make_conf_item(
                confInfo[entity.name],
                entity.content,
                entity.eai,
            )

    return wrapper


class AdminExternalHandler(admin.MConfigHandler):

    # Leave it for setting REST model
    endpoint = None

    def __init__(self, scriptMode, ctxInfo, request=None):
        admin.MConfigHandler.__init__(
            self,
            scriptMode,
            ctxInfo,
            request,
        )
        self.handler = RestHandler(
            get_splunkd_uri(),
            self.getSessionKey(),
            self.endpoint,
        )
        self.payload = self._convert_payload()

    def setup(self):
        actions = (admin.ACTION_LIST, admin.ACTION_REMOVE)
        if self.requestedAction in actions:
            return

        model = self.endpoint.model(
            self.callerArgs.id,
            self.payload,
        )
        if self.requestedAction == admin.ACTION_CREATE:
            for field in model.fields:
                if field.required:
                    self.supportedArgs.addReqArg(field.name)
                else:
                    self.supportedArgs.addOptArg(field.name)

        if self.requestedAction == admin.ACTION_EDIT:
            for field in model.fields:
                self.supportedArgs.addOptArg(field.name)

    @build_conf_info
    def handleList(self, confInfo):
        if self.callerArgs.id:
            result = self.handler.get(self.callerArgs.id)
        else:
            sort_dir = self.sortAscending and 'asc' or 'desc'
            query = {
                'count': self.maxCount,
                'sort_key': self.sortByKey,
                'sort_dir': sort_dir,
                'offset': self.posOffset,
            }
            result = self.handler.all(**query)
        return result

    @build_conf_info
    def handleCreate(self, confInfo):
        return self.handler.create(
            self.callerArgs.id,
            self.payload,
        )

    @build_conf_info
    def handleEdit(self, confInfo):
        disabled = self.payload.get('disabled')
        if disabled is None:
            return self.handler.update(
                self.callerArgs.id,
                self.payload,
            )
        elif is_true(disabled):
            return self.handler.disable(self.callerArgs.id)
        else:
            return self.handler.enable(self.callerArgs.id)

    @build_conf_info
    def handleRemove(self, confInfo):
        return self.handler.delete(self.callerArgs.id)

    def _convert_payload(self):
        check_actions = (admin.ACTION_CREATE, admin.ACTION_EDIT)
        if self.requestedAction not in check_actions:
            return None

        payload = {}
        for filed, value in self.callerArgs.data.iteritems():
            payload[filed] = value[0] if value and value[0] else ''
        return payload


def handle(
        endpoint,
        handler=AdminExternalHandler,
        context_info=admin.CONTEXT_APP_ONLY,
):
    """
    Handle request.

    :param endpoint: REST endpoint
    :param handler: REST handler
    :param context_info:
    :return:
    """
    real_handler = type(
        handler.__name__,
        (handler, ),
        {'endpoint': endpoint},
    )
    admin.init(real_handler, ctxInfo=context_info)
