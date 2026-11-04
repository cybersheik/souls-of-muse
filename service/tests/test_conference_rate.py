"""Integrated three-account signalling must not consume login/message quota."""
import unittest
from fastapi.testclient import TestClient
from service.tests import test_group_participants as fixtures


class ConferenceRate(unittest.TestCase):
    def fixture(self):
        f=fixtures.GroupParticipants();f.setUpClass();f.setUp();return f

    def test_three_people_can_poll_and_rejoin_without_starving_normal_session_requests(self):
        f=self.fixture();route=f.group();m=f.clients['M'];self.assertEqual(m.post(route+'/start').status_code,200)
        generations={}
        for name in ['M','A','B']:
            c=f.clients[name];self.assertEqual(c.post(route+'/join').status_code,200)
            response=c.post(route+'/conference/join',json={});self.assertEqual(response.status_code,200,response.text)
            generations[name]=response.json()['connection_id']
        for _ in range(125):
            for name in ['M','A','B']:
                c=f.clients[name];response=c.get(route+'/conference/events',params={'connection_id':generations[name],'after':0})
                self.assertEqual(response.status_code,200,response.text)
        for name in ['M','A','B']:
            self.assertEqual(f.clients[name].get('/api/harness/sessions').status_code,200)
            self.assertEqual(f.clients[name].post(route+'/conference/leave',json={'connection_id':generations[name]}).status_code,200)
            self.assertEqual(f.clients[name].post(route+'/conference/join',json={}).status_code,200)

    def test_unauthenticated_requests_cannot_gain_the_authenticated_conference_quota(self):
        f=self.fixture();client=TestClient(f.site)
        statuses=[client.get('/api/harness/sessions/unknown/conference/events').status_code for _ in range(125)]
        self.assertIn(429,statuses);self.assertEqual(statuses[-1],429)

    def test_three_authenticated_people_share_an_ip_without_sharing_a_read_quota(self):
        f=self.fixture();route=f.group()
        # A three-person lesson refreshes three resources per person every 5s.
        # Include an ordinary action margin within each participant's limit.
        for _ in range(55):
            for name in ['M','A','B']:
                response=f.clients[name].get(route)
                self.assertEqual(response.status_code,200,response.text)
        # The allowance stays bounded for a single signed-in account.
        statuses=[f.clients['M'].get(route).status_code for _ in range(125)]
        self.assertEqual(statuses[-1],429)
