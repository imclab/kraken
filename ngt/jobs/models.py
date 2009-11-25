from django.db import models
import os, time, hashlib, datetime
import uuid
from ngt.messaging.messagebus import MessageBus
from ngt.assets.models import Asset, DATA_ROOT
import json
from ngt import protocols
from ngt.protocols import protobuf

messagebus = MessageBus()

messagebus.channel.exchange_declare(exchange="Job_Exchange", type="direct", durable=True, auto_delete=False,)
messagebus.channel.queue_declare(queue='reaper.generic', auto_delete=False)
messagebus.channel.queue_bind(queue='reaper.generic', exchange='Job_Exchange', routing_key='reaper.generic')
"""
# RPC Service to dispatch
REPLY_QUEUE_NAME = 'jobmodels'
JOB_EXCHANGE_NAME = 'Job_Exchange'
chan.queue_declare(queue=self.REPLY_QUEUE_NAME, durable=False, auto_delete=True)
chan.queue_bind(self.REPLY_QUEUE_NAME, self.JOB_EXCHANGE_NAME, routing_key=self.REPLY_QUEUE_NAME)
dispatch_rpc_channel = protocols.rpc_services.RpcChannel(self.JOB_EXCHANGE_NAME, self.REPLY_QUEUE_NAME, 'dispatch')
dispatch = protobuf.DispatchCommandService_Stub(dispatch_rpc_channel)
amqp_rpc_controller = protocols.rpc_services.AmqpRpcController()
"""

class Job(models.Model):
    uuid = models.CharField(max_length=32, null=True)
    jobset = models.ForeignKey('JobSet', related_name="jobs")
    command = models.CharField(max_length=64)
    arguments = models.TextField(null=True) # an array seriaized as json
    status = models.CharField(max_length=32, default='new')
    processor = models.CharField(max_length=32, null=True, default=None)
    assets = models.ManyToManyField(Asset, related_name='jobs')
    output = models.TextField(null=True)
    
    creates_new_asset = models.BooleanField(default=True)
    outfile_argument_index = medels.SmallIntegerField(default=1) # index of the output filename in the argument list.  Used to generate output asset records.
    output_assets = models.ManyToManyField(Asset, related_name='jobs')
    
    def _generate_uuid(self):
        '''Returns a unique job ID that is the MD5 hash of the local
        hostname, the local time of day, and the command & arguments for this job.'''
        return uuid.uuid1().hex
    
    def __unicode__(self):
        return self.uuid

    @property
    def command_string(self):
        return self.command + ' ' + ' '.join(json.loads(self.arguments))
    
    def enqueue(self):
        cmd = {
            'uuid': self.uuid,
            'command': self.command,
            'args': json.loads(self.arguments)
        }
        message_body = protocols.pack(protobuf.Command, cmd)
        self.status = 'queued'
        self.save()
        messagebus.publish(message_body, exchange='Job_Exchange', routing_key='reaper.generic') #routing key is the name of the intended reaper type
        print "Enqueued %s" % self.uuid
        
    def spawn_output_asset(self):
        """ Creates a new asset record for the job's output file. 
            Assumes that the output filename will be the second parameter in the output list
        """
        assert self.assets.count() == 1
        asset_o = self.assets.all()[0]
        asset_n = copy(asset_o)
        asset_n.id = None
        asset_n.is_original = False
        args = json.loads(self.arguments)
        asset_n.relative_file_path = args[self.outfile_argument_index].replace(DATA_ROOT,'')
        assert os.path.exists(asset_n.file_path)
        asset_n.class_label = self.jobset.output_asset_label or self.jobset.name
        asset_n.save()
        self.output_assets.add(asset_n)
        asset_n.parents.add(asset_o)
        
    
    
def set_uuid(instance, **kwargs):
    if not instance.uuid:
        instance.uuid = instance._generate_uuid()
models.signals.pre_save.connect(set_uuid, sender=Job)

class JobSet(models.Model):
    name = models.CharField(max_length=256)
    assets = models.ManyToManyField(Asset) # this collection of assets can be used to populate jobs
    #jobs = models.ManyToManyField(Job, editable=False) # now a foreign key in the Job model
    status = models.CharField(max_length=32, default='new')
    command = models.CharField(max_length=64)
    active = models.BooleanField(default=False)
    
    output_asset_label = models.CharField(max_length=256, null=True, default=None) # this is the label that will be applied to assets generated by jobs in this set
    
    def __unicode__(self):
        return self.name
        
    def simple_populate(self):
        """Create one-parameter jobs for each of this batch's assets"""
        print "Creating jobs for %s" % str(self.assets.all())
        for asset in self.assets.all():
            print "About to create a job for %s" % str(asset)
            self.jobs.create(
                command=self.command, 
                arguments='["%s"]' % asset.file_path, #json-decodable lists of one
            )
    
    def execute(self):
        #self.simple_populate()
        self.status = "dispatched"
        for job in self.jobs.filter(status='new'):
            job.enqueue()
            


"""
I'd like jobs to be populated from the JobSet's properties by a post-save signal...
But this won't work because the related objects in jobbatch.assests don't get created until after the post_save signal has fired.

def populate_jobs(instance, created, **kwargs):
    print "populate_jobs fired: %s" % str(created)
    if created:
        instance.simple_populate() #just one asset per job, for now.
models.signals.post_save.connect(populate_jobs, sender=JobSet)
"""
