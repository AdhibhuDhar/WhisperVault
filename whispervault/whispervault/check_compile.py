import qai_hub as hub

print("Checking jp2rqzy6g...")
compile_job = hub.get_job("jp2rqzy6g")
print("Status:", compile_job.get_status().code)

if compile_job.get_status().code == "FINISHED":
    print(compile_job.get_target_model())
else:
    print(compile_job.get_status())
