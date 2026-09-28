import qai_hub as hub
import sys

target_model_id = 'mn752ppom'

print(f"Retrieving target model: {target_model_id}")
target_model = hub.get_model(target_model_id)
device = hub.Device("Snapdragon X Elite CRD")

print("Submitting profile job...")
profile_job = hub.submit_profile_job(
    model=target_model,
    device=device,
    name="whispervault-ner-profiling"
)
print(f"Profile job submitted: {profile_job.job_id}")
print(f"Profile URL: {profile_job.url}")

profile_job.wait()

profile_res = profile_job.get_status().code
print("Profile status:", profile_res)

try:
    results = profile_job.download_profile()
    print("Profile Results downloaded.")
    print("NPU Summary:")
    print(results)
except Exception as e:
    print("Failed to download profile:", e)
