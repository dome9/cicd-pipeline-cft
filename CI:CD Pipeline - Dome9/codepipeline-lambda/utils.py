import json

def get_user_params(job_data,step):
    #print(job_data)
    """Decodes the JSON user parameters and validates the required properties.

    Args:
        job_data: The job data structure containing the UserParameters string which should be a valid JSON structure

    Returns:
        The JSON parameters decoded as a dictionary.

    Raises:
        Exception: The JSON can't be decoded or a property is missing.

    """
    try:
        # Get the user parameters which contain the artifact and file settings
        user_parameters = job_data['actionConfiguration']['configuration']['UserParameters']
        decoded_parameters = json.loads(user_parameters)

    except Exception as e:
        # We're expecting the user parameters to be encoded as JSON
        # so we can pass multiple values. If the JSON can't be decoded
        # then fail the job with a helpful message.
        raise Exception('UserParameters could not be decoded as JSON')

    if step == "Static_Analysis" and 'input' not in decoded_parameters:
        # Validate that the artifact name is provided, otherwise fail the job
        # with a helpful message.
        raise Exception('Your UserParameters JSON must include the artifact name')

    if step == "Static_Analysis" and 'file' not in decoded_parameters:
        # Validate that the template file is provided, otherwise fail the job
        # with a helpful message.
        raise Exception('Your UserParameters JSON must include the template file name')

    if step == "Static_Analysis" and 'output' not in decoded_parameters:
        # Validate that the output bucket name is provided, otherwise fail the job
        # with a helpful message.
        raise Exception('Your UserParameters JSON must include the output bucket')


    if step == "Live_Analysis" and 'stackName' not in decoded_parameters:
        # Validate that the output bucket name is provided, otherwise fail the job
        # with a helpful message.
        raise Exception('Your UserParameters JSON must include the stack name')

    if step == "Live_Analysis" and 'region' not in decoded_parameters:
        # Validate that the output bucket name is provided, otherwise fail the job
        # with a helpful message.
        raise Exception('Your UserParameters JSON must include the region')

    if step == "Live_Analysis" and 'awsAccount' not in decoded_parameters:
        # Validate that the output bucket name is provided, otherwise fail the job
        # with a helpful message.
        raise Exception('Your UserParameters JSON must include the AWS Account value')

    if step == "Live_Analysis" and 'bundleId' not in decoded_parameters:
        # Validate that the output bucket name is provided, otherwise fail the job
        # with a helpful message.
        raise Exception('Your UserParameters JSON must include the Dome9 bundleId')



    return decoded_parameters

