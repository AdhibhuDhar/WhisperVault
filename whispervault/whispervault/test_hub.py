import qai_hub as hub

print("Waiting for compile job jp2rqzy6g...")
compile_job = hub.get_job("jp2rqzy6g")
compile_job.wait()

print("Waiting for profile job jpyoky305...")
profile_job = hub.get_job("jpyoky305")
profile_job.wait()

print("Profile Job Finished:", profile_job.get_status().code)

if profile_job.get_status().code == "FINISHED":
    profile_data = profile_job.get_profile()
    
    print("\n--- PERFORMANCE METRICS ---")
    if hasattr(profile_data, 'execution_detail'):
        print("Inference Time:", profile_data.execution_detail.estimated_inference_time_us / 1000.0, "ms")
    elif hasattr(profile_data, 'estimated_inference_time_us'):
        print("Inference Time:", profile_data.estimated_inference_time_us / 1000.0, "ms")
    else:
        print(dir(profile_data))
        
    print("\nDetails:")
    for key, value in profile_data.items() if isinstance(profile_data, dict) else [("dir", dir(profile_data))]:
        print(key, value)
else:
    print(profile_job.get_status())
