
import responder

from ddtrace.contrib.responder.patch import patch, unpatch
from ddtrace.pin import Pin

from ...utils.tracer import DummyTracer


class TestResponder(object):

    def setup_method(self):
        patch()

    def teardown_method(self):
        unpatch()

    def test_200(self):
        patch()
        tracer, api = _make_test_api()
        resp = api.session().get("/login")

        assert resp.ok
        assert resp.status_code == 200

        spans = tracer.writer.pop()
        assert len(spans) == 1
        s = spans[0]
        assert s.name == 'responder.request'
        assert s.get_tag('http.status_code') == '200'
        assert s.get_tag('http.method') == 'GET'

    def test_routing(self):
        patch()
        tracer, api = _make_test_api()
        resp = api.session().get("/home/wayne")

        assert resp.ok
        assert resp.status_code == 200
        assert resp.text == 'hello wayne'

        spans = tracer.writer.pop()
        assert len(spans) == 1
        s = spans[0]
        assert s.name == 'responder.request'
        assert s.resource == '/home/{user}'
        assert s.get_tag('http.status_code') == '200'
        assert s.get_tag('http.method') == 'GET'


    def test_exception(self):
        tracer, api = _make_test_api()

        # don't raise exceptions so we can test status codes, etc.
        client = responder.api.TestClient(api, raise_server_exceptions=False)

        resp = client.get("/exception")

        assert not resp.ok
        assert resp.status_code == 500

        spans = tracer.writer.pop()
        assert len(spans) == 1
        s = spans[0]
        assert s.name == 'responder.request'
        assert s.get_tag('http.status_code') == '500'
        assert s.get_tag('http.method') == 'GET'


    def test_tracing_http_headers(self):
        tracer, api = _make_test_api()
        resp = api.session().get("/login", headers={
            "x-datadog-trace-id":"123",
            "x-datadog-parent-id":"456",
        })

        assert resp.ok
        assert resp.status_code == 200

        spans = tracer.writer.pop()
        assert len(spans) == 1
        s = spans[0]
        assert s.name == 'responder.request'
        assert s.resource == '/login'
        assert s.trace_id == 123
        assert s.parent_id == 456


def _make_test_api():
    tracer = DummyTracer()
    api = responder.API()

    Pin.override(api, tracer=tracer)

    @api.route("/login")
    def login(req, resp):
        resp.text = "asdf"

    @api.route("/home/{user}")
    def home(req, resp, *, user):
        resp.text = f"hello {user}"


    @api.route("/exception")
    def exception(req, resp):
        raise FakeError("ohno")

    return tracer, api

class FakeError(Exception): pass
