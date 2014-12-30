import json
from flask import Flask, Response
from jsonschema.exceptions import ValidationError, SchemaError
from mock import Mock, patch
from nose.tools import eq_
from hyperschema.hypermedia import HyperMedia, MIME_JSON

__author__ = 'sukrit'

MOCK_SCHEMA = {
    '$schema': 'http://json-schema.org/draft-04/hyper-schema#',
    'type': 'object'
}

SCHEMA_TEST = 'schema-test'
MIME_TEST = 'application/vnd.test+json'
MIME_FORM_URL_ENC = 'application/x-www-form-urlencoded'


class TestSchemaApi:
    """
    Tests for SchemaApi
    """

    def setup(self):
        self.app = Flask(__name__)
        self.hypermedia = HyperMedia()
        self.hypermedia.register_schema_api(self.app)
        self.hypermedia.load_schema = Mock()
        self.hypermedia.get_all_schemas = Mock()
        self.client = self.app.test_client(False)

    def test_get_existing_schema(self):
        # Given: Existing schema
        self.hypermedia.load_schema.return_value = MOCK_SCHEMA

        # When I get schema by given id
        resp = self.client.get('/schemas/schema1')

        # Expected schema is returned
        eq_(resp.status_code, 200)
        eq_(resp.mimetype, MIME_JSON)
        eq_(MOCK_SCHEMA, json.loads(resp.data.decode()))
        self.hypermedia.load_schema.assert_called_once_with(
            'http://localhost', 'schema1')

    def test_get_schema_when_not_found(self):
        # Given: Existing schema
        self.hypermedia.load_schema.return_value = None

        # When I get schema by given id
        resp = self.client.get('/schemas/schema1')

        # Expected schema is returned
        eq_(resp.status_code, 404)

    def test_should_list_schemas(self):
        # Given: Existing schemas
        schema_list = ['schema1', 'schema2']
        self.hypermedia.get_all_schemas.return_value = schema_list

        # When I get all schemas
        resp = self.client.get('/schemas')

        # Schema list is returned
        eq_(resp.status_code, 200)
        eq_(resp.mimetype, MIME_JSON)
        eq_(json.loads(resp.data.decode()), schema_list)


class TestProduces:
    """
    Tests for wrapper produces
    """
    def setup(self):
        self.app = Flask(__name__)
        self.client = self.app.test_client(False)
        self.hypermedia = HyperMedia()
        self.hypermedia.register_schema_api(self.app)

    def _create_mock_endpoint(self, type_mappings, default=MIME_TEST):
        @self.app.route('/')
        @HyperMedia.produces(type_mappings, default=default)
        def test_endpoint(**kwargs):
            return Response('')
        return test_endpoint

    def test_produces_with_no_accept_headers(self):
        # Given: A test endpoint
        self._create_mock_endpoint({
            MIME_TEST: SCHEMA_TEST
        })

        # When I access the endpoint with no accept headers
        resp = self.client.get('/')

        # Then: Expected status and content type is returned
        eq_(resp.status_code, 200)
        eq_(resp.mimetype, MIME_TEST)
        eq_(resp.headers['Link'],
            '<http://localhost/schemas/schema-test#>; rel="describedBy"')

    def test_produces_with_all_headers(self):
        # Given: A test endpoint
        self._create_mock_endpoint({
            MIME_TEST: SCHEMA_TEST
        })

        # When I access the endpoint with no accept headers
        resp = self.client.get('/',
                               headers=[('Accept', '*/*')])

        # Then: Expected status and content type is returned
        eq_(resp.status_code, 200)
        eq_(resp.mimetype, MIME_TEST)
        eq_(resp.headers['Link'],
            '<http://localhost/schemas/schema-test#>; rel="describedBy"')

    def test_produces_with_unsupported_header(self):
        # Given: A test endpoint
        self._create_mock_endpoint({
            MIME_TEST: SCHEMA_TEST
        })

        # When I access the endpoint with no accept headers
        resp = self.client.get('/',
                               headers=[('Accept', 'application/unsupported')])

        # Then: Expected status and content type is returned
        eq_(resp.status_code, 406)

    def test_produces_with_headers_match(self):
        # Given: A test endpoint
        self._create_mock_endpoint({
            MIME_TEST: SCHEMA_TEST,
            MIME_JSON: SCHEMA_TEST,
        })

        # When I access the endpoint with no accept headers
        resp = self.client.get(
            '/', headers=[
                ('Accept', 'application/unsupported+json,'
                           'application/vnd.test+json'
                 ),
            ])

        # Then: Expected status and content type is returned
        eq_(resp.status_code, 200)
        eq_(resp.mimetype, MIME_TEST)
        eq_(resp.headers['Link'],
            '<http://localhost/schemas/schema-test#>; rel="describedBy"')


