import json

from fullctl.django.models.concrete import Task
from fullctl.django.tasks import register

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

    def run(self, from_asn, to_asn, *args, **kwargs):
        workflow = None
        try:
            workflow = AutopeerWorkflow(from_asn, to_asn, self)
            return json.dumps(workflow.request())
        except Exception as e:
            # workflow failed
            if workflow and workflow.peer_request:
                workflow.peer_request.status = "failed"
                workflow.peer_request.notes = str(e)
                workflow.peer_request.save()
            raise
