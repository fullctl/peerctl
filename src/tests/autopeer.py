from django.test import TestCase

import requests
from django_peerctl.autopeer import autopeer_url, request_valid_for_schema, AutoPeerRequestNotValid


class AutoPeer_Requests(TestCase):

    def test_list_locations(self):
        req = requests.Request("get", f"{autopeer_url}/list_locations?asn=65535")
        self.assertEqual(True, request_valid_for_schema(req.prepare()))
        
        req = requests.Request("get", f"{autopeer_url}/list_locations?asn=65535")
        self.assertEqual(False, request_valid_for_schema(req.prepare()))
        
        req = requests.Request("get", f"{autopeer_url}/list_locations?asn=65535")
        self.assertRaises(AutoPeerRequestNotValid, request_valid_for_schema(req.prepare()))