class TestConsumes:
    """
    Tests for wrapper consumes
    """
    def setup(self):
        self.app = Flask(__name__)
        self.client = self.app.test_client(False)
        self.hypermedia = HyperMedia()
        self.hypermedia.load_schema = Mock()
        self.hypermedia.register_schema_api(self.app)

    def _create_mock_endpoint(self, type_mappings):
        @self.app.route('/', methods=['POST'])
        @self.hypermedia.consumes(type_mappings)
        def test_endpoint(request_data=None, request_mimetype=MIME_TEST):
            return Response(json.dumps(request_data),
                            mimetype=request_mimetype)
        return test_endpoint

    def test_consumes_unsupported_endpoint(self):
        # Given: A test endpoint
        self._create_mock_endpoint({
            MIME_TEST: SCHEMA_TEST
        })

        # When: I access the endpoint with unsupported content type
        resp = self.client.post(
            '/', headers=[('Content-Type', 'application/unsupported+json')])
        eq_(resp.status_code, 415)

    @patch('hyperschema.hypermedia.validate')
    def test_consumes_with_suppported_endpoint(self, mock_validate):
        # Given: A test endpoint
        self._create_mock_endpoint({
            MIME_TEST: SCHEMA_TEST
        })

        data = {
            'key': 'value'
        }

        # When: I access the endpoint with unsupported content type
        resp = self.client.post(
            '/', data=json.dumps(data), headers=[('Content-Type', MIME_TEST)])
        eq_(resp.status_code, 200)
        eq_(resp.mimetype, MIME_TEST)
        eq_(json.loads(resp.data.decode()), data)

    @patch('hyperschema.hypermedia.validate')
    def test_consumes_with_suppported_url_encoded_endpoint(self,
                                                           mock_validate):
        # Given: A test endpoint
        self._create_mock_endpoint({
            MIME_FORM_URL_ENC: SCHEMA_TEST
        })

        data = {
            'key': 'value'
        }

        form_data = {
            'payload': json.dumps(data)
        }

        # When: I access the endpoint with unsupported content type
        resp = self.client.post(
            '/', data=form_data, headers=[('Content-Type', MIME_FORM_URL_ENC)])
        eq_(resp.status_code, 200)
        eq_(resp.mimetype, MIME_FORM_URL_ENC)
        eq_(json.loads(resp.data.decode()), data)


class TestErrorHandlers:
    """
    Tests  Schema Error handlers for HyperSchema
    """

    def setup(self):
        self.app = Flask(__name__)
        self.client = self.app.test_client(False)
        self.hypermedia = HyperMedia()
        self.hypermedia.register_error_handlers(self.app)

    def _create_mock_endpoint(self, error):
        @self.app.route('/')
        def test_endpoint():
            raise error
        return test_endpoint

    def test_validation_error(self):
        # given: Endpoint that returns validation error
        error = ValidationError(message='Mock Message', schema=MOCK_SCHEMA,
                                schema_path='/properties/mock')
        self._create_mock_endpoint(error)

        # When: I access test endpoint
        resp = self.client.get('/')

        # Then: Expected error response is returned
        eq_(resp.status_code, 400)

    def test_schema_error(self):
        # given: Endpoint that returns validation error
        error = SchemaError(message='Mock Message', schema=MOCK_SCHEMA,
                            schema_path='/properties/mock')
        self._create_mock_endpoint(error)

        # When: I access test endpoint
        resp = self.client.get('/')

        # Then: Expected error response is returned
        eq_(resp.status_code, 500)
