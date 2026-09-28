import qai_hub as hub

print("Checking jp0m897ng...")
profile_job = hub.get_job("jp0m897ng")
print("Status:", profile_job.get_status().code)

if profile_job.get_status().code == "FINISHED":
    profile_data = profile_job.get_profile()
    if hasattr(profile_data, 'execution_detail'):
        print("Inference Time:", profile_data.execution_detail.estimated_inference_time_us / 1000.0, "ms")
    elif hasattr(profile_data, 'estimated_inference_time_us'):
        print("Inference Time:", profile_data.estimated_inference_time_us / 1000.0, "ms")
    for k, v in profile_data.items() if isinstance(profile_data, dict) else [("dir", dir(profile_data))]:
        print(k, v)
else:
    print(profile_job.get_status())
