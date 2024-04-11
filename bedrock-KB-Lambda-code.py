import json
import logging
import base64
import os
import boto3
from botocore.exceptions import ClientError
import requests

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize a Boto3 client for Bedrock
bedrock = boto3.client(service_name='bedrock-runtime')
bedrock_client = boto3.client(service_name='bedrock-agent-runtime')

def invoke_bedrock_model(prompt):
    try:
        # Format the prompt
        formatted_prompt = "\n\nHuman: " + prompt + "\n\nAssistant:"
        body = {
            "modelId": "anthropic.claude-v2:1",
            "contentType": "application/json",
            "accept": "*/*",
            "body": {
                "prompt": formatted_prompt,
                "max_tokens_to_sample": 10000,
                "temperature": 0,
                "top_k": 250,
                "top_p": 1,
                "stop_sequences": ["\n\nAssistant:"],
                "anthropic_version": "bedrock-2023-05-31"
            }
        }

        # Invoke the Bedrock model
        response = bedrock.invoke_model(
            body=json.dumps(body['body']),
            modelId=body['modelId'],
            contentType=body['contentType'],
            accept=body['accept']
        )

        # Parse the response from Bedrock
        response_body = json.loads(response['body'].read())
        logger.info(f"Response from Bedrock model: {response_body}")
        return response_body.get('completion', '').strip()
    except ClientError as e:
        logger.error("An error occurred while invoking Bedrock model: %s", e, exc_info=True)
        raise

def create_and_commit_file(repo_owner, repo_name, path, token, commit_message, content):
    # Construct the URL for GitHub API
    url = f'https://api.github.com/repos/{repo_owner}/{repo_name}/contents/{path}'
    # Headers for GitHub API
    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json',
    }
    # Encode the content to base64
    encoded_content = base64.b64encode(content.encode('utf-8')).decode('utf-8')
    # Prepare the payload for the GitHub API request
    data = {
        'message': commit_message,
        'content': encoded_content,
    }
    # Make the PUT request to GitHub API to create the file
    response = requests.put(url, headers=headers, data=json.dumps(data), timeout=20)
    # Check the response from GitHub
    if response.status_code in [200, 201]:
        logger.info(f'{path} successfully created/updated in GitHub repo.')
    else:
        logger.error(f'Failed to create/update {path}', response.json())
        response.raise_for_status()

    
def retrieve_module_definitions(knowledge_base_id, model_arn, services):
    query_text = f"Retrieve Terraform module sources for AWS services: {', '.join(services)}"
    try:
        response = bedrock_client.retrieve_and_generate(
            input={
                'text': query_text
            },
            retrieveAndGenerateConfiguration={
                'type': 'KNOWLEDGE_BASE',
                'knowledgeBaseConfiguration': {
                    'knowledgeBaseId': knowledge_base_id,
                    'modelArn': model_arn
                }
            }
        )
        
    # Extracting the text from the response
        print("KB Response 1:", response) 
        response_text = response['output']['text']
        print("KB Response:", response_text)  # Print the response text

        # Assuming the response text contains a JSON string with module definitions
        module_definitions = response_text #json.loads(response_text)
        return module_definitions

    except ClientError as e:
        print("An error occurred:", e)
        return {}
    except json.JSONDecodeError as json_err:
        print("JSON parsing error:", json_err)
        return {}



def lambda_handler(event, context):
    # Print the entire event
    print("Received event: " + json.dumps(event))
    try:
        properties = {prop["name"]: prop["value"] for prop in event["requestBody"]["content"]["application/json"]["properties"]}
        repo_owner = 'ebbsleo'
        repo_name = 'learn-terraform-aft-account-customizations'
        token = os.environ['GITHUB_TOKEN']

        account_email = properties['AccountEmail']
        account_name = properties['AccountName']
  
        customization_name = properties['CustomizationName']
        user_request = properties['AwsServices'].split(',')  # Split the request into a list of services
        user_request = [service.strip() for service in user_request]  # Clean up any extra whitespace
        # Define the directory path and file names
        directory_path = f'{customization_name}-{account_name}/'
        main_tf_path = f'{directory_path}main.tf'
        readme_path = f'{directory_path}README.md'
        main_tf_path_url = f'https://github.com/{repo_owner}/{repo_name}/blob/main/{directory_path}main.tf'
        readme_path_url = f'https://github.com/{repo_owner}/{repo_name}/blob/main/{directory_path}README.md'

        # Generate Terraform config using Bedrock model
        module_definitions = retrieve_module_definitions("UNSXEU9TCO", "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-v2", user_request)

        # Construct the prompt with module definitions
        terraform_prompt = "Generate Terraform configurations for AWS services. Follow security best practices by using IAM roles and least privilege permissions. Include all necessary parameters, with default values.Add comments explaining the overall architecture and the purpose of each resource. "
        terraform_prompt += ', '.join(user_request)
        terraform_prompt += ". Use the following module definitions: "
        terraform_prompt += json.dumps(module_definitions)
        terraform_prompt += " For any service not listed, create a Terraform resource configuration."
        print("terraform_prompt", terraform_prompt)  # Print the response text

        
        # Invoke the model or method to generate Terraform configuration based on the prompt
        main_tf_content = invoke_bedrock_model(terraform_prompt)

        # Generate README using Bedrock model
        readme_prompt = f"Generate a detailed README for the Terraform configuration based on AWS services: {user_request}. Include sections on security improvements, cost optimization tips following the AWS Well-Architected Framework. Also, include detailed Cost Breakdown for each AWS service used with hourly rates and total daily and monthly costs"
        readme_content = invoke_bedrock_model(readme_prompt)
        # Commit main.tf to GitHub
        create_and_commit_file(repo_owner, repo_name, main_tf_path, token, f"Add main.tf for {account_name}", main_tf_content)
        # Commit README.md to GitHub
        create_and_commit_file(repo_owner, repo_name, readme_path, token, f"Add README.md for {account_name}", readme_content)

        return {
            'messageVersion': '1.0',
            'response': {
                'actionGroup': event['actionGroup'],
                'apiPath': event['apiPath'],
                'httpMethod': event['httpMethod'],
                'httpStatusCode': 200,
                'responseBody': {
                    'application/json': {
                        'body': json.dumps({
                            "message": f"main.tf and README.md successfully created in {directory_path}",
                            "main_tf_path": main_tf_path_url,
                            "readme_path": readme_path_url
                        })
                    }
                },
                'sessionAttributes': event.get('sessionAttributes', {}),
                'promptSessionAttributes': event.get('promptSessionAttributes', {})
            }
        }

    except Exception as e:
        logger.error(f"An error occurred: {e}", exc_info=True)
        # Ensure that error responses also align with the OpenAPI schema
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                "error": "An error occurred during the process.",
                "details": str(e)
            })
        }