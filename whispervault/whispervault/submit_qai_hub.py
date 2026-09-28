import qai_hub as hub
import time

model_id = 'mmxjl11eq'

print(f"Retrieving model: {model_id}")
model = hub.get_model(model_id)

print("Submitting compile job...")
device = hub.Device("Snapdragon X Elite CRD")

compile_job = hub.submit_compile_job(
    model=model,
    device=device,
    input_specs={
        'input_ids': ((1, 512), 'int64'),
        'attention_mask': ((1, 512), 'int64')
    },
    name="whispervault-ner-compilation"
)
print(f"Compile job submitted: {compile_job.job_id}")
print(f"Compile URL: {compile_job.url}")
print("Waiting for compile job...")
compile_job.wait()

print("Compile status:", compile_job.get_status().code)

target_model = compile_job.get_target_model()
if target_model is None:
    print("Compile job failed, stopping.")
    exit(1)

print("Submitting profile job...")
profile_job = hub.submit_profile_job(
    model=target_model,
    device=device,
    name="whispervault-ner-profiling"
)
print(f"Profile job submitted: {profile_job.job_id}")
print(f"Profile URL: {profile_job.url}")
print("Waiting for profile job...")
profile_job.wait()

profile_res = profile_job.get_status().code
print("Profile status:", profile_res)

try:
    results = profile_job.download_profile()
    print("Profile Results downloaded.")
except Exception as e:
    print("Failed to download profile:", e)
