import qai_hub as hub
import json

job_id = 'jpxl8zk8p'
profile_job = hub.get_job(job_id)
print("Device:", profile_job.device.name)
