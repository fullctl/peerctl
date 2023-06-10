import json

from fullctl.django.models.concrete import Task
from fullctl.django.tasks import register

import django_peerctl.models.peerctl as models
from django_peerctl.autopeer.workflow import AutopeerWorkflow

__all__ = [
    "AutopeerRequest",
]


@register
class AutopeerRequest(Task):

    """
    Autopeer request from one network to another

    Expected arguments during create task:

    - asn (int)
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
        return str(self.asn) + "-" + str(self.to_asn)

    @property
    def asn(self):
        return self.param["args"][0]

    @property
    def to_asn(self):
        return self.param["args"][1]

    @property
    def peer_request(self):
        if hasattr(self, "_peer_request"):
            return self._peer_request

        peer_request_id = self.param["kwargs"].get("peer_request_id")

        try:
            self._peer_request = models.PeerRequest.objects.get(id=peer_request_id)
        except models.PeerRequest.DoesNotExist:
            self._peer_request = None

        return self._peer_request

    def run(self, from_asn, to_asn, *args, **kwargs):
        workflow = None
        try:
            workflow = AutopeerWorkflow(
                from_asn, to_asn, self, peer_request=self.peer_request
            )
            if self.peer_request:
                self.peer_request.task = self
                self.peer_request.save()
            return json.dumps(workflow.request())
        except Exception as e:
            # workflow failed
            if workflow and workflow.peer_request:
                workflow.peer_request.status = "failed"
                workflow.peer_request.notes = str(e)
                workflow.peer_request.save()
            raise


    def _fail(self, error):
        super()._fail(error)

        if self.peer_request:

            # when the task fails, we need to update the peer request
            # and all the locations to failed as well

            self.peer_request.status = "failed"
            self.peer_request.locations.all().update(status="failed")
            self.peer_request.notes = "Task failed"
            self.peer_request.save()