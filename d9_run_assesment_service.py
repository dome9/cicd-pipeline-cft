import requests


class AssessmentExecutor:
    def __init__(self, cloud_account, d9_cloud_account, d9_secret, d9_key, region, relevant_resource_ids=dict()):
        self.cloud_account = cloud_account
        self.d9_secret = d9_secret
        self.d9_key = d9_key
        self.region = region
        self.d9_cloud_account = d9_cloud_account
        self.relevant_resource_ids = relevant_resource_ids

    def run_assessment(self, bundel_id):
        print("**** Start Assessment execution ****")
        result = self.__execute_assemssent(bundel_id)

        return self.analyze_assesment_result(result)

    def __execute_assemssent(self, bundel_id):
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

        body = {
            "id": bundel_id,
            # "name": "test",
            # "description":
            "cloudAccountId": self.d9_cloud_account,
            "region": self.region,
            "cloudAccountType": "Aws"
        }

        r = requests.post('https://api.dome9.com/v2/assessment/bundleV2', params=body, headers=headers,
                          auth=(self.d9_key, self.d9_secret))

        print(r)
        print(r.json())

    # Analyze the assessment execution result and return the assets id and types for all the assets the fail in
    # each rule execution
    def analyze_assessment_result(self, assessment_result):

        if len(self.relevant_resource_ids) > 0:

            # Create a flat list of all the resources from the specific stack supported by dome9
            flat_resource_ids = [resource_id for resource_type in self.relevant_resource_ids for resource_id in
                                 self.relevant_resource_ids[resource_type]]
            # for all the failed tests
            for test in [tst for tst in assessment_result["tests"] if not tst["testPassed"]]:
                # for each failed asset
                for asset in [ast for ast in test["entityResults"] if ast["isRelevant"] and not ast["isValid"]]:
                    if asset['testObj']['id'] in  flat_resource_ids:
                        print('The Resource {} is not valid for Rule - {} based onDome9 Compliance assessment '
                              'execution '.format(asset['testObj']['id'], test['rule']['name']))

            print("**** Assessment Analyzing was Done ****")





#exec_service = AssessmentExecutor("766426469869", "b7157b93-04c1-4eb3-9c90-da2e842df4ac", '98ysuq9jd9dwktciaayf8y8q', 'd27f09d4-9484-4502-80b7-cb04de63eef5', 'us-west-2')

#exec_service.run_assessment(-15)
