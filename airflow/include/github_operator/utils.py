def result_processor_custom_github_operator(res):
    print(res.status_code)
    print(res.raw_headers)
    print(res.raw_data)
    print(res.last_modified_datetime)
    return res.raw_data, res.last_modified_datetime
