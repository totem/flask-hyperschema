"""
Module that provides decorators for hypermedia handling and Schema validation
using Json HyperSchema and Json Schema.
"""

import functools
import glob
import json
import os
import traceback
from flask import make_response, request, url_for, Response
import flask
from flask.views import MethodView
from jsonschema import validate, ValidationError, SchemaError
from ordered_set import OrderedSet
from repoze.lru import lru_cache
from werkzeug.exceptions import UnsupportedMediaType, NotAcceptable

SCHEMA_PATH = os.getenv('SCHEMA_PATH', './schemas')
SCHEMA_CACHE_MAX_SIZE = int(os.getenv('SCHEMA_CACHE_MAX_SIZE', '50'))
MIME_JSON = 'application/json'


class HyperMedia:
    """
    Class wrapping methods for hypermedia
    """

    def __init__(self, schema_cache_size=SCHEMA_CACHE_MAX_SIZE,
                 schema_path=SCHEMA_PATH, base_url=None):
        """
        Constructor

        :keyword schema_cache_size: Cache size for storing schema
          (defaults to 50)
        :type schema_cache_size: str
        :keyword schema_path: File Path where schemas are stored
          (defaults to ./schemas)
        :type schema_path: str
        :keyword base_url: Base url for loading schemas
        :type base_url: str
        """
        self.schema_cache_size = schema_cache_size
        self.load_schema = self._load_schema()
        self.get_all_schemas = self._get_all_schemas()
        self.schema_path = schema_path
        self.base_url = base_url

    def _load_schema(self):
        """
        Creates the load schema function with cache decorator. Size of the
        cache is read from property schema_cache_size

        :return: load schema function
        :rtype: function
        """
        @lru_cache(self.schema_cache_size)
        def load_schema(base_url, schema_name):
            """
            Helper function that loads given schema

            :param schema_name:
            :return:
            """
            fname = '%s/%s.json' % (self.schema_path, schema_name)
            with open(fname) as file:
                data = file.read().replace(
                    '${base_url}', base_url or self.base_url)
                return json.loads(data)
        return load_schema

    def _get_all_schemas(self):
        """
        Creates get all schemas function (to fetch all available schemas).

        :return: get_all_schemas function
        :rtype: function
        """
        @lru_cache(1)
        def get_all_schemas():
            return [os.path.splitext(os.path.basename(filepath))[0]
                    for filepath in glob.glob('%s/*.json' % self.schema_path)]
        return get_all_schemas

    def consumes(self, type_mappings):
        """
        Wrapper that finds matches the content with one of supported type and
        performs a json schema validation for the type.

        :param type_mappings: Dictionary of (content type, schema name)
        :return: decorated function
        """
        def decorated(fn):
            @functools.wraps(fn)
            def wrapper(*args, **kwargs):
                if request.mimetype not in type_mappings:
                    raise UnsupportedMediaType()
                if request.mimetype.lower() == \
                        'application/x-www-form-urlencoded':
                    data = json.loads(request.form['payload'])
                else:
                    data = json.loads(request.data.decode('utf-8'))
                schema_name = type_mappings.get(request.mimetype)
                if schema_name:
                    schema = self.load_schema(
                        self.base_url or request.url_root[:-1],
                        schema_name)
                    validate(data, schema)
                kwargs.setdefault('request_mimetype', request.mimetype)
                kwargs.setdefault('request_data', data)
                return fn(*args, **kwargs)
            return wrapper
        return decorated

    @staticmethod
    def produces(type_mappings, default=MIME_JSON, set_mimetype=True,
                 strict=False):
        """
        Wrapper that does content negotiation based on accept headers and
        applies hyperschema to the response.
        It passes the negotiated header to the wrapped method. Currently it
        does a very basic negotitation. In future it can be modified to do full
        content negotiation.

        :param type_mappings: Dictionary of (content type, hyperschema name)
        :type type_mappings: dict
        :param default: Default Mime Type if no Accept header is specified.
        :type default: str
        :param set_mimetype: If True: the mimetype is automatically set for
            response .
        :type set_mimetype: bool
        :keyword strict: Boolean parameter specifying whether to use strict
            negotiation. If False, default mimetype is used if negotiation
            fails else 406 response is returned.
        :type strict: bool
        :return: decorated function
        """
        def decorated(fn):
            @functools.wraps(fn)
            def wrapper(*args, **kwargs):
                requested = OrderedSet(request.accept_mimetypes.values())
                defined = type_mappings.keys()
                supported = requested & defined
                if len(requested) == 0 or next(iter(requested)) == '*/*':
                    mimetype = default
                elif len(supported) == 0:
                    if strict:
                        raise NotAcceptable()
                    else:
                        mimetype = default
                else:
                    mimetype = next(iter(supported))
                kwargs.setdefault('accept_mimetype', mimetype)
                resp = make_response(fn(*args, **kwargs))

                if set_mimetype:
                    resp.headers['Content-Type'] = mimetype
                hyperschema = type_mappings[mimetype]
                if hyperschema:
                    resp.headers['Link'] = \
                        '<%s#>; rel="describedBy"' % url_for(
                            '.schemas', schema_id=hyperschema, _external=True)
                return resp
            return wrapper
        return decorated

    def register_schema_api(self, flask_app, schema_uri='/schemas'):
        """
        Registers schema API with flask

        :param flask_app: Flask application
        :type flask_app: Flask
        :keyword schema_uri: URI for Schema endpoint. Defaults to '/schemas'
        :type schema_uri: str
        :return: self instance
        :rtype: HyperMedia
        """
        schema_view = SchemaApi.as_view('schemas')
        SchemaApi.hypermedia = self
        uris = ['%s/<string:schema_id>' % schema_uri, schema_uri,
                schema_uri+'/']
        for uri in uris:
            flask_app.add_url_rule(uri, view_func=schema_view, methods=['GET'])
        return self

    def register_error_handlers(self, flask_app):
        """
        Registers error handlers for schema with flask application.

        :param flask_app: Flask application
        :type flask_app: Flask
        :return: self instance
        :rtype: HyperMedia
        """

        @flask_app.errorhandler(ValidationError)
        def validation_error(error):
            return self._as_flask_error(error, **{
                'code': 'VALIDATION',
                'message': error.message,
                'details': self._get_error_details(error),
                'status': 400,
                })

        @flask_app.errorhandler(SchemaError)
        def schema_error(error):
            return self._as_flask_error(error, **{
                'code': 'SCHEMA_ERROR',
                'message': error.message,
                'details': self._get_error_details(error),
                'status': 500,
                'traceback': traceback.format_exc()
            })
        return self

    @staticmethod
    def _as_flask_error(error, message=None, details=None, traceback=None,
                        status=500, code='INTERNAL'):
        return flask.jsonify({
            'path': request.path,
            'url': request.url,
            'method': request.method,
            'message': message or str(error),
            'details': details,
            'traceback': traceback,
            'status': status,
            'code': code
        }), status

    @staticmethod
    def _get_error_details(error):
        return {
            'schema': error.schema,
            'schema-path': '/'.join(error.schema_path)
        }


class SchemaApi(MethodView):
    """
    Root API
    """

    hypermedia = None

    def get(self, schema_id=None):
        """
        Gets the schema by ID if schema_id is given or lists all schemas

        :param schema_id: id/name for the schema. If None, all schemas are
            listed
        :type schema_id: str
        :return: Flask Json Response containing version.
        :rtype: flask.Response
        """
        if schema_id:
            schema = self.hypermedia.load_schema(request.url_root[:-1],
                                                 schema_id)
            if not schema:
                return flask.abort(404)
            return flask.jsonify(schema)

        else:
            schema_list = self.hypermedia.get_all_schemas()
            return Response(json.dumps(schema_list), mimetype=MIME_JSON)
