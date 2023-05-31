from django.conf import settings
from fullctl.django.models.concrete import Task
from fullctl.django.tasks import register

from django_peerctl.peer_session_workflow import PeerSessionWorkflow

__all__ = [
    "autopeer_url",
    "AutopeerRequest",
    "AutopeerWorkflow",
]

def autopeer_url(asn):
    """
    checks if the target network is autopeer enabled and returns its autopeer
    api url.

    Will return None if disabled or no url is present
    """

    # TODO: this should query autopeer-registry once it exsts
    return settings.AUTOPEER_NETWORKS_ENABLED.get(asn,{}).get("url")


class AutopeerWorkflow(PeerSessionWorkflow):

    """
    Peer Session setup workflow using autopeer
    """

    cc = False
    test_mode = False

    def __init__(self, my_asn, their_asn, ix_ids):
        self.net = Network.objects.get(asn=my_asn)
        self.other_net = pdbctl.Network().first(asn=their_asn)
        self.ix_ids = ix_ids or []
        self.member = pdbctl.NetworkIXLan().first(asn=their_asn)
        self.other_asn = their_asn
        self.asn = my_asn

        if not self.autopeer_url:
            raise ValueError("Autopeer is not enabled for this ASN")


    @property
    def autopeer_url(self):
        """
        checks if the target network is autopeer enabled and returns its autopeer
        api url.

        Will return None if disabled or no url is present
        """
        return autopeer_url(self.other_asn)

    def request(self, *args, **kwargs):
        
        """
        Initial autopeer request, since autopeering is all automatic and it can be
        assumed that peerctl sessions will be propagated to the devices as soon
        as they exist we can immediately progress to finalize
        """
        
        super().request()
        self.finalize()


    def config_complete(self,*args, **kwargs):
        """
        Config complete step is not needed for autopeer
        """
        return

    def finalize(self, *args, **kwargs):
        """
        PeerCtl side session objects are set up and live, create the AutopeerRequest
        Task to be processed by the autopeer api
        """
        super().finalize()
        AutopeerRequest.create_task(
            self.asn,
            self.other_asn,
            self.autopeer_url,
        )


    def progress(self, *args, **kwargs):
        return



@register
class AutopeerRequest(Task):

    """
    Autopeer request from one network to another

    Expected arguments during create task:

    - from_asn (int)
    - to_asn (int)
    """

    class Meta:
        proxy = True

    class TaskMeta:
        limit = 1

    class HandleRef:
        tag = "task_autopeer_request"

    @property
    def generate_limit_id(self):
        # as a task limiter we use the two asns delimited by a dash
        return str(self.param["args"][0])+"-"+str(self.param["args"][1])

    def run(self, from_asn, to_asn, *args, **kwargs):
        # TODO - AutoPeer request logic to remote autopeer api
        raise NotImplementedError("Autopeer request not implemented")