"""Exercise installed Jasmin protocol contracts without a broker or SMS provider."""

from io import BytesIO
from tempfile import TemporaryDirectory
from unittest import TestCase, main
from unittest.mock import patch

from jasmin.protocols.smpp.configs import SMPPClientConfig
from jasmin.protocols.smpp.factory import SMPPClientFactory
from jasmin.routing.jasminApi import Group, User
from jasmin.routing.Routables import RoutableSubmitSm
from pyasn1.codec.der.decoder import decode
from pyasn1.codec.der.encoder import encode
from pyasn1.type.univ import Integer
from smpp.pdu.operations import DeliverSM, SubmitSM
from smpp.pdu.pdu_encoding import PDUEncoder
from twisted.internet.defer import Deferred
from twisted.web.client import Agent
from txamqp.protocol import AMQClient
import certifi
import urllib3


class JasminDependencyCompatibility(TestCase):
    def setUp(self):
        self.network = patch(
            "socket.socket.connect", side_effect=AssertionError("network forbidden")
        )
        self.network.start()
        self.addCleanup(self.network.stop)

    def test_submit_and_delivery_pdu_roundtrip(self):
        for pdu_type in (SubmitSM, DeliverSM):
            with self.subTest(pdu=pdu_type.__name__):
                pdu = pdu_type(
                    seqNum=7,
                    source_addr=b"CI",
                    destination_addr=b"15555550123",
                    short_message=b"isolated fixture",
                )
                result = PDUEncoder().decode(BytesIO(PDUEncoder().encode(pdu)))
                self.assertEqual(result.seqNum, 7)
                for field in ("source_addr", "destination_addr", "short_message"):
                    self.assertEqual(result.params[field], pdu.params[field])

    def test_actual_jasmin_routable_and_credentials(self):
        user = User("ci-user", Group("ci-group"), "fixture", "fixture-password")
        pdu = SubmitSM(seqNum=1, short_message=b"isolated fixture")
        result = RoutableSubmitSm(pdu, user)
        self.assertEqual(result.user.uid, "ci-user")
        self.assertIs(result.pdu, pdu)

    def test_smpp_factory_preserves_owned_configuration(self):
        config = SMPPClientConfig(id="ci-source", host="127.0.0.1", port=2775)
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        config.log_file = directory.name + "/smpp.log"
        factory = SMPPClientFactory(config)
        self.assertIs(factory.config, config)
        self.assertTrue(callable(factory.buildProtocol))

    def test_twisted_deferred_callback_and_error_contract(self):
        values = []
        deferred = Deferred()
        deferred.addCallback(lambda value: value + 1)
        deferred.addCallback(values.append)
        deferred.callback(41)
        self.assertEqual(values, [42])
        failures = []
        deferred = Deferred()
        deferred.addErrback(lambda failure: failures.append(failure.type))
        deferred.errback(ValueError("isolated fixture"))
        self.assertEqual(failures, [ValueError])

    def test_asn1_binary_roundtrip(self):
        value, remainder = decode(encode(Integer(42)))
        self.assertEqual(int(value), 42)
        self.assertEqual(remainder, b"")

    def test_amqp_and_twisted_http_import_contract(self):
        self.assertTrue(callable(AMQClient))
        self.assertTrue(callable(Agent))

    def test_tls_bundle_and_http_response_contract(self):
        with open(certifi.where(), "rb") as bundle:
            self.assertIn(b"BEGIN CERTIFICATE", bundle.read())
        response = urllib3.response.HTTPResponse(body=b"isolated fixture", preload_content=True)
        self.assertEqual(response.data, b"isolated fixture")


if __name__ == "__main__":
    main()
