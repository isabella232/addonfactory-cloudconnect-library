import base64
import logging

from .ext import lookup_method
from .template import compile_template

logging.basicConfig(level=logging.DEBUG)
_LOGGER = logging


class _Token(object):
    """Token class wraps a template expression"""

    def __init__(self, template_expr):
        self._render = compile_template(template_expr)

    def value(self, variables):
        return self._render(variables)


class BaseAuth(object):
    """A base class for all authorization classes"""

    def __call__(self, headers, context):
        raise NotImplementedError('Auth must be callable.')


class BasicAuthorization(BaseAuth):
    """BasicAuthorization class implements basic auth"""

    def __init__(self, options):
        if not options:
            raise ValueError('Options for basic auth unexpected to be empty')

        username = options.get('username')
        if not username:
            raise ValueError('Username is mandatory for basic auth')
        password = options.get('password')
        if not password:
            raise ValueError('Password is mandatory for basic auth')

        self._username = _Token(username)
        self._password = _Token(password)

    def __call__(self, headers, context):
        username = self._username.value(context)
        password = self._password.value(context)
        headers['Authorization'] = 'Basic %s' % base64.encodestring(
            username + ':' + password
        ).strip()


class Options(object):
    def __init__(self, url, method, header=None, auth=None, body=None):
        self._header = {k: _Token(v) for k, v in (header or {}).iteritems()}
        self._url = _Token(url)
        self._method = method.upper()
        self._auth = auth
        self._body = {k: _Token(v) for k, v in (body or {}).iteritems()}

    @property
    def header(self):
        return self._header

    @property
    def url(self):
        return self._url

    @property
    def method(self):
        return self._method

    @property
    def auth(self):
        return self._auth

    @property
    def body(self):
        return self._body

    def normalize_url(self, context):
        return self._url.value(context)

    def normalize_header(self, context):
        return {k: v.value(context) for k, v in self._header.iteritems()}

    def normalize_body(self, context):
        return {k: v.value(context) for k, v in self._body.iteritems()}


class _Function(object):
    def __init__(self, inputs, function):
        self._inputs = tuple(_Token(expr) for expr in inputs or [])
        self._function = function

    @property
    def inputs(self):
        return self._inputs

    def inputs_values(self, context):
        """
        Get rendered input values.
        """
        for arg in self._inputs:
            yield arg.value(context)

    @property
    def function(self):
        return self._function


class Task(_Function):
    """Task class wraps a task in processor pipeline"""

    def __init__(self, inputs, function, output=None):
        super(Task, self).__init__(inputs, function)
        self._output = output

    @property
    def output(self):
        return self._output

    def execute(self, context):
        """Execute task with arguments which rendered from context """
        args = [arg for arg in self.inputs_values(context)]
        caller = lookup_method(self.function)
        output = self._output

        _LOGGER.info(
            'Executing task method: [%s], output: [%s]', self.function, output
        )

        if output is None:
            caller(*args)
            return {}

        return {output: caller(*args)}


class Condition(_Function):
    """A condition return the value calculated from input and function"""

    def calculate(self, context):
        args = [arg for arg in self.inputs_values(context)]
        caller = lookup_method(self.function)
        return caller(*args)


class _Conditional(object):
    """A base class for all conditional action"""

    def __init__(self, conditions):
        self._conditions = conditions or []

    @property
    def conditions(self):
        return self._conditions

    def passed(self, context):
        """
        Determine if current conditions are all passed.
        :param context: variables to render template
        :return: `True` if all passed else `False`
        """
        for condition in self._conditions:
            if not condition.calculate(context):
                return False
        return True


class Processor(_Conditional):
    """Processor class contains a conditional data process pipeline"""

    def __init__(self, conditions, pipeline):
        super(Processor, self).__init__(conditions)
        self._pipeline = pipeline or []

    @property
    def pipeline(self):
        return self._pipeline


class RepeatMode(_Conditional):
    def __init__(self, loop_type, conditions):
        super(RepeatMode, self).__init__(conditions)
        self._type = loop_type.strip().lower()

    @property
    def type(self):
        return self._type

    @property
    def conditions(self):
        return self._conditions

    def is_once(self):
        return self._type == 'once'


class Checkpoint(object):
    """A checkpoint includes a namespace to determine the checkpoint location
    and a content defined the format of content stored in checkpoint."""

    def __init__(self, namespace, contents):
        if not contents:
            raise ValueError('Checkpoint content must not be empty')

        self._namespace = tuple(_Token(expr) for expr in namespace or [])
        self._content = {k: _Token(v) for k, v in contents.iteritems()}

    @property
    def namespace(self):
        return self._namespace

    @property
    def content(self):
        return self._content
